import os
import json
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

def main():
    channels = list_channels()
    output = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "is_member": c.get("is_member", False)
        }
        for c in channels
    ]
    with open("channels.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Exported metadata for {len(output)} channels to channels.json.")

if __name__ == "__main__":
    main()
