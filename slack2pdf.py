import json
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, legal, A4, A3, A2, A1, A0, A5
from reportlab.lib.units import inch
from PIL import Image
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import io
import qrcode
from reportlab.lib.utils import ImageReader
import logging
import random

logging.basicConfig(level=logging.INFO)

PAGE_SIZES = {
        'A5': (5.83, 8.27),
        'A5_FULLBLEED': (5.955, 8.395),
        'A4': (8.27, 11.69),
        'A3': (11.69, 16.54),
        'A2': (16.54, 23.39),
        'A1': (23.39, 33.11),
        'A0': (33.11, 46.81),
        'TRADE_LARGE': (7, 9),
        'LETTER': (8.5, 11),
        'LEGAL': (8.5, 14),
        'TABLOID': (11, 17),
        'DIGEST': (5.5, 8.5),         # Digest size
        'DIGEST_FULLBLEED': (5.625, 8.625),
        'POCKETBOOK': (4.25, 6.87),   # PocketBook size
        'POCKETBOOK_FULLBLEED': (4.375, 6.995),
        # Playing card sizes (in inches, rounded to 2 decimals)
        'POKER': (2.48, 3.46),        # 63x88mm
        'BRIDGE': (2.24, 3.46),       # 57x88mm
        'MINI': (1.73, 2.68),         # 44x68mm
        'LARGE_TAROT': (2.76, 4.72),  # 70x120mm
        'SMALL_TAROT': (2.76, 4.25),  # 70x108mm
        'LARGE_SQUARE': (2.76, 2.76), # 70x70mm
        'SMALL_SQUARE': (2.48, 2.48), # 63x63mm
}

messages_file = 'omata-developers/messages.json'
users_file = 'users.json'
avatars_dir = 'avatars'

MARGIN = inch
AVATAR_SIZE = 0.4 * inch
LINE_HEIGHT = 8
FONT_SIZE = 7

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ts_to_human(ts):
    return ts  # Already human readable in JSON


def draw_wrapped_text(c, text, x, y, max_width, line_height, font_name="Helvetica", font_size=FONT_SIZE):
    words = text.split(' ')
    line = ''
    c.setFont(font_name, font_size)
    for word in words:
        test_line = line + word + ' '
        if c.stringWidth(test_line, font_name, font_size) < max_width:
            line = test_line
        else:
            c.drawString(x, y, line.strip())
            y -= line_height
            line = word + ' '
    if line:
        c.drawString(x, y, line.strip())
        y -= line_height
    return y


def draw_user_key_page(c, users, avatars_dir, page_width, page_height, margin, avatar_size, line_height, normal_font_name="Helvetica"):
    c.showPage()
    c.setFont(normal_font_name, FONT_SIZE)
    c.drawString(margin, page_height - margin, "User Key")

    y = page_height - margin - 30
    x_left = margin
    x_right = margin + (page_width - 2 * margin) / 2
    c.setFont(normal_font_name, FONT_SIZE)

    col = 0

    for user in users:
        if col == 0 and y < margin + avatar_size:
            c.showPage()
            c.setFont(normal_font_name, FONT_SIZE)
            c.drawString(margin, page_height - margin, "User Key")
            y = page_height - margin - 30

        user_id = user.get('id', 'unknown')
        real_name = user.get('real_name', '')
        display_name = user.get('name', '')

        x = x_left if col == 0 else x_right

        # Draw avatar
        avatar_path = None
        for ext in ['.jpg', '.jpeg', '.png']:
            path = os.path.join(avatars_dir, f'{user_id}{ext}')
            if os.path.isfile(path):
                avatar_path = path
                break
        if avatar_path:
            try:
                c.drawImage(avatar_path, x, y - avatar_size, avatar_size, avatar_size, mask='auto')
            except Exception:
                c.setFillColorRGB(0, 0, 0)
                c.rect(x, y - avatar_size, avatar_size, avatar_size, fill=1)
        else:
            c.setFillColorRGB(0, 0, 0)
            c.rect(x, y - avatar_size, avatar_size, avatar_size, fill=1)

        # Draw user info
        text_x = x + avatar_size + 5
        c.drawString(text_x, y - 10, f'{real_name} ({display_name})')
        c.drawString(text_x, y - 25, f'User ID: {user_id}')

        if col == 1:
            y -= avatar_size + 15

        col = (col + 1) % 2

    # If last row was single column, add some space
    if col == 1:
        y -= avatar_size + 15


