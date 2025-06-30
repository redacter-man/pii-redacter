from typing import List
import zipfile, os, shutil
from pdf.PIIDetector import PIIDetector
from pdf.PDFAdapter import PDFAdapter
from .logger_config import logger
from .DocumentData import DocumentData, Token, BoundingBox
import pymupdf


class PDFRedactor:
  """A class with static methods that will do the orchestration between the helper classes."""

  def process_zip(work_dir: str, zip_path: str):
    if not os.path.isfile(zip_path):
      raise FileNotFoundError(f"No zip file found at path '{zip_path}'!")
    os.makedirs(work_dir, exist_ok=True)

     # Extract all files from the zip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
      zip_ref.extractall(work_dir)

    # Find all PDF files in the extracted directory (recursively)
    pdf_files = []
    for root, _, files in os.walk(work_dir):
      for file in files:
        if file.lower().endswith('.pdf'):
          pdf_files.append(os.path.join(root, file))

    for pdf_path in pdf_files:
      try:
        PDFRedactor.process_single_pdf(work_dir, pdf_path)
      except Exception as e:
        logger.error(f"File Processing Error - {str(e)}")
    
    # Collect all redacted PDFs (those starting with 'redacted-')
    redacted_pdfs = []
    for root, _, files in os.walk(work_dir):
      for file in files:
        if file.startswith('redacted-') and file.lower().endswith('.pdf'):
          redacted_pdfs.append(os.path.join(root, file))

    # Create a new zip file with redacted PDFs
    base_name = os.path.splitext(os.path.basename(zip_path))[0]
    redacted_zip_path = os.path.join(work_dir, f"{base_name}-redacted.zip")
    with zipfile.ZipFile(redacted_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
      for pdf in redacted_pdfs:
        arcname = os.path.relpath(pdf, work_dir) # Just prevents us exposing the app's inner directories
        zipf.write(pdf, arcname=arcname)

    logger.info(f"Redacted zip created at: {redacted_zip_path}")

  def process_single_pdf(work_dir, pdf_path: str) -> None:
    """Redacts a single pdf file"""

    # 1. PDF existence check, load it in, and make sure we loaded in a pdf
    if not os.path.isfile(pdf_path):
      raise FileNotFoundError(f"No file found at path '{pdf_path}' !")
    pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)
    if not pdf_doc.is_pdf:
      raise ValueError(
        f"Error: Document at path '{pdf_path}' was opened, but it wasn't a pdf!"
      )

    # pdf name without extension
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    is_image_pdf = PDFRedactor.is_image_pdf(pdf_doc)

    logger.info(f"'{pdf_name}' found and loaded successfully!")
    if is_image_pdf:
      logger.info(f"'{pdf_name}' is likely an image-based PDF. Activating OCR!")
      doc_data: DocumentData = PDFAdapter.google_doc_to_data(pdf_doc, pdf_path, use_cache=True)
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
    
    # Copy original pdf and redacted version to the work directory
    shutil.copy2(pdf_path, os.path.join(work_dir, pdf_name))        
    pdf_doc.save(os.path.join(work_dir, f"{pdf_name}-redacted.pdf"), garbage=4, deflate=True)
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

    if not (
      0 <= bbox.x0 < bbox.x1 <= page_width and 0 <= bbox.y0 < bbox.y1 <= page_height
    ):
      logger.warning(
        f"Redaction bbox {rect} is out of bounds for page size {page_width:.2f}x{page_height:.2f}. Operation skipped!"
      )
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