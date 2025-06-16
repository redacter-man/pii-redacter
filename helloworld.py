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
    '''
    
    Step by Step Explanation:
    1. Iniitalize a "data" array. This array will contain the data 
    2. Iterate through each pdf document that we've been given
      a. Iterate through every page in the given pdf document
        - Here we are manipulating the image to zoom it in a think
        - Pixel maps are rectangular sets of pixels, with each pixel being described as a number of bytes defining its color (rgb) and then an optional alpha byte 
          describing its transparency. Here we're just getting a pixel map of the document page, so if we were to imagine this, it's like having a very big matrix, with each element 
          in the matrix representing a color pixel from the pdf page. I think that's the way to conceptualize it and it's probably the way they implemented it. 
        - We then convert this pixel map into a sequence of bytes to make it look like a .png, and open that in PIL. The reason we're doing this in the first place is because our Python
        API for Tesseract can't read a pdf and OCR it directly. However, it's able to do OCT with something like a .png, so we have to do the work for that conversion.
        
        - Read the text from the image into a dictionary containing all of our data. Let's go and review each field and what it means:
          1. level: The OCR granularity level. E.g. page, block, paragraph, line, and evne word.
          2. page_num: Page number if multiple pages are processes
          3. block_num: Id of the text block on the page, and a block could be a paragraph, table cell, etc.
          4. par_num: Paragraph number within the block
          5. line_num: Line number within the paragraph.
          6. word_num: word number within the line
          7. left: X coordinate of the top left corner of the bounding box
          8. top: Y coordinate of the top left corner of the bounding box
          9. width: Width of the bounding box
          10. height: Height of the bounding box
          11. conf: OCR confidence score (0-100), -1 means it's not applicable
          12. text: The actual text that it detected.

    Example Data:
    {
        'level':     [1, 2, 3, 4, 5, 5],
        'page_num':  [1, 1, 1, 1, 1, 1],
        'block_num': [0, 1, 1, 1, 1, 1],
        'par_num':   [0, 1, 1, 1, 1, 1],
        'line_num':  [0, 1, 1, 1, 1, 1],
        'word_num':  [0, 0, 0, 0, 1, 2],
        'left':      [0, 50, 50, 50, 60, 150],
        'top':       [0, 100, 100, 100, 105, 105],
        'width':     [0, 300, 300, 300, 80, 90],
        'height':    [0, 50, 50, 50, 20, 20],
        'conf':      ['-1', '-1', '-1', '-1', '95', '92'],
        'text':      ['', '', '', '', 'Hello', 'World']
    }

    We detected two words "Hello" and "World". The both are at the level 5, which indicates that they are words.
    You can reason that they're within the same page, the same block and paragraph. They're even on the same line, but 
    they're just different words on that line. With "Hello" coming first and "World" second.

    We also attach the pixel map and image that we used to the page data as extra fields as we'll need them later for drawing 
    on those bounding boxes and redacting them. Again all of this is for a single page on the pdf, we provide to do this for all pages.

    Relating to our return type:
      1. dict: Data dictionary for one pdf page
      2. list[dict]: List of data dictionaries, represents the data for an entire pdf with all of its pages
      3. list[list[dict]]: List of elements in step 2, indicating data for all pdfs.
      
    ''' 
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

def redact(data: List[List[dict]]) -> None:
    '''
    Step by Step:
    1. Construct a regex pattern for SSNs.
    2. Iterate through all pdfs.
      a. Iterate through every page in a given pdf
        - Iterate through every word we got on the page
          1. If the word is an SSN, redact it
          2. We will get the original image since that's what we're going to be modifying (possible change this back to a pdf after?). The other solution would be hoping OCR and PyMuPDF use the same mapping, which may not be true.
            It sounds much simpler to just turn the ocred image back into a pdf instead of doing some mickey mouse game
          3. Get the coordinates and dimensions of the word bounding box and draw a rectangle on that image to redact it.
    '''
    
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