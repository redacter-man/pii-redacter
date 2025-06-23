import os, math
import pymupdf
from typing import List
from .GoogleDocumentAI import request_google_ocr, load_document_from_json, save_document_as_json
from .PageData import BoundingBox, TextElement, TextLine, TextBlock, PageData
from pdf.logger_config import logger

# If it's alright, we should probably start moving stuff here
# 1. google ocr to our data model
# 2. pymupdf ocr to our data model, etc. In the future if they want to do tesseract they ake 
class PDFAdapter:


  ##########
  # Google Document AI Related Code
  ##########   

  # Note: How you'd go about identifying certain elements to redact
  # Well that's almost how it works. Here's the workflow:
  # - Assume you have the full document text and array of tokens.
  # 1. You do a regex for social security numbers and 2 SSNs on two different pages pop up. 
  # 2. You get their indices in the document text. So you know that they're at indices [i, j) and [x, y).
    # - Note: You may get multiple indices for a given element due to complex layouts and whatnot. It doesn't seem to be avoidable, you probably can't finalize it into a single 2-tuple for indices becasue 
    # then you'd need to change the source of truth, which is not a good idea.
  # 3. Then for the locations of patterns that look like credit card numbers, you'll regex the full document text, and get the indices.
  # 4. Now that we have the PIIs and the tokens, we need to redact these piis. To do that, you need the bounding boxes of where they're located inside the page, and to find that you have to look at the tokens.
  # 5. Iterate through all tokens we got:
    # - Iterate through all PIIs we detected and their indices:   
    # - If a given token's indices overlap with a PII's, mark that token for redaction and indicate what PII it was detected as
  # 6. You should now have a list of tokens that were detected as PIIs, or at least they were part of a PII, and so they will be redacted using their bounding_poly info.
  # Note: You should also be able to indicate what page that a token is a part of 

  # Note: If you want your document parser to work with other OCRs like Textract, Azure, or Tesseract-OCR, probably note that at the token/word level 
  # you're probably not going to have multiple segments. That's fine, as long as you're able to accomodate for multiple and understand the limits, it's all good .
  # I mean I guess you could take the segment's start index and last segment's end index but then you could be including new lines and spaces in the token text.

  def convert_bounding_poly(bounding_poly, page_width: float, page_height: float) -> BoundingBox:
    
    # Apply rounding if desired
    # Note: This assumes approximately axis-aligned input image. If you can't make this assumption
    # consider representing all points in the bounding polygon and redacting all four points.
    x0 = round(bounding_poly.normalized_vertices[0].x * page_width, 2)
    y0 = round(bounding_poly.normalized_vertices[0].y * page_height, 2)
    x1 = round(bounding_poly.normalized_vertices[2].x * page_width, 2)
    y1 = round(bounding_poly.normalized_vertices[2].y * page_height, 2)
    return BoundingBox(
      x0=x0,
      y0=y0,
      x1=x1,
      y1=y1
    )
    
  def extract_text_from_text_anchor(text_anchor, document_text: str) -> str:
    """Extracts the text content corresponding to a TextAnchor from the full document
    
    Args:
      text_anchor: The TextAnchor object, which contains text_segments.
      document_text: The completet text content of the document (document.text)
    
    Returns:
      A string containing the content those text segments were enclosing
    """
    if not text_anchor or not text_anchor.text_segments:
       return ""
    extracted_text = ""
    for segment in text_anchor.text_segments:
      start_index = int(segment.start_index)
      end_index = int(segment.end_index)
      # Indices could be out of bounds due to sharding so just make sure we don't get that
      if 0 <= start_index < end_index <= len(document_text):
         extracted_text += document_text[start_index:end_index]
      else:
        logger.warning(f"Text segment indices [{start_index, end_index}] are out of bounds. Getting a partial string")
        # There are a couple of options:
        # 1. Handle error: Here we log it and try to get at least a partial string.
        # 2. You could also just skip it
        extracted_text += document_text[start_index:min(end_index, len(document_text))]
    
    return extracted_text

  def google_doc_to_data(pdf_path: str, use_cache: bool) -> List[PageData]:
    """Makes a google OCR request and turns the data into what we need for our workflow

    Note: This is kind of a hack. Google's Document AI doesn't really nest data in a dictionary like 
    how PyMuPDF does it. What I mean is that I can't just do pages -> blocks -> lines -> tokens and store 
    everything nested like that. To adapt google's data to our own, I'll just make each page have one block, and 
    each block have one line with all the text for that page. The good thing is that this shouldn't really 
    matter to our pii detection code since it doesn't really pay attention to detailed layout stuff, but rather 
    processes tokens straight
    """


    pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    token_file_path = os.path.join(os.path.dirname(__file__), "test_data", pdf_name + ".txt")
    cache_dir = os.path.join(os.path.dirname(__file__), "test_data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    json_file_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
    cache_path = os.path.join(cache_dir, json_file_name)

    doc = None  
    if use_cache: 
       if os.path.isfile(cache_path):
        logger.info(f"Cached JSON file FOUND at '{cache_path}'. Loading it as document!")
        doc = load_document_from_json(cache_path)
       else:
        logger.info(f"Cached JSON file NOT FOUND at '{cache_path}'. Fallback activated, querying Google OCR!")
        doc = request_google_ocr(pdf_path)
        save_document_as_json(doc, cache_path)
    else:
       logger.info(f"Not using cached document. Requesting Google OCR to analyze pdf at '{pdf_path}'.")
       doc = request_google_ocr(pdf_path)
       save_document_as_json(doc, cache_path)

    # Iterate through all pages
    with open(token_file_path, 'w') as token_file:
      document_text = doc.text
      pages = []
      for index, page in enumerate(doc.pages):

        # Original pdf's page width and height are needed to correctly calculate bounding box
        page_width = pdf_doc[index].rect.width
        page_height = pdf_doc[index].rect.height

        tokens_per_page = []
        # Iterate through all tokens in a page
        for token in page.tokens:

          # Calculate the token text and skip empty tokens
          token_text = PDFAdapter.extract_text_from_text_anchor(token.layout.text_anchor, document_text)
          if not token_text.strip():
            continue
          
          token_file.write(repr(token_text) + '\n')

          # Create text element and append it to the array of elements for a given page.
          token = TextElement(
            text=token_text,
            bbox=PDFAdapter.convert_bounding_poly(token.layout.bounding_poly, page_width, page_height),
            confidence=round(token.layout.confidence, 2)
          )
          tokens_per_page.append(token)
        
        # Create page data since we iterated through entire page
        page = PageData(
          blocks=[
            TextBlock(
              lines=[
                TextLine(tokens_per_page, BoundingBox(x0=0,y0=0,x1=0,y1=0), 0)
              ],
              bbox=BoundingBox(x0=0,y0=0,x1=0,y1=0),
              block_id=0
            )
          ],

          # Bounding box data for lines or text blocks literally doesn't matter
          # Dimensions for the actual PDF page doesn't matter. 
          width=0,
          height=0,
          source="GoogleOCR"
        )
        pages.append(page)

      logger.info("Successfully parsed Google DocAI API Response, returning list of page data")
      return pages

  ##########
  # PyMuPDF Related Code
  ##########
  def pymupdf_to_data(doc: pymupdf.Document) -> List[PageData]:
    page_data = []
    for page_num, page in enumerate(doc):
      # Using get_text("words") returns a list of lists:
      # [x0,y0,x1,y1, "word", block_no, line_no, word_no]
      tokens = page.get_text("words")

      processed_words = []
      for t in tokens:
        if t[4].strip() == "": # Skip any words/tokens that don't have meaningful text.
          continue 

        processed_words.append(TextElement(
          text=t[4],
          bbox=BoundingBox(
            x0=round(t[0], 2),
            y0=round(t[1], 2),
            x1=round(t[2], 2),
            y1=round(t[3], 2)
          )
        ))
        
      # Collected all words on page 
      if not processed_words:
        continue
      
      # Create a page with one text blcok, one line that contains all of those processed words
      # Note: Yeah in a later PR we need to re-write this whole thing to ensure we don't have 
      # any redundant data holy crap. Holy unreadable.
      page_data.append(PageData(
         blocks=[
            TextBlock(
               lines=[
                  TextLine(
                     elements=processed_words,
                     bbox=None,
                     line_id=0
                  )
               ],
               bbox=None,
               block_id=0,
               block_type=None
            )
         ],
         width=0,
         height=0,
         source="PyMuPDF"
      ))

    # Return list of pages and their data
    return page_data