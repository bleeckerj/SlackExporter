# SlackExporterForOmata

A robust toolkit for exporting Slack workspace data, including messages, files, user metadata, and avatars. Designed for administrators who need to archive or analyze Slack content.

## Features
- Export messages from public and private channels where the bot is a member
- Download all files (attachments) shared in exported channels
- Export all user metadata and download user avatars
- Channel-level checkpointing for resumable exports
- Selective channel export via configuration file
- Robust handling of Slack API rate limits

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
4. **Create a Slack App:**
   - Add the following OAuth scopes: `channels:history`, `groups:history`, `im:history`, `mpim:history`, `channels:read`, `groups:read`, `users:read`, `users:read.email`, `team:read`, `files:read`.
   - Install the app to your workspace and copy the Bot User OAuth Token (starts with `xoxb-`).
5. **Create a `.env` file:**
   ```env
   SLACK_BOT_TOKEN=xoxb-...
   ```

## Scripts

### slack_exporter.py
Exports messages and files from channels where the bot is a member (or from channels specified in `export_config.json`).
- Downloads all files shared in messages to the `files/` directory.
- Saves user metadata and avatars.
- Tracks exported channels in `exported_channels.json` for resumable exports.
- Handles Slack API rate limits robustly.

#### Usage
```bash
python slack_exporter.py
```
- To export only specific channels, create `export_config.json`:
  ```json
  {
    "channel_ids": ["C12345678", "C87654321"]
  }
  ```

### export_users_metadata.py
Exports all user metadata to `users.json` and downloads user avatars to the `avatars/` directory.

#### Usage
```bash
python export_users_metadata.py
```

### export_channels_metadata.py
Exports all channel metadata (name, ID, is_member) to `channels.json` for reference or configuration.

#### Usage
```bash
python export_channels_metadata.py
```

### list_channels_metadata.py
Prints all channels and indicates whether the bot is a member of each.

#### Usage
```bash
python list_channels_metadata.py
```

## Notes
- The bot must be a member of private channels to export their messages.
- All output files (messages, users, avatars, files) are saved in the project directory or subdirectories.
- For large workspaces, exporting may take significant time due to Slack API rate limits.

## License
MIT
