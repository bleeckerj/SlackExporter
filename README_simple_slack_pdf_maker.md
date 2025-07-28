# simple_slack_pdf.py

This script converts Slack exported JSON messages into a simple printable PDF transcript.

## Features

- Sequentially renders Slack messages with user avatars, usernames, timestamps, and message text.
- Supports specifying PDF page size from standard ANSI and ISO A series sizes.
- Allows custom fonts for normal and bold text via TTF files.
- Supports configurable page margins.
- Includes a final "User Key" page listing all users with avatars, real names, and user IDs.

## Usage

Run the script with:

```bash
python3 simple_slack_pdf.py path/to/messages.json --page-size a4 --normal-font path/to/normal.ttf --bold-font path/to/bold.ttf --margin-top 1 --margin-bottom 1 --margin-left 1 --margin-right 1
```

- `messages.json` path is positional and optional (defaults to `omata-developers/messages.json`).
- `--page-size` selects the PDF page size (default `a4`).
- `--normal-font` and `--bold-font` specify TTF font files for text.
- Margins are specified in inches.

The output PDF is named `slack_transcript_<channel>_<pagesize>.pdf` where `<channel>` is the parent directory name of the messages JSON.

## Requirements

- Python 3
- reportlab
- Pillow

Install dependencies with:

```bash
pip install reportlab Pillow
```
