import zipfile, os
from pdf.PiiDetector import PiiDetector
from pdf.PDFAdapter import PDFAdapter
from .logger_config import logger
from .DocumentData import BoundingBox
import pymupdf


class PDFRedactor:
  """A class with static methods that will do the orchestration between the helper classes."""

  def process_single_pdf(pdf_path: str, output_path: str) -> None:
    """Redacts a single pdf file"""

    # PDF existence check, load it in, and make sure we loaded in a pdf
    if not os.path.isfile(pdf_path):
      raise FileNotFoundError(f"No file found at path '{pdf_path}' !")
    pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)
    if not pdf_doc.is_pdf:
      raise ValueError(
        f"Error: Document at path '{pdf_path}' was opened, but it wasn't a pdf!"
      )
    
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    is_image_pdf = PDFRedactor.is_image_pdf(pdf_doc)

    logger.info(f"'{pdf_name}' found and loaded successfully!")
    if is_image_pdf:
      logger.info(f"'{pdf_name}' is likely an image-based PDF. Activating OCR!")
      page_data_list = PDFAdapter.google_doc_to_data(pdf_path, use_cache=True)
      logger.info(f"'PDF Data Obtained'. Now evaluating PIIs!")      
      for index, page in enumerate(pdf_doc):
        page_data = page_data_list[index]
        pii_elements = PiiDetector.detect_page_piis(page_data)
        
        for pii in pii_elements:
          print("PIi: ", pii)
          PDFRedactor.redact_pdf_content(page, pii.bbox)  
          page.apply_redactions()
        
      pdf_doc.save(output_path, garbage=4, deflate=True)
      pdf_doc.close()
      return
    
    logger.info(f"'{pdf_name}' is likely a text-based PDF. Preparing PDF parsing technology!")
    logger.info(f"'PDF Data Obtained'. Now evaluating PIIs!")

    # TODO: Handle the text-based case after you're done making the new data model.
    # Or probably after you're done adjusting everything to fit the new model
    # Save and close the changes; pdf is outputted to the output path now
    
    pdf_doc.save(output_path, garbage=4, deflate=True)
    pdf_doc.close()

  def redact_pdf_content(self, page: pymupdf.Page, bbox: BoundingBox) -> None:
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

    self.redact_pdf_helper(page, rect)

  def redact_pdf_content(self, page: pymupdf.Page, bbox: BoundingBox) -> None:
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