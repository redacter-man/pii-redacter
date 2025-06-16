from paddleocr import PaddleOCR, PPStructureV3
import pymupdf, os
from PIL import Image, ImageDraw
import io


class OCREngine:
  # You'd run the two pass system here
  # I suggest starting with setting up PaddleOCR to do hand-written recognition

  '''
  PaddleOCR Notes

  Tesseract-OCR Notes:
  Tesseract is a lot more friendly in the sense that you can just pass an image of the pdf page, 
  and then tesseract does the rest for text recognition. That's useful, but i'm not seeing an option to 
  do something similar with PaddleOCR?

  Maybe I should try printed OCR first? 
  '''
  def __init__(self):
    self.printed_ocr_engine = None
    self.handwritten_ocr_engine = None
    self.paddle_ocr_engine = PaddleOCR(
      ocr_version="PP-OCRv5", 
      use_doc_orientation_classify=False, 
      use_doc_unwarping=False, 
      use_textline_orientation=False
    )

  # 1. Convert PDF page to png
  # 2. Save PNG to disk
  def apply_paddle_ocr(self, img_arr):
    result = self.paddle_ocr_engine.predict(img_arr)
    for res in result:
      res.print()

    

    

  def apply_printed_OCR(self, page: pymupdf.Page):
    mat = pymupdf.Matrix(2, 2) # if taking too much room, try 2, 2 zoom
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    pass