# slack_exporter.py

A robust script for exporting Slack workspace data, including messages, files, user metadata, and avatars. Designed for administrators who need to archive or analyze Slack content..or make fun books from messages and files.

## Features
- Export messages from public and private channels where the bot is a member (or specified in export_config.json)
- Download all files (attachments) shared in exported channels
- Export all user metadata and download user avatars
- Channel-level checkpointing for resumable exports
- Selective channel export via configuration file
- Robust handling of Slack API rate limits
- Deduplication and chronological sorting of messages
- Supports dry-run mode and skipping user export

## Setup
1. **Clone the repository and navigate to the directory.**
2. **Create and activate a Python virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create a Slack App and obtain a Bot User OAuth Token.**
5. **Create a `.env` file:**
   ```env
   SLACK_BOT_TOKEN=xoxb-your-token-here
   ```

## Usage
Run the exporter with:
```bash
python slack_exporter.py
```

### Options
- `--dry-run` — Simulate export without writing files or downloading attachments.
- `--skip-users` — Skip exporting user metadata and avatars.

### Selective Channel Export
To export only specific channels, create `export_config.json`:
```json
{
  "channel_ids": ["C12345678", "C87654321"]
}
```

## Output
- Messages are saved in `<channel_name>/messages.json`.
- Files are downloaded to `<channel_name>/files/`.
- User metadata is saved to `users.json` and avatars to `avatars/`.
- Export progress is tracked in `exported_channels.json` for resumable exports.

## Notes
- The bot must be a member of private channels to export their messages.
- Handles Slack API rate limits and network errors robustly.
- For large workspaces, exporting may take significant time due to rate limits.

## License
Creative Commons Attribution-NonCommercial (CC BY-NC)

This project is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) license. You are free to use, share, and adapt the software, provided you give appropriate credit and do not use it for commercial purposes. For more details, see https://creativecommons.org/licenses/by-nc/4.0/