def insert_breaks_in_url(text):
    # Insert zero-width space after special URL chars to improve wrapping
    special_chars = ['/', '.', '|', '-', '_', '?', '=', '&']
    for ch in special_chars:
        text = text.replace(ch, ch + '\u200b')
    return text


def replace_user_mentions(text, user_map):
    import re
    # Replace user mentions
    pattern = re.compile(r'<@([A-Z0-9]+)>')
    def replacer(match):
        user_id = match.group(1)
        return '@' + user_map.get(user_id, 'unknown')
    text = pattern.sub(replacer, text)

    # Replace Slack-style URLs <url|display> with clean filename
    slack_url_pattern = re.compile(r'<([^|>]+)\|([^>]+)>')
    def slack_url_replacer(match):
        display = match.group(2)
        # Extract filename by removing trailing non-filename chars
        filename = display.split('/')[-1]
        filename = re.sub(r'[^\w\d\.\-]+$', '', filename)
        return filename
    text = slack_url_pattern.sub(slack_url_replacer, text)

    # Replace plain URLs with 'URL'
    url_pattern = re.compile(r'https?://\S+')
    text = url_pattern.sub('URL', text)

    return text


def replace_urls_in_text(text):
    import re
    logging.debug(f'replace_urls_in_text called with: {text}')
    # Match Slack-style URLs like <url|display>
    slack_url_pattern = re.compile(r'<([^|>]+)\|([^>]+)>')
    matches = slack_url_pattern.findall(text)
    for match in matches:
        logging.debug(f'Replacing Slack-style URL: <{match[0]}|{match[1]}>')
    def slack_url_replacer(m):
        display = m.group(2)
        filename = display.split('/')[-1]
        filename = re.sub(r'[^\x00-\x7F]+$', '', filename)  # Remove trailing non-ASCII chars
        return filename
    text = slack_url_pattern.sub(slack_url_replacer, text)

    # Replace plain URLs with 'URL'
    url_pattern = re.compile(r'https?://\S+')
    matches = url_pattern.findall(text)
    for match in matches:
        logging.debug(f'Replacing plain URL: {match}')
    text = url_pattern.sub('URL', text)

    return text


def draw_qr_code(c, data, x, y, size):
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    c.drawImage(ImageReader(img_buffer), x, y - size, size, size)


def draw_file_index_page(c, files, page_width, page_height, margin_left, margin_bottom, line_height, normal_font_name="Helvetica"):
    c.showPage()
    c.setFont(normal_font_name, FONT_SIZE + 2)
    margin_top = margin_bottom  # Use same margin for top as bottom for consistency
    c.drawString(margin_left, page_height - margin_top, "File Index")

    y = page_height - margin_top - 30
    x_left = margin_left
    x_right = margin_left + (page_width - 2 * margin_left) / 2
    c.setFont(normal_font_name, FONT_SIZE)

    col = 0
    file_index = 0
    
    while file_index < len(files):
        # Check if we need a new page
        if y < margin_bottom + line_height:
            c.showPage()
            c.setFont(normal_font_name, FONT_SIZE + 2)
            c.drawString(margin_left, page_height - margin_top, "File Index (continued)")
            y = page_height - margin_top - 30
            c.setFont(normal_font_name, FONT_SIZE - 2)
            col = 0
        
        x = x_left if col == 0 else x_right
        c.drawString(x, y, files[file_index])
        file_index += 1
        
        if col == 1:
            y -= line_height

        col = (col + 1) % 2
    
    # If last row was single column, add some space
    if col == 1:
        y -= line_height


