#!/usr/bin/env python3
"""Create FontDock app icon"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create a 1024x1024 image with cyan background
size = 1024
img = Image.new('RGB', (size, size), color='#00bcd4')
draw = ImageDraw.Draw(img)

# Draw a large white "F"
try:
    # Try to use a system font
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 600)
except:
    # Fallback to default font
    font = ImageFont.load_default()

# Draw the F centered
text = "F"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
x = (size - text_width) // 2
y = (size - text_height) // 2 - 50

draw.text((x, y), text, fill='white', font=font)

# Draw small dots at top
dot_radius = 20
dot_y = 100
for dot_x in [100, 180, 260]:
    draw.ellipse([dot_x - dot_radius, dot_y - dot_radius, 
                  dot_x + dot_radius, dot_y + dot_radius], 
                 fill=(255, 255, 255, 150))

# Draw arrow (dock icon) in top right
arrow_x = 850
arrow_y = 150
arrow_size = 80
draw.line([(arrow_x, arrow_y), (arrow_x + arrow_size, arrow_y - arrow_size)], 
          fill='white', width=20)
draw.line([(arrow_x, arrow_y), (arrow_x + arrow_size, arrow_y + arrow_size)], 
          fill='white', width=20)

# Save the 1024x1024 PNG
img.save('icon_1024.png')
print("✓ Created icon_1024.png")

# Create iconset directory
os.makedirs('icon.iconset', exist_ok=True)

# Generate all required sizes
sizes = [
    (16, 'icon_16x16.png'),
    (32, 'icon_16x16@2x.png'),
    (32, 'icon_32x32.png'),
    (64, 'icon_32x32@2x.png'),
    (128, 'icon_128x128.png'),
    (256, 'icon_128x128@2x.png'),
    (256, 'icon_256x256.png'),
    (512, 'icon_256x256@2x.png'),
    (512, 'icon_512x512.png'),
    (1024, 'icon_512x512@2x.png'),
]

for size_px, filename in sizes:
    resized = img.resize((size_px, size_px), Image.Resampling.LANCZOS)
    resized.save(f'icon.iconset/{filename}')
    print(f"✓ Created {filename}")

print("\n✅ All icon sizes created!")
print("Now run: iconutil -c icns icon.iconset -o assets/icon.icns")
