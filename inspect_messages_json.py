import json
import os
from datetime import datetime, timezone

def inspect_messages(messages_path="./omata-developers/messages.json"):
    if not os.path.exists(messages_path):
        print(f"{messages_path} not found.")
        return
    with open(messages_path, "r") as f:
        messages = json.load(f)
    count = len(messages)
    if count == 0:
        print("No messages found.")
        return
    timestamps = [float(msg['ts']) for msg in messages]
    earliest = min(timestamps)
    latest = max(timestamps)
    print(f"Total messages: {count}")
    print(f"Earliest timestamp: {earliest} ({datetime.fromtimestamp(earliest, timezone.utc)})")
    print(f"Latest timestamp: {latest} ({datetime.fromtimestamp(latest, timezone.utc)})")

if __name__ == "__main__":
    inspect_messages()
