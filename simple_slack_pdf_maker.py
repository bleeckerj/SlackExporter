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

PAGE_SIZES = {
    'letter': letter,
    'legal': legal,
    'tabloid': (792, 1224),  # 11 x 17 inches in points
    'a0': A0,
    'a1': A1,
    'a2': A2,
    'a3': A3,
    'a4': A4,
    'a5': A5,
}

messages_file = 'omata-developers/messages.json'
users_file = 'users.json'
avatars_dir = 'avatars_40x40'

MARGIN = inch
AVATAR_SIZE = 0.35 * inch
LINE_HEIGHT = 10
FONT_SIZE = 9

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
    print(f'[DEBUG] replace_urls_in_text called with: {text}')
    # Match Slack-style URLs like <url|display>
    slack_url_pattern = re.compile(r'<([^|>]+)\|([^>]+)>')
    matches = slack_url_pattern.findall(text)
    for match in matches:
        print(f'Replacing Slack-style URL: <{match[0]}|{match[1]}>')
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
        print(f'Replacing plain URL: {match}')
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


def main(messages_json_path, page_size_name='letter', normal_font_path=None, bold_font_path=None, margin_top=inch, margin_bottom=inch, margin_left=inch, margin_right=inch):
    page_size = PAGE_SIZES.get(page_size_name.lower(), letter)
    PAGE_WIDTH, PAGE_HEIGHT = page_size

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

    # Use parent directory name of messages.json for output PDF name
    parent_dir = os.path.basename(os.path.dirname(os.path.abspath(messages_json_path)))
    output_pdf_name = f'slack_transcript_{parent_dir}_{page_size_name}.pdf'

    c = canvas.Canvas(output_pdf_name, pagesize=page_size)
    y = PAGE_HEIGHT - margin_top
    print(f'Generating PDF transcript: {output_pdf_name}')
    for msg in messages:
        if msg.get('type') != 'message':
            continue

        text = msg.get('text')
        file_names = []
        if msg.get('files'):
            file_names = [f.get('name', 'unknown') for f in msg['files'] if isinstance(f, dict)]
            # Ensure file names are ASCII only
            file_names = [name.encode('ascii', errors='ignore').decode('ascii') for name in file_names]
            print(f"[DEBUG] Found file names: {file_names}")
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
        print(f"[DEBUG] Before URL replacement: {text}")
        text = replace_user_mentions(text, user_map)
        text = replace_urls_in_text(text)
        print(f"[DEBUG] After URL replacement: {text}")

        # Draw avatar
        avatar_path = None
        for ext in ['.jpg', '.jpeg', '.png']:
            path = os.path.join(avatars_dir, f'{user_id}{ext}')
            if os.path.isfile(path):
                avatar_path = path
                break
        if avatar_path:
            try:
                c.drawImage(avatar_path, margin_left, y - AVATAR_SIZE, AVATAR_SIZE, AVATAR_SIZE, mask='auto')
            except Exception:
                c.setFillColorRGB(0, 0, 0)
                c.rect(margin_left, y - AVATAR_SIZE, AVATAR_SIZE, AVATAR_SIZE, fill=1)
        else:
            c.setFillColorRGB(0, 0, 0)
            c.rect(margin_left, y - AVATAR_SIZE, AVATAR_SIZE, AVATAR_SIZE, fill=1)

        # Draw username and timestamp
        c.setFont(bold_font_name, FONT_SIZE)
        c.drawString(margin_left + AVATAR_SIZE + 5, y - 10, f'{username} [{ts_human}]')

        # Draw message text
        c.setFont(normal_font_name, FONT_SIZE)
        text_x = margin_left + AVATAR_SIZE + 5
        text_y = y - 25
        max_text_width = PAGE_WIDTH - margin_right - text_x
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

        # Check for page break
        if y < margin_bottom + AVATAR_SIZE:
            c.showPage()
            y = PAGE_HEIGHT - margin_top

    # Draw user key page
    draw_user_key_page(c, users, avatars_dir, PAGE_WIDTH, PAGE_HEIGHT, margin_left, AVATAR_SIZE, LINE_HEIGHT, normal_font_name)

    c.save()
    print(f'PDF transcript generated: {output_pdf_name}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate Slack messages PDF transcript.')
    parser.add_argument('messages_json', nargs='?', default=messages_file, help='Path to messages.json file')
    parser.add_argument('--page-size', default='a4', choices=PAGE_SIZES.keys(), help='Page size for PDF output')
    parser.add_argument('--normal-font', help='Path to TTF file for normal font')
    parser.add_argument('--bold-font', help='Path to TTF file for bold font')
    parser.add_argument('--margin-top', type=float, default=1.0, help='Top margin in inches')
    parser.add_argument('--margin-bottom', type=float, default=1.0, help='Bottom margin in inches')
    parser.add_argument('--margin-left', type=float, default=1.0, help='Left margin in inches')
    parser.add_argument('--margin-right', type=float, default=1.0, help='Right margin in inches')
    args = parser.parse_args()

    main(args.messages_json, args.page_size, args.normal_font, args.bold_font, args.margin_top * inch, args.margin_bottom * inch, args.margin_left * inch, args.margin_right * inch)
