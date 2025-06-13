import io
import os
import zipfile

import fitz
import pytesseract
from PIL import Image, ImageDraw
from rich.console import Console
from typing import List
import re

console = Console()

def unzip_files() -> None:
    # Delete the masking directory containing all of our data
    if os.path.exists("Masking/"):
        [os.remove("Masking/" + file) for file in os.listdir("Masking/")]
    os.rmdir("Masking/")

    # Unzip the zip files from zip file; 
    # Note: Clean reset everytime
    zip_path = 'Masking.zip'
    extract_path = '.'
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    console.print(f"Files extracted to '{extract_path}'")
    for file in os.listdir('Masking'):
        print(file)

def open_docs() -> List[fitz.Document]:
    # Open the PDF files
    docs = []
    for file in os.listdir("Masking"):
        docs.append(fitz.open("Masking/" + file))
    return docs

def ocr_docs(docs) -> List[List[dict]]:
    data = []
    for i, doc in enumerate(docs):
        data.append([])
        console.print(f"Doc {i + 1}:")
        for j, page in enumerate(doc):
            console.print(f"Page {j + 1}:")
            mat = fitz.Matrix(2, 2) # if taking too much room, try 2, 2 zoom
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            # dict fields: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
            page_data['pix'] = pix
            page_data['img'] = img
            data[i].append(page_data)
        doc.close()
    return data

def redact(data) -> None:
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    for i, doc in enumerate(data):
        for j, page in enumerate(doc):
            for k, text in enumerate(page['text']):
                if re.match(ssn_pattern, text):
                    print("SSN FOUND: " + text)
                    draw = ImageDraw.Draw(page['img'])
                    x = page["left"][k]
                    y = page["top"][k]
                    w = page["width"][k]
                    h = page["height"][k]
                    
                    # Draw black rectangle to redact
                    draw.rectangle([x, y, x + w, y + h], fill="black")

                    page['img'].save(f"redacted_{i}_{j}.png")



def main() -> None:
    # set tesseract path because we aren't allowed to change our env vars :(((
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    unzip_files()
    docs = open_docs()
    data = ocr_docs(docs)
    redact(data)

if __name__ == "__main__":
    main()