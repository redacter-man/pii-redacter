import fitz
import zipfile
import os
from rich.console import Console
import pytesseract
from PIL import Image
import io

console = Console()

def unzip_files() -> None:
    # unzip file if not already unzipped
    if not os.path.exists("Masking/"):
        zip_path = 'Masking.zip'
        extract_path = '.'

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        console.print(f"Files extracted to '{extract_path}'")

        for file in os.listdir('Masking'):
            print(file)

def open_docs() -> None:
    # Open the PDF files
    docs = []
    for file in os.listdir("Masking"):
        docs.append(fitz.open("Masking/" + file))
        print(type)
    return docs

def ocr_docs(docs) -> None:
    for i, doc in enumerate(docs):
        console.print(f"Doc {i + 1}:")
        for j, page in enumerate(doc):
            console.print(f"Page {j + 1}:")
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)
            print(text)
        doc.close()

def main() -> None:
    # set tesseract path because we aren't allowed to change our env vars :(((
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    unzip_files()
    docs = open_docs()
    ocr_docs(docs)

if __name__ == "__main__":
    main()