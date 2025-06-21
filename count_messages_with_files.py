import json
import os

def count_messages_with_files(messages_path="./omata-developers/messages.json"):
    if not os.path.exists(messages_path):
        print(f"{messages_path} not found.")
        return
    with open(messages_path, "r") as f:
        messages = json.load(f)
    count = sum(1 for msg in messages if msg.get('files'))
    print(f"Messages with file attachments: {count} out of {len(messages)} total messages.")

if __name__ == "__main__":
    count_messages_with_files()
