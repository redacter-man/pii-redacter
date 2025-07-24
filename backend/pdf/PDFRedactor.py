from typing import List
import zipfile, os, shutil
from pdf.PIIDetector import PIIDetector
from pdf.PDFAdapter import PDFAdapter
from .logger_config import logger
from .DocumentData import DocumentData, BoundingBox
from db import SessionLocal, File
import fitz


class PDFRedactor:
  """A class with static methods that will do the orchestration between the helper classes."""

  def process_zip(work_dir: str, zip_path: str):
    """
    Processes all PDF files in a zip archive, redacts them, and outputs a new zip with redacted PDFs.
    Assumes the zip file only has one level (no subdirectories).
    """
    import os, zipfile, shutil
    from db import SessionLocal, File

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    input_dir = os.path.join(work_dir, "input")
    output_dir = os.path.join(work_dir, "output")
    os.mkdir(input_dir)
    os.mkdir(output_dir)

    # Extract all files from the zip (flat structure)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(input_dir)

    # List all PDFs in the work_dir (no recursion)
    pdf_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]

    # Process and redact each PDF
    for pdf_path in pdf_files:
        try:
            PDFRedactor.process_single_pdf(output_dir, pdf_path)
        except Exception as e:
            logger.error(f"File Processing Error - {str(e)}")

    # Collect original and redacted PDFs only for database logging
    # Create zip file with all redacted pdfs
    base_name = os.path.splitext(os.path.basename(zip_path))[0]
    redacted_zip_path = os.path.join(work_dir, f"masked-{base_name}.zip")
    with zipfile.ZipFile(redacted_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
      session = SessionLocal()
      for file in os.listdir(output_dir):
        full_path = os.path.join(output_dir, file)
        zipf.write(full_path, arcname=file)  # <-- Save file to zip
        session.add(File(path=full_path, status=True))
      session.commit()
      session.close()
    

  def process_single_pdf(work_dir, pdf_path: str) -> None:
    """Redacts a single pdf file"""

    # 1. PDF existence check, load it in, and make sure we loaded in a pdf
    if not os.path.isfile(pdf_path):
      raise FileNotFoundError(f"No file found at path '{pdf_path}' !")
    pdf_doc: fitz.Document = fitz.open(pdf_path)
    if not pdf_doc.is_pdf:
      raise ValueError(
        f"Error: Document at path '{pdf_path}' was opened, but it wasn't a pdf!"
      )

    # pdf name without extension
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    is_image_pdf = PDFRedactor.is_image_pdf(pdf_doc)

    if is_image_pdf:
      logger.info(f"'{pdf_name}' is likely an image-based PDF. Activating OCR!")
      doc_data: DocumentData = PDFAdapter.google_doc_to_data(pdf_doc, pdf_path, use_cache=True)
    else:
      # Else text-based pdf, so parse the text from it
      logger.info(f"'{pdf_name}' is likely an text-based PDF. Parsing!")
      doc_data: DocumentData = PDFAdapter.fitz_to_data(pdf_doc)

    pii_tokens = PIIDetector.get_pii_tokens(work_dir, doc_data)
    for pii_token_object in pii_tokens:
      page_index, token = pii_token_object
      pdf_page = pdf_doc[page_index]
      PDFRedactor.redact_pdf_content(pdf_page, token.bbox)
      pdf_page.apply_redactions()
    
    # redacted version to the work directory
    pdf_doc.save(os.path.join(work_dir, f"masked-{pdf_name}.pdf"), garbage=4)
    pdf_doc.close()

  def redact_pdf_content(page: fitz.Page, bbox: BoundingBox) -> None:
    """Redacts content on a pdf, given a page and information about the bounding box we want to redact.
    Args:
        page (fitz.Page): Page that we're redacting content on.
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

  def is_image_pdf(pdf_doc: fitz.Document) -> bool:
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