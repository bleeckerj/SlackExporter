import logging
import os
import time
import json
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from datetime import datetime
import sys
import ssl
import urllib.error
import argparse


# ensure logging is configured once, before any logging calls
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Python 3.8+ ensures reconfiguration
)

# parse command line args (add --root-dir, --dry-run, --skip-users)
parser = argparse.ArgumentParser(description="SlackExporterForOmata")
parser.add_argument("--root-dir", help="Root directory where export data will be saved", default=os.getcwd())
parser.add_argument("--dry-run", action="store_true", help="Fetch and log but don't write messages (files still downloaded).")
parser.add_argument("--skip-users", action="store_true", help="Skip fetching users and avatars.")
known = parser.parse_args()

ROOT_DIR = os.path.abspath(known.root_dir)
DRY_RUN = known.dry_run
SKIP_USERS = known.skip_users
os.makedirs(ROOT_DIR, exist_ok=True)

def out_path(*parts):
    """Return an absolute path under the configured ROOT_DIR."""
    return os.path.join(ROOT_DIR, *parts)

# global checkpoint file placed under ROOT_DIR
CHECKPOINT_FILE = out_path("exported_channels.json")

# Load environment variables from .env
load_dotenv()
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

client = WebClient(token=SLACK_BOT_TOKEN)

