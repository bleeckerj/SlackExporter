# SlackExporterForOmata

A robust toolkit for exporting Slack workspace data, including messages, files, user metadata, and avatars. Designed for administrators who need to archive or analyze Slack content.

## Features
- Export messages from public and private channels where the bot is a member
- Download all files (attachments) shared in exported channels
- Export all user metadata and download user avatars
- Channel-level checkpointing for resumable exports
- Selective channel export via configuration file
- Robust handling of Slack API rate limits

## Consists of the following tools:

- slack_exporter.py — Export messages and files from channels, save user metadata and avatars, handle rate limits.
- export_users_metadata.py — Export all user metadata and download user avatars.
- export_channels_metadata.py — Export all channel metadata (name, ID, is_member).
- list_channels_metadata.py — Print all channels and indicate bot membership.
- slack2pdf.py — Convert Slack JSON exports into printable PDF transcripts with avatars and message text. [See detailed usage and options for slack2pdf.py in README_slack2pdf.md.](README_slack2pdf.md)
- resize_avatars.py — Resize avatars to 168x168 at 300 DPI for PDF transcripts.
- inspect_messages_json.py — Report total messages and earliest/latest timestamps for a messages.json.
- sample_messages_json.py — Print first/last N sample messages from a messages.json.
- count_messages_with_files.py — Count messages that include file attachments.
- run-on-all.sh — Batch-run the PDF transcript generator for every messages.json.

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

## How to Obtain Your Slack Bot OAuth Token

1. **Create a Slack App:**
   - Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click "Create New App".
   - Choose "From scratch" and give your app a name and select your workspace.

2. **Add OAuth Scopes:**
   - In your app settings, go to "OAuth & Permissions".
   - Under "Scopes", add the following Bot Token Scopes:
     - `channels:history`
     - `groups:history`
     - `im:history`
     - `mpim:history`
     - `channels:read`
     - `groups:read`
     - `users:read`
     - `users:read.email`
     - `team:read`
     - `files:read`

3. **Install the App to Your Workspace:**
   - In the "OAuth & Permissions" section, click "Install App to Workspace".
   - Authorize the app when prompted.

4. **Copy the Bot User OAuth Token:**
   - After installation, you’ll see a "Bot User OAuth Token" (it starts with `xoxb-`).
   - Copy this token.

5. **Add the Token to Your `.env` File:**
   - In your project directory, create a `.env` file (if it doesn’t exist).
   - Add the following line:
     ```
     SLACK_BOT_TOKEN=xoxb-your-token-here
     ```

**Note:**  
The bot must be invited to each channel (public or private) you wish to export from. Use `/invite @your-bot-name` in Slack to add it to channels

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

## Simple Slack PDF Transcript

This workspace includes `slack2pdf.py`, a script to convert the Slack JSON exports that the above tools produce into printable PDF transcripts with user avatars, timestamps, and message text.

This script makes the books (almost — no covers, no representation of the visual assets). To do the visual assets you'll want to look at the [pdf-to-grid-of-images](https://github.com/bleeckerj/pdf-to-grid-of-images) repository. To do the covers — well...at the moment, you'll want to do that by hand!

### Features

- Supports ANSI and ISO A series page sizes.
- Custom fonts and page margins.
- Includes a user key page with avatars and user info.

### Usage

Run with:

```bash
python3 slack2pdf.py path/to/messages.json --page-size a4 --normal-font path/to/normal.ttf --bold-font path/to/bold.ttf --margin-top 1 --margin-bottom 1 --margin-left 1 --margin-right 1
```

The output PDF is named based on the channel folder and page size.

## Integration with pdf-to-grid-of-images

The [pdf-to-grid-of-images](https://github.com/bleeckerj/pdf-to-grid-of-images) repository can be used to convert the PDFs, images, and movie files found in each channel’s `files` directory into pages of visual content for book assembly or further processing.  
That project includes two Python scripts:

- `directory_to_images.py`: Converts all pdfs, images and movies in a directory into page-ready image assets.
- `pdf_to_images.py`: Converts PDF files into images for use as pages.
- `process_all_slack_dirs.py`: Creates page images and combined PDFs along with flipbook pages representing video files, user indices, etc., for all the Slack content directories.

Use these tools to process the exported files from Slack channels and generate pages full of message transcripts and visual assets for your book or archive.

## Notes
- The bot must be a member of private channels to export their messages.
- All output files (messages, users, avatars, files) are saved in the project directory or subdirectories.
- For large workspaces, exporting may take significant time due to Slack API rate limits.

## License
MIT
