import fitz  # PyMuPDF for reading PDFs
import cv2
import numpy as np
import os
from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

def detect_content_region(image, margin=20):
    """
    Detects the bounding box of non-blank content in an image.
    Adds a margin around the detected content for better spacing.
    Returns (x_min, y_min, width, height) of content.
    """
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None  # No content detected

    x, y, w, h = cv2.boundingRect(np.vstack(contours))

    # Find the leftmost content pixel
    x_min = min([cv2.boundingRect(cnt)[0] for cnt in contours])

    # Expand bounding box by margin, ensuring it stays within bounds
    x_min = max(0, x_min - margin)
    y = max(0, y - margin)
    w = min(image.width - x_min, w + 2 * margin)
    h = min(image.height - y, h + 2 * margin)

    return x_min, y, w, h

def add_border_and_filename(pdf_path, margin=20, border_color="black", border_width=3, corner_radius=15):
    """
    Processes a single-page PDF:
    - Adds a rounded border around detected content.
    - Aligns filename to the **leftmost content**.
    - Overwrites the original file.
    """
    filename = os.path.basename(pdf_path).replace(".pdf", "")
    images = convert_from_path(pdf_path, dpi=300)

    if len(images) != 1:
        print(f"❌ Skipping {pdf_path}: This script only processes single-page PDFs.")
        return

    img = images[0]
    bbox = detect_content_region(img, margin)

    if bbox:
        x_min, y, w, h = bbox  # Use x_min for actual leftmost content alignment
        draw = ImageDraw.Draw(img)

        # Draw rounded rectangle
        draw.rounded_rectangle([x_min, y, x_min + w, y + h], outline=border_color, width=border_width, radius=corner_radius)

        # Add filename text **aligned to the leftmost content**
        try:
            font = ImageFont.truetype("Times New Roman Bold.ttf", 36)  # Bold Times New Roman, 36pt
        except:
            font = ImageFont.load_default()  # Fallback if Times New Roman is missing

        text_bbox = draw.textbbox((0, 0), filename, font=font)  # Get text size
        text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]

        text_x = x_min + 24  # Align filename **to the leftmost content pixel**
        text_y = max(12, y - text_h - 10)  # Place slightly above the border

        draw.text((text_x, text_y), "", fill=border_color, font=font)  # Draw text

    # Overwrite the original file
    img.save(pdf_path, "PDF")
    print(f"✅ Processed: {pdf_path}")

def process_all_pdfs_in_directory():
    """
    Finds all PDFs in the current directory, sorts them alphabetically, and processes each.
    """
    pdf_files = sorted([f for f in os.listdir() if f.endswith(".pdf")])

    if not pdf_files:
        print("❌ No PDF files found in the directory.")
        return

    for pdf in pdf_files:
        add_border_and_filename(pdf)


process_all_pdfs_in_directory()
