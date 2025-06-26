from typing import List
import zipfile, os
from pdf.PIIDetector import PIIDetector
from pdf.PDFAdapter import PDFAdapter
from .logger_config import logger
from .DocumentData import DocumentData, Token, BoundingBox
import pymupdf


class PDFRedactor:
  """A class with static methods that will do the orchestration between the helper classes."""

  def process_single_pdf(work_dir, pdf_path: str) -> None:
    """Redacts a single pdf file"""

    # PDF existence check, load it in, and make sure we loaded in a pdf
    if not os.path.isfile(pdf_path):
      raise FileNotFoundError(f"No file found at path '{pdf_path}' !")
    pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)
    if not pdf_doc.is_pdf:
      raise ValueError(
        f"Error: Document at path '{pdf_path}' was opened, but it wasn't a pdf!"
      )
    os.makedirs(work_dir, exist_ok=True)
    
    # pdf name with extension
    pdf_name = os.path.basename(pdf_path)
    is_image_pdf = PDFRedactor.is_image_pdf(pdf_doc)

    logger.info(f"'{pdf_name}' found and loaded successfully!")
    if is_image_pdf:
      logger.info(f"'{pdf_name}' is likely an image-based PDF. Activating OCR!")
      doc_data: DocumentData = PDFAdapter.google_doc_to_data(pdf_path, use_cache=True)
    else:
      # Else text-based pdf, so parse the text from it
      logger.info(f"'{pdf_name}' is likely an text-based PDF. Parsing!")
      doc_data: DocumentData = PDFAdapter.pymupdf_to_data(pdf_doc)
    
    logger.info(f"PDF Data Obtained!")

    
    pii_tokens = PIIDetector.get_pii_tokens(work_dir, doc_data)    
    for pii_token_object in pii_tokens:
      page_index, token = pii_token_object
      pdf_page = pdf_doc[page_index]
      PDFRedactor.redact_pdf_content(pdf_page, token.bbox)  
      pdf_page.apply_redactions()
        
    pdf_doc.save(os.path.join(work_dir, pdf_name), garbage=4, deflate=True)
    pdf_doc.close()
  
    
  def redact_pdf_content(page: pymupdf.Page, bbox: BoundingBox) -> None:
    """Redacts content on a pdf, given a page and information about the bounding box we want to redact.
    Args:
        page (pymupdf.Page): Page that we're redacting content on.
        x (_type_): X coordinate of the top left corner of the bounding box.
        y (_type_): Y coordinate of the top left corner of the bounding box.
        length (_type_): Length of the bounding box.
        width (_type_): Width of the bounding box.
    """
    rect = [
      bbox.x0,
      bbox.y0,
      bbox.x1,
      bbox.y1,
    ]
    page_width = page.rect.width
    page_height = page.rect.height

    if not (0 <= bbox.x0 < bbox.x1 <= page_width and 0 <= bbox.y0 < bbox.y1 <= page_height):
      logger.warning(f"Redaction bbox {rect} is out of bounds for page size {page_width:.2f}x{page_height:.2f}. Operation skipped!")
      return

    PDFRedactor.redact_pdf_helper(page, rect)

  def redact_pdf_content(page: pymupdf.Page, bbox: BoundingBox) -> None:
    """Redacts content on a pdf, given a page and information about the bounding box we want to redact.
    Args:
        page (pymupdf.Page): Page that we're redacting content on.
        x (_type_): X coordinate of the top left corner of the bounding box.
        y (_type_): Y coordinate of the top left corner of the bounding box.
        length (_type_): Length of the bounding box.
        width (_type_): Width of the bounding box.

    Note: You still have to call page.apply_redactions() after you're done. We'll leave this 
    up to the calling function since we'll expect multiple redactions per page, and it's more 
    efficient to apply all of the redactions at the end, rather than one by one.
    """
    rect = [
      bbox.x0,
      bbox.y0,
      bbox.x1,
      bbox.y1,
    ]
    page_width = page.rect.width
    page_height = page.rect.height

    if not (0 <= bbox.x0 < bbox.x1 <= page_width and 0 <= bbox.y0 < bbox.y1 <= page_height):
      logger.warning(f"Redaction bbox {rect} is out of bounds for page size {page_width:.2f}x{page_height:.2f}. Operation skipped!")
      return
    page.add_redact_annot(rect, fill=(0, 0, 0))
  
  def is_image_pdf(pdf_doc: pymupdf.Document) -> bool:
    """Given a PDF, return whether it's an image-based PDF or not
    
    Note: This uses a heuristic and some assumptions. We just inspect the first page of the pdf, 
    and if that page has text, we'll assume the entire PDF is text based. Else, the first page 
    contains no text, so the page is probably an image. Then we'll assume the entire pdf is image-based.
    """
    first_page = pdf_doc[0]
    text = first_page.get_text()
    if not text.strip():
      return True
    else:
      return False