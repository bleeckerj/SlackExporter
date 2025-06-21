import os
import json
import requests
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
client = WebClient(token=SLACK_BOT_TOKEN)

def robust_api_call(api_func, *args, **kwargs):
    while True:
        try:
            return api_func(*args, **kwargs)
        except SlackApiError as e:
            if e.response['error'] == 'ratelimited':
                retry_after = int(e.response.headers.get('Retry-After', 30))
                print(f"Rate limited. Sleeping for {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Slack API error: {e}")
                return None

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
    os.makedirs(output_dir, exist_ok=True)
    with open("users.json", "w") as f:
        json.dump(users, f, indent=2)
    for user in users:
        profile = user.get('profile', {})
        image_url = profile.get('image_512') or profile.get('image_192')
        if image_url:
            avatar_path = os.path.join(output_dir, f"{user['id']}.jpg")
            try:
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200:
                    with open(avatar_path, "wb") as imgf:
                        imgf.write(resp.content)
            except Exception as e:
                print(f"Failed to download avatar for {user['id']}: {e}")

def main():
    users = fetch_all_users()
    print(f"Fetched {len(users)} users.")
    save_users_and_avatars(users)
    print("User metadata saved to users.json and avatars downloaded.")

if __name__ == "__main__":
    main()
