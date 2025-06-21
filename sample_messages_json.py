import json
import os
from datetime import datetime

def print_sample_messages(messages_path="omata-developers/messages.json", sample_size=5):
    if not os.path.exists(messages_path):
        print(f"{messages_path} not found.")
        return
    with open(messages_path, "r") as f:
        messages = json.load(f)
    count = len(messages)
    print(f"Total messages: {count}")
    if count == 0:
        print("No messages found.")
        return
    def fmt(msg):
        ts = float(msg['ts'])
        dt = datetime.fromtimestamp(ts)
        text = msg.get('text', '')
        return f"{ts} ({dt}): {text[:80]}"
    print("\nFirst messages:")
    for msg in messages[:sample_size]:
        print(fmt(msg))
    print("\nLast messages:")
    for msg in messages[-sample_size:]:
        print(fmt(msg))

if __name__ == "__main__":
    print_sample_messages()