def robust_api_call(api_func, *args, **kwargs):
    method_name = api_func.__name__
    channel_id = kwargs.get('channel') or (args[0] if args else None)
    retry_count = 0
    while True:
        try:
            logging.info(f"Calling {method_name} for channel: {channel_id if channel_id else ''}")
            result = api_func(*args, **kwargs)
            logging.info(f"Success: {method_name} for channel: {channel_id if channel_id else ''}")
            return result
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                retry_after = int(e.response.headers.get('Retry-After', 30))
                logging.warning(f"Rate limited on {method_name} for channel: {channel_id if channel_id else ''}. Sleeping for {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                logging.error(f"Slack API error in {method_name} for channel: {channel_id if channel_id else ''}: {e}")
                return None
        except (ssl.SSLEOFError, urllib.error.URLError, requests.exceptions.RequestException) as net_err:
            retry_count += 1
            wait_time = min(60, 5 * retry_count)
            logging.error(f"Network error in {method_name} for channel: {channel_id if channel_id else ''}: {net_err}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as ex:
            logging.error(f"Unexpected error in {method_name} for channel: {channel_id if channel_id else ''}: {ex}")
            return None

def list_channels():
    channels = []
    cursor = None
    while True:
        response = robust_api_call(client.conversations_list, types="public_channel,private_channel", limit=100, cursor=cursor)
        if not response:
            break
        channels.extend(response['channels'])
        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    return channels

def fetch_messages(channel_id, limit=10):
    response = robust_api_call(client.conversations_history, channel=channel_id, limit=limit)
    if response:
        return response['messages']
    return []

def fetch_all_users():
    users = []
    cursor = None
    while True:
        response = robust_api_call(client.users_list, limit=200, cursor=cursor)
        if not response:
            break
        users.extend(response['members'])
        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    return users

def save_users_and_avatars(users, output_dir="avatars"):
    avatar_root = out_path(output_dir)
    os.makedirs(avatar_root, exist_ok=True)
    with open(out_path("users.json"), "w") as f:
        json.dump(users, f, indent=2)
    for user in users:
        profile = user.get('profile', {})
        image_url = profile.get('image_512') or profile.get('image_192')
        if image_url:
            avatar_path = os.path.join(avatar_root, f"{user['id']}.jpg")
            try:
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200:
                    with open(avatar_path, "wb") as imgf:
                        imgf.write(resp.content)
            except Exception as e:
                logging.error(f"Failed to download avatar for {user['id']}: {e}")

def load_exported_channels(checkpoint_file="exported_channels.json"):
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, "r") as f:
            data = json.load(f)
        # Auto-migrate old formats (list or str/bool values)
        if isinstance(data, list):
            # Old list format: just channel IDs
            return {cid: {'complete': True} for cid in data}
        elif isinstance(data, dict):
            migrated = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    migrated[k] = v
                else:
                    migrated[k] = {'complete': bool(v)}
            return migrated
    return {}

def save_exported_channel(channel_id, latest_ts, checkpoint_file="exported_channels.json"):
    exported = load_exported_channels(checkpoint_file)
    exported[channel_id] = latest_ts
    with open(checkpoint_file, "w") as f:
        json.dump(exported, f)

def save_channel_messages_batch(channel_name, new_batch):
    import json
    import os
    from datetime import datetime
    # Ensure channel directory exists under ROOT_DIR
    channel_dir = out_path(channel_name)
    os.makedirs(channel_dir, exist_ok=True)

    # Load existing messages from the channel directory
    path = os.path.join(channel_dir, "messages.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            existing = json.load(f)
    else:
        existing = []
    # Merge and deduplicate by ts
    all_msgs = {msg['ts']: msg for msg in existing}
    for msg in new_batch:
        ts = float(msg['ts'])
        dt = datetime.fromtimestamp(ts)
        text = msg.get('text', '')
        words = ' '.join(text.split()[:10])
        if msg['ts'] in all_msgs:
            print(f"DEDUPLICATED: {dt}: {words}")
        else:
            print(f"ADDED:        {dt}: {words}")
        all_msgs[msg['ts']] = msg
    # Sort chronologically
    merged_sorted = [all_msgs[ts] for ts in sorted(all_msgs, key=lambda t: float(t))]
    if not DRY_RUN:
        with open(path, "w") as f:
            json.dump(merged_sorted, f, indent=2)
        print(f"Saved {len(merged_sorted)} total messages to {path}")
    else:
        print(f"[DRY RUN] Would save {len(merged_sorted)} total messages to {path}")
    return merged_sorted

def fetch_all_messages(channel_id, channel_name, latest_saved_ts=None):
    messages = []
    cursor = None
    total_fetched = 0
    unique_timestamps = set()
    fetch_new_only = latest_saved_ts is not None
    while True:
        if fetch_new_only:
            logging.info(f"Fetching NEW messages for {channel_name} with ts > {latest_saved_ts}")
            response = robust_api_call(client.conversations_history, channel=channel_id, limit=1000, cursor=cursor, oldest=latest_saved_ts)
        else:
            logging.info(f"Fetching ALL messages for {channel_name} (cursor: {cursor if cursor else 'start'})")
            response = robust_api_call(client.conversations_history, channel=channel_id, limit=1000, cursor=cursor)
        start_time = time.time()
        if not response:
            break
        batch = response['messages']
        if not batch:
            logging.info(f"No more messages in batch for {channel_name}.")
            break
        batch_ts = [msg['ts'] for msg in batch]
        unique_timestamps.update(batch_ts)
        logging.info(f"Fetched {len(batch)} messages for {channel_name}. Batch ts range: {batch_ts[-1]} to {batch_ts[0]}")
        logging.info(f"Unique timestamps so far: {len(unique_timestamps)}")
        messages += batch
        total_fetched = len(messages)
        logging.info(f"Total messages fetched for {channel_name}: {total_fetched}")
        cursor = response.get('response_metadata', {}).get('next_cursor')
        elapsed = time.time() - start_time
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        if not cursor:
            break
    # Sort messages chronologically (oldest to newest)
    messages.sort(key=lambda m: float(m['ts']))
    return messages

def download_file(file_info, token, output_dir):
    """
    Save file preserving the original filename in output_dir.
    - If no collision: save as output_dir/<original_name>
    - If collision: create a timestamp-named subdirectory and save there as <original_name>
    - If collision still exists in the timestamp subdir, append a numeric suffix.
    - After successful save, append an entry to output_dir/downloaded_files.json with:
        { "filepath": "<abs path>", "raw_ts": "<seconds>", "actual_ts": "<with fractional seconds>" }
    """
    import re
    import tempfile
    import shutil
    import json
    import time

    os.makedirs(output_dir, exist_ok=True)

    url = file_info.get('url_private')
    if not url:
        logging.warning(f"Skipping file with missing URL in {output_dir}")
        return None

    # preserve original filename (sanitized)
    orig_name = file_info.get('name') or file_info.get('id') or "file"
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", orig_name)

    # preferred candidate: direct save in output_dir
    candidate_path = os.path.join(output_dir, safe_name)

    # If no collision, save directly in output_dir
    if not os.path.exists(candidate_path):
        target_dir = output_dir
        final_path = candidate_path
    else:
        # Collision: choose a timestamp-like subdirectory name
        if file_info.get('created'):
            ts_key = str(file_info.get('created'))
        elif file_info.get('timestamp'):
            ts_key = str(file_info.get('timestamp'))
        elif file_info.get('id'):
            ts_key = str(file_info.get('id'))
        else:
            ts_key = str(int(time.time()))
        subdir_name = ts_key.replace('.', '_')
        target_dir = os.path.join(output_dir, subdir_name)
        os.makedirs(target_dir, exist_ok=True)
        final_path = os.path.join(target_dir, safe_name)
        # If collision still exists in subdir, suffix numerically
        if os.path.exists(final_path):
            base, ext = os.path.splitext(safe_name)
            i = 1
            while True:
                candidate = f"{i}_{base}{ext}"
                candidate_path = os.path.join(target_dir, candidate)
                if not os.path.exists(candidate_path):
                    final_path = candidate_path
                    break
                i += 1

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30, stream=True)
        if resp.status_code == 200:
            # atomic write into target directory
            with tempfile.NamedTemporaryFile(delete=False, dir=target_dir) as tf:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        tf.write(chunk)
                temp_path = tf.name
            shutil.move(temp_path, final_path)
            logging.info(f"Downloaded file to {final_path}")
            # update manifest (idempotent, non-blocking)
            try:
                manifest_path = os.path.join(os.path.dirname(output_dir), "manifest.json")
                manifest = {}
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as mf:
                        manifest = json.load(mf)
                file_id = file_info.get('id') or safe_name
                manifest[file_id] = {
                    "saved_path": os.path.relpath(final_path, output_dir),
                    "original_name": orig_name,
                    "dir": os.path.relpath(target_dir, output_dir),
                    "ts": file_info.get('created') or file_info.get('timestamp') or None
                }
                with open(manifest_path, "w") as mf:
                    json.dump(manifest, mf, indent=2)
            except Exception:
                # manifest failure shouldn't block the download
                pass

            # append an entry to downloaded_files.json with filepath and timestamps
            try:
                index_path = os.path.join(os.path.dirname(output_dir), "downloaded_files.json")
                entries = []
                if os.path.exists(index_path):
                    with open(index_path, "r") as idxf:
                        try:
                            entries = json.load(idxf)
                            if not isinstance(entries, list):
                                entries = []
                        except Exception:
                            entries = []
                # determine raw_ts and actual_ts
                raw_ts = None
                actual_ts = None
                if file_info.get('created') is not None:
                    raw_ts = str(int(file_info.get('created')))
                    actual_ts = f"{int(file_info.get('created'))}.000000"
                elif file_info.get('timestamp') is not None:
                    try:
                        actual_ts = str(file_info.get('timestamp'))
                        raw_ts = str(int(float(actual_ts)))
                    except Exception:
                        actual_ts = str(file_info.get('timestamp'))
                        raw_ts = actual_ts.split('.')[0]
                else:
                    # fallback to current time
                    now = time.time()
                    raw_ts = str(int(now))
                    actual_ts = f"{int(now)}.000000"

                entry = {
                    "filepath": os.path.relpath(final_path),
                    "raw_ts": raw_ts,
                    "actual_ts": actual_ts,
                    "permalink": file_info.get('permalink'),
                    "permalink_public": file_info.get('url')
                }
                entries.append(entry)
                with open(index_path, "w") as idxf:
                    json.dump(entries, idxf, indent=2)
            except Exception:
                # indexing failure should not break download
                pass

            return final_path
        else:
            print(f"Failed to download file {orig_name}: HTTP {resp.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading file {orig_name}: {e}")
        return None

def load_export_config(config_file="export_config.json"):
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            data = json.load(f)
            return set(data.get("channel_ids", []))
    return None

def fetch_messages_newer(channel_id, channel_name, latest_saved_ts):
    messages = []
    cursor = None
    unique_timestamps = set()
    while True:
        print(f"Fetching NEWER messages for {channel_name} with ts > {latest_saved_ts}")
        start_time = time.time()
        response = robust_api_call(client.conversations_history, channel=channel_id, limit=1000, cursor=cursor, oldest=latest_saved_ts)
        if not response:
            break
        batch = response['messages']
        if not batch:
            print(f"No more newer messages in batch for {channel_name}.")
            break
        batch_ts = [msg['ts'] for msg in batch]
        unique_timestamps.update(batch_ts)
        print(f"Fetched {len(batch)} newer messages for {channel_name}. Batch ts range: {batch_ts[-1]} to {batch_ts[0]}")
        print(f"Unique newer timestamps so far: {len(unique_timestamps)}")
        messages += batch
        cursor = response.get('response_metadata', {}).get('next_cursor')
        elapsed = time.time() - start_time
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        if not cursor:
            break
    return messages

def fetch_messages_older(channel_id, channel_name, oldest_saved_ts):
    messages = []
    cursor = None
    unique_timestamps = set()
    while True:
        print(f"Fetching OLDER messages for {channel_name} with ts < {oldest_saved_ts}")
        start_time = time.time()
        response = robust_api_call(client.conversations_history, channel=channel_id, limit=1000, cursor=cursor, latest=oldest_saved_ts)
        if not response:
            break
        batch = response['messages']
        if not batch:
            print(f"No more older messages in batch for {channel_name}.")
            break
        batch_ts = [msg['ts'] for msg in batch]
        unique_timestamps.update(batch_ts)
        print(f"Fetched {len(batch)} older messages for {channel_name}. Batch ts range: {batch_ts[-1]} to {batch_ts[0]}")
        print(f"Unique older timestamps so far: {len(unique_timestamps)}")
        messages += batch
        cursor = response.get('response_metadata', {}).get('next_cursor')
        elapsed = time.time() - start_time
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        if not cursor:
            break
    return messages

def save_channel_messages_two_way(channel_name, older_messages, existing_messages, newer_messages):
    channel_dir = out_path(channel_name)
    os.makedirs(channel_dir, exist_ok=True)
    path = os.path.join(channel_dir, "messages.json")
    # Combine and deduplicate
    all_messages = older_messages + existing_messages + newer_messages
    all_messages = {msg['ts']: msg for msg in all_messages}.values()
    all_messages = sorted(all_messages, key=lambda m: float(m['ts']))
    if not DRY_RUN:
        with open(path, "w") as f:
            json.dump(list(all_messages), f, indent=2)
        print(f"Saved {len(all_messages)} total messages to {path}")
    else:
        print(f"[DRY RUN] Would save {len(all_messages)} total messages to {path}")
    return list(all_messages)

def log_message_sample(msg):
    ts = float(msg['ts'])
    dt = datetime.fromtimestamp(ts)
    text = msg.get('text', '')
    words = ' '.join(text.split()[:10])
    print(f"  {dt}: {words}")

def fetch_full_history(channel_id, channel_name):
    messages = []
    cursor = None
    unique_timestamps = set()
    channel_dir = out_path(channel_name)
    path = os.path.join(channel_dir, "messages.json")
    os.makedirs(channel_dir, exist_ok=True)
    while True:
        print(f"Fetching ALL messages for {channel_name} (cursor: {cursor if cursor else 'start'})")
        start_time = time.time()
        response = robust_api_call(client.conversations_history, channel=channel_id, limit=1000, cursor=cursor)
        if not response:
            break
        batch = response['messages']
        if not batch:
            print(f"No more messages in batch for {channel_name}.")
            break
        batch_ts = [msg['ts'] for msg in batch]
        unique_timestamps.update(batch_ts)
        logging.info(f"Fetched {len(batch)} messages for {channel_name}. Batch ts range: {batch_ts[-1]} to {batch_ts[0]}")
        for msg in batch:
            log_message_sample(msg)
        logging.info(f"Unique timestamps so far: {len(unique_timestamps)}")
        messages += batch
        logging.info(f"Total messages fetched for {channel_name}: {len(messages)}")
        # Aggressively save after each batch
        if os.path.exists(path):
            with open(path, "r") as f:
                existing = json.load(f)
        else:
            existing = []
        all_msgs = {msg['ts']: msg for msg in existing}
        for msg in messages:
            ts = float(msg['ts'])
            dt = datetime.fromtimestamp(ts)
            text = msg.get('text', '')
            words = ' '.join(text.split()[:10])
            # Add human-readable timestamp below 'ts'
            msg['ts_human'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            if msg['ts'] in all_msgs:
                logging.warning(f"NOT SAVED (DEDUPLICATED): {dt}: {words}")
            else:
                logging.info(f"SAVED: {dt}: {words}")
            all_msgs[msg['ts']] = msg
        merged_sorted = [all_msgs[ts] for ts in sorted(all_msgs, key=lambda t: float(t))]
        if not DRY_RUN:
            with open(path, "w") as f:
                json.dump(merged_sorted, f, indent=2)
            logging.info(f"Aggressively saved {len(merged_sorted)} total messages to {path}")
        else:
            logging.info(f"[DRY RUN] Would save {len(merged_sorted)} total messages to {path}")
        cursor = response.get('response_metadata', {}).get('next_cursor')
        elapsed = time.time() - start_time
        if elapsed < 1.2:
            time.sleep(1.2 - elapsed)
        if not cursor:
            break
    # Sort messages chronologically (oldest to newest)
    messages.sort(key=lambda m: float(m['ts']))
    return messages

def main():
    if not SKIP_USERS:
        users = fetch_all_users()
        save_users_and_avatars(users)
    channels = list_channels()
    logging.info(f"Found {len(channels)} channels.")
    member_channels = [c for c in channels if c.get('is_member')]
    config_channel_ids = load_export_config()
    if config_channel_ids:
        member_channels = [c for c in member_channels if c['id'] in config_channel_ids]
        logging.info(f"Exporting from {len(member_channels)} channels specified in export_config.json.")
    else:
        logging.info(f"Exporting from {len(member_channels)} channels where bot is a member.")
    exported = load_exported_channels(CHECKPOINT_FILE)
    checkpoint_file = CHECKPOINT_FILE
    for channel in member_channels:
        channel_id = channel['id']
        channel_name = channel['name']
        path = out_path(channel_name, "messages.json")
        channel_checkpoint = exported.get(channel_id, {})
        backfilled = channel_checkpoint.get('backfilled', False)
        # Always backfill if not done yet
        if not backfilled:
            logging.info(f"\nChannel: {channel_name} ({channel_id}) - Performing full backfill.")
            messages = fetch_full_history(channel_id, channel_name)
            saved_messages = save_channel_messages_batch(channel_name, messages)
            # Post-save verification: log any fetched message not saved
            saved_ts_set = set(msg['ts'] for msg in saved_messages)
            for msg in messages:
                if msg['ts'] not in saved_ts_set:
                    ts = float(msg['ts'])
                    dt = datetime.fromtimestamp(ts)
                    text = msg.get('text', '')
                    words = ' '.join(text.split()[:10])
                    logging.warning(f"Fetched but NOT SAVED: {dt}: {words}")
            files_dir = out_path(channel_name, 'files')
            file_count = 0
            for msg in saved_messages:
                for file_info in msg.get('files', []):
                    if not DRY_RUN:
                        download_file(file_info, SLACK_BOT_TOKEN, files_dir)
                        file_count += 1
                    else:
                        logging.info(f"[DRY RUN] Would download file: {file_info.get('name')}")
            # Only set backfilled after successful save
            exported[channel_id] = {
                'backfilled': True,
                'latest_ts': saved_messages[-1]['ts'] if saved_messages else None
            }
            with open(checkpoint_file, "w") as f:
                json.dump(exported, f, indent=2)
            logging.info(f"Finished channel {channel_name}: {len(saved_messages)} messages, {file_count} files downloaded.")
            time.sleep(1)
            continue
        # If already backfilled, only fetch newer messages
        logging.info(f"\nChannel: {channel_name} ({channel_id}) - Already backfilled, checking for new messages.")
        existing_messages = []
        latest_saved_ts = None
        if os.path.exists(path):
            with open(path, "r") as f:
                existing_messages = json.load(f)
            if existing_messages:
                latest_saved_ts = existing_messages[-1]['ts']
        newer_messages = fetch_messages_newer(channel_id, channel_name, latest_saved_ts) if latest_saved_ts else []
        if newer_messages:
            all_messages = existing_messages + newer_messages
            all_messages = {msg['ts']: msg for msg in all_messages}.values()
            all_messages = sorted(all_messages, key=lambda m: float(m['ts']))
            save_channel_messages_batch(channel_name, list(all_messages))
            files_dir = out_path(channel_name, 'files')
            file_count = 0
            for msg in newer_messages:
                for file_info in msg.get('files', []):
                    if not DRY_RUN:
                        download_file(file_info, SLACK_BOT_TOKEN, files_dir)
                        file_count += 1
                    else:
                        logging.info(f"[DRY RUN] Would download file: {file_info.get('name')}")
            exported[channel_id]['latest_ts'] = all_messages[-1]['ts'] if all_messages else latest_saved_ts
            with open(checkpoint_file, "w") as f:
                json.dump(exported, f, indent=2)
            logging.info(f"Updated channel {channel_name}: {len(all_messages)} messages, {file_count} new files downloaded.")
        else:
            logging.info(f"No new messages for channel {channel_name}.")
        time.sleep(1)

if __name__ == "__main__":
    main()