def draw_page_number_and_channel(c, page_num, page_width, margin_bottom, normal_font_name, font_size, channel_name, page_height, margin_top):
    # Draw page number at bottom center
    c.setFont(normal_font_name, font_size)
    page_num_text = f"{page_num}"
    text_width = c.stringWidth(page_num_text, normal_font_name, font_size)
    x = (page_width - text_width) / 2
    y = margin_bottom + font_size * 1.5
    c.drawString(x, y, page_num_text)
    # Draw channel name at top center
    channel_text_width = c.stringWidth(channel_name, normal_font_name, font_size + 2)
    channel_x = (page_width - channel_text_width) / 2
    channel_y = page_height - margin_top + 1.5 * font_size
    c.setFont(normal_font_name, font_size + 2)
    c.drawString(channel_x, channel_y, channel_name)


def estimate_wrapped_text_height(c, text, max_width, line_height, font_name, font_size):
    words = text.split(' ')
    line = ''
    lines = 0
    for word in words:
        test_line = line + word + ' '
        if c.stringWidth(test_line, font_name, font_size) < max_width:
            line = test_line
        else:
            lines += 1
            line = word + ' '
    if line:
        lines += 1
    return lines * line_height


def parse_page_size(page_size_name):
    import re
    # Check for custom WxH format (e.g., 6x9)
    match = re.match(r'^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$', page_size_name.strip(), re.IGNORECASE)
    if match:
        w_in = float(match.group(1))
        h_in = float(match.group(2))
        return (w_in * inch, h_in * inch)
    # Otherwise, use predefined sizes
    page_size_in = PAGE_SIZES.get(page_size_name.upper(), PAGE_SIZES['LETTER'])
    return (page_size_in[0] * inch, page_size_in[1] * inch)


