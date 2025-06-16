import pymupdf, os
from .PageData import pymupdf_to_unified, PageData, BoundingBox

"""
This module provides PDF redaction and conversion utilities using PyMuPDF.

Coordinate Systems:
- PDF standard coordinates: origin (0, 0) is **bottom-left**.
- MuPDF (fitz) coordinates: origin (0, 0) is **top-left**.
- 1 point = 1/72 inch.

Redaction Tips:
- Use `page.add_redact_annot(rect, fill=(0, 0, 0))` for black-box redactions.
- Apply redactions using `page.apply_redactions()`.
- Don't forget to save the pdf to actually apply changes to disk

Rectangle Formats:
- Rect-like: [x0, y0, x1, y1]
- Quad-like: [ [x0, y0], [x1, y1], [x2, y2], [x3, y3] ]
- Precision: 5 decimal places is practical max.
"""


class PDFProcessor:
  """
  Dynamically allocated reference to a PDF document. This class handles all the PDF related operations
  that we need. Operations such as:
    1. Loading in a PDF from a specific path.
    2. Extracting the text on a given PDF.
    3. Handling redacting areas of content on a PDF.
    4. Converting a page on the pdf into an image or vice versa and updating the current pdf page.

  Note: Once done processing the pdf, please call the close() method to free the allocated memory.
  """

  def __init__(self, pdf_path: str, output_path: str):
    # TODO: Log when pdf is opened successfully, log metadata about the pdf as well

    if not os.path.isfile(pdf_path):
      raise FileNotFoundError(f"No file found at path '{pdf_path}' !")
    self.pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)

    if not self.pdf_doc.is_pdf:
      raise ValueError(
        f"Error: Document at path '{pdf_path}' was opened, but it wasn't a pdf!"
      )

    self.output_path = output_path

  def extract_text(self, page):
    """Extracts text from every page in the pdf document

    Returns:
        _type_: _description_

    Note: When there's no text, the "blocks" field will be an empty array.
    But note that the blocks field may have something else like a block as an image.
    Our pymupdf_to_unified function at least takes care of that. So at least
    when the redactor is getting data, it's in this unified form.
    """

    page_text = page.get_text("dict")
    page_text = pymupdf_to_unified(page_text)

    return page_text

  def redact_pdf_helper(self, page: pymupdf.Page, rect):
    """Helper function for redacting content from a PDF page

    Pdf redactions happen in two steps:
    1. First identify areas whose content should be removed from the document, highlights what'll be removed. The is the add_redact_annot() function.
    2. Second, apply the redactions

    Note: Technically the last step is saving those changes to the PDF document in disk.
    It seemes that saving after every redaction is kind of inefficient.
    """
    page.add_redact_annot(rect, fill=(0, 0, 0))
    page.apply_redactions()

  def redact_pdf_text(self, page: pymupdf.Page, text_to_redact: str):
    """Redacts text given a page and text on the page we want to redact

    Args:
        page (pymupdf.Page): A page associated with self.pdf_doc.
        text_to_redact (str): The text on the given page that we want to redact.
    """
    instances = page.search_for(text_to_redact)
    for inst in instances:
      self.redact_pdf_helper(page, inst)

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
    self.redact_pdf_helper(page, rect)

  # Note:
  # May need these later:

  # def convert_image_to_pdf(self):
  #   pass

  # def convert_pdf_to_image(self, page: pymupdf.Page,  ):
  #   # Create a zoom matrix, which just means you're going to get better resolution on the resulting image
  #   zoom_x = 2.0
  #   zoom_y = 2.0
  #   zoom_matrix = pymupdf.Matrix(zoom_x, zoom_y)
  #   pixel_map = page.get_pixmap(matrix=zoom_matrix)
  #   return pixel_map

  def get_pages(self):
    for page in self.pdf_doc:
      yield page

  def save_and_close(self):
    """Saves and closes the opened pdf
    Args:
        output_path (str, optional): The output path that ou want to save the modified PDF to
    """
    if self.output_path:
      self.pdf_doc.save(self.output_path)
    else:
      self.pdf_doc.save()
    self.pdf_doc.close()
