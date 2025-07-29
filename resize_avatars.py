import os
from PIL import Image

INPUT_DIR = 'avatars'
OUTPUT_DIR = 'avatars_40x40'

os.makedirs(OUTPUT_DIR, exist_ok=True)

for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with Image.open(input_path) as img:
            img = img.convert('RGB')  # Convert to RGB to avoid mode issues
            img = img.resize((168, 168), Image.LANCZOS)
            img.save(output_path, dpi=(300, 300))
            print(f'Resized and saved {output_path} with 300 DPI')

print('All images resized to 168x168 pixels at 300 DPI and saved in', OUTPUT_DIR)