def main(messages_json_path, page_size_name='letter', normal_font_path=None, bold_font_path=None, margin_top=inch, margin_bottom=inch, margin_left=inch, margin_right=inch, output_dir=None):
    PAGE_WIDTH, PAGE_HEIGHT = parse_page_size(page_size_name)
    page_size = (PAGE_WIDTH, PAGE_HEIGHT)

    # Register fonts if provided
    if normal_font_path:
        pdfmetrics.registerFont(TTFont('CustomNormal', normal_font_path))
        normal_font_name = 'CustomNormal'
    else:
        normal_font_name = 'Helvetica'

    if bold_font_path:
        pdfmetrics.registerFont(TTFont('CustomBold', bold_font_path))
        bold_font_name = 'CustomBold'
    else:
        bold_font_name = 'Helvetica-Bold'

    messages = load_json(messages_json_path)
    users = load_json(users_file)

    user_map = {user['id']: user['name'] for user in users}

    # Use parent directory name of messages.json for output PDF name and channel name
    parent_dir = os.path.basename(os.path.dirname(os.path.abspath(messages_json_path)))
    output_pdf_name = f'slack_transcript_{parent_dir}_{page_size_name}.pdf'
    channel_name = parent_dir

    # If output_dir is specified, use it for the output PDF path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_pdf_path = os.path.join(output_dir, output_pdf_name)
    else:
        output_pdf_path = output_pdf_name

    page_num = 1
    c = canvas.Canvas(output_pdf_path, pagesize=page_size)
    y = PAGE_HEIGHT - margin_top
    logging.info(f'Generating PDF transcript: {output_pdf_path}')
    for msg in messages:
        if msg.get('type') != 'message':
            continue

        text = msg.get('text')
        file_names = []
        if msg.get('files'):
            file_names = [f.get('name', 'unknown') for f in msg['files'] if isinstance(f, dict)]
            # Ensure file names are ASCII only
            file_names = [name.encode('ascii', errors='ignore').decode('ascii') for name in file_names]
            logging.debug(f"Found file names: {file_names}")
        # If no text, but files exist, show only file references
        if (not text or not text.strip()) and file_names:
            text = ''  # No main text, only files
        elif not text or not text.strip():
            continue
        # If both text and files, keep text as is
        # File references will be drawn separately

        user_id = msg.get('user', 'unknown')
        username = user_map.get(user_id, 'Unknown User')
        ts_human = ts_to_human(msg.get('ts_human', 'Unknown Time'))
        # Do NOT overwrite text here!

        # Replace user mentions and URLs in main text only
        logging.debug(f"Before URL replacement: {text}")
        text = replace_user_mentions(text, user_map)
        text = replace_urls_in_text(text)
        logging.debug(f"After URL replacement: {text}")

        # Estimate message height
        text_x = margin_left + AVATAR_SIZE + 5
        max_text_width = PAGE_WIDTH - margin_right - text_x
        message_height = 25  # header and spacing
        if text:
            message_height += estimate_wrapped_text_height(c, text, max_text_width, LINE_HEIGHT, normal_font_name, FONT_SIZE)
        if file_names:
            message_height += len(file_names) * LINE_HEIGHT
        message_height += 10  # bottom spacing

        # Check for page break BEFORE drawing
        if y - message_height < margin_bottom + FONT_SIZE * 2:
            draw_page_number_and_channel(c, page_num, PAGE_WIDTH, margin_bottom, normal_font_name, FONT_SIZE, channel_name, PAGE_HEIGHT, margin_top)
            c.showPage()
            page_num += 1
            y = PAGE_HEIGHT - margin_top

        # Draw avatar
        avatar_path = None
        if user_id == "U08B6KZJ4":
            # Hardcoded filenames for this user
            hardcoded_files = [
                os.path.join(avatars_dir, "U62S2LGFK.jpg"),
                os.path.join(avatars_dir, "U08B6KZJ4.jpg"),
                os.path.join(avatars_dir, "drunk_clown.jpg"),
                os.path.join(avatars_dir, "U0FR0H27Q.jpg"),
            ]
            existing_files = [path for path in hardcoded_files if os.path.isfile(path)]
            if existing_files:
                avatar_path = random.choice(existing_files)
        else:
            for ext in ['.jpg', '.jpeg', '.png']:
                path = os.path.join(avatars_dir, f'{user_id}{ext}')
                if os.path.isfile(path):
                    avatar_path = path
                    break
        if avatar_path:
            try:
                c.drawImage(avatar_path, margin_left, y - AVATAR_SIZE - 3, AVATAR_SIZE, AVATAR_SIZE, mask='auto')  # -10 moves it further down
            except Exception:
                c.setFillColorRGB(0, 0, 0)
                c.rect(margin_left, y - AVATAR_SIZE - 8, AVATAR_SIZE, AVATAR_SIZE, fill=1)
        else:
            c.setFillColorRGB(0, 0, 0)
            c.rect(margin_left, y - AVATAR_SIZE - 8, AVATAR_SIZE, AVATAR_SIZE, fill=1)

        if user_id == 'U08B6KZJ4':
            # here's a list of names, pick one
            villain_names = ["Astaroth", "Nyx", "Zaxxon", "Voldymor", "Zoltron", "Zebulon", "Thorne", "Snidely", "Cruella", "Mojo", "Ratso", "Cruntolimeu", "Hexadreadcimal", "Viperina", "Jinque", "Zorton", "Malbeced", "Draco", "Scarabella", "Venomina", "Clawdia", "Grumbleton", "Slinko", "Druenna", "Morgul", "Tricksy", "Cankle", "Cackles", "Drusilda", "Dank Druid", "Fizzlewick", "Gloomsworth", "Malarkus", "Nefaria", "Zombina", "Snivelston", "Velsneer"]
            # pick a random villain name
            username = random.choice(villain_names)

        # Draw username and timestamp
        c.setFont(bold_font_name, FONT_SIZE)
        c.drawString(margin_left + AVATAR_SIZE + 5, y - 8, f'{username} [{ts_human}]')

        # Draw message text
        c.setFont(normal_font_name, FONT_SIZE)
        text_y = y - 2.8 * FONT_SIZE
        if text:
            text_y = draw_wrapped_text(c, text, text_x, text_y, max_text_width, LINE_HEIGHT, font_name=normal_font_name, font_size=FONT_SIZE)
        # Draw file references (never wrapped or altered)
        if file_names:
            for name in file_names:
                c.drawString(text_x, text_y, f'FILE: {name}')
                text_y -= LINE_HEIGHT

        # Optionally draw QR code for URLs
        url_pattern = re.compile(r'(https?://\S+)')
        urls = url_pattern.findall(text)
        if urls:
            qr_code_size = AVATAR_SIZE
            qr_code_x = PAGE_WIDTH - margin_right - qr_code_size
            qr_code_y = y - AVATAR_SIZE
            for url in urls:
                draw_qr_code(c, url, qr_code_x, qr_code_y, qr_code_size)
                qr_code_y -= qr_code_size + 5  # Stack QR codes if multiple

        # Update y position for next message
        y = text_y - 10

    # Draw file index page
    draw_page_number_and_channel(c, page_num, PAGE_WIDTH, margin_bottom, normal_font_name, FONT_SIZE, channel_name, PAGE_HEIGHT, margin_top)
    
    # Collect all file names from messages
    all_files = []
    for msg in messages:
        if msg.get('type') == 'message' and msg.get('files'):
            for f in msg.get('files', []):
                if isinstance(f, dict) and f.get('name'):
                    file_name = f.get('name', '').encode('ascii', errors='ignore').decode('ascii')
                    if file_name and file_name not in all_files:
                        all_files.append(file_name)
    
    # Sort files alphabetically
    all_files.sort()
    
    # Draw the file index page
    if all_files:
        draw_file_index_page(c, all_files, PAGE_WIDTH, PAGE_HEIGHT, margin_left, margin_bottom, LINE_HEIGHT, normal_font_name)
        page_num += 1
    
    # Draw user key page
    draw_page_number_and_channel(c, page_num, PAGE_WIDTH, margin_bottom, normal_font_name, FONT_SIZE, channel_name, PAGE_HEIGHT, margin_top)
    draw_user_key_page(c, users, avatars_dir, PAGE_WIDTH, PAGE_HEIGHT, margin_left, AVATAR_SIZE, LINE_HEIGHT, normal_font_name)

    c.save()
    logging.info(f'PDF transcript generated: {output_pdf_path}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate Slack messages PDF transcript.')
    parser.add_argument('messages_json', nargs='?', default=messages_file, help='Path to messages.json file')
    parser.add_argument('--page-size', default='A4', help='Page size for PDF output (e.g. A4, LETTER, or custom WxH in inches, e.g. 6x9)')
    parser.add_argument('--normal-font', help='Path to TTF file for normal font')
    parser.add_argument('--bold-font', help='Path to TTF file for bold font')
    parser.add_argument('--margin-top', type=float, default=1.0, help='Top margin in inches')
    parser.add_argument('--margin-bottom', type=float, default=1.0, help='Bottom margin in inches')
    parser.add_argument('--margin-left', type=float, default=1.0, help='Left margin in inches')
    parser.add_argument('--margin-right', type=float, default=1.0, help='Right margin in inches')
    parser.add_argument('--output-dir', help='Directory to save the output PDF')
    args = parser.parse_args()

    main(args.messages_json, args.page_size, args.normal_font, args.bold_font, args.margin_top * inch, args.margin_bottom * inch, args.margin_left * inch, args.margin_right * inch, args.output_dir)
