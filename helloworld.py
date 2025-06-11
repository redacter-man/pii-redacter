import fitz
import zipfile
import os
from rich.console import Console

console = Console()

# Define the path to your zip file and the extract destination
if not os.path.exists("Masking/"):
    zip_path = 'Masking.zip'
    extract_path = '.'

    # Open the zip file and extract its contents
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    console.print(f"Files extracted to '{extract_path}'")

    for file in os.listdir('Masking'):
        print(file)

# Open the PDF file
pdf1 = 'Masking/Mask1.pdf'
pdf2 = 'Masking/Mask2.pdf'
doc1 = fitz.open(pdf1)
doc2 = fitz.open(pdf2)

# Loop through pages and extract text
for doc in [doc1, doc2]:
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)  # Load the page
        text = page.get_text()          # Extract text
        print(f"--- Page {page_num + 1} ---")
        print(text)
    doc.close()

