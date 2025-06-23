import os, math
import pymupdf
from typing import List
from .GoogleDocumentAI import request_google_ocr, load_document_from_json, save_document_as_json
from .DocumentData import DocumentData, PageData, Token, TextSegment, BoundingBox

from pdf.logger_config import logger

# If it's alright, we should probably start moving stuff here
# 1. google ocr to our data model
# 2. pymupdf ocr to our data model, etc. In the future if they want to do tesseract they ake 
class PDFAdapter:


  

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

  
  # NOTE: Functions for logging parsed tokens and parsed PIIs should probably be in PDF redactor in order to centralize things


  ##########
  # Google Document AI Related Code
  ##########   
  def convert_bounding_poly(bounding_poly, page_width: float, page_height: float) -> BoundingBox:
    """Converts a bounding_poly from Google DocAI API to a bounding box that we support.

    Args:
        bounding_poly (_type_): An object returned by Google DocAI API that dictates the vertices of the polygon that encloses this token.
        page_width (float): Width of the pdf page that contains this token
        page_height (float): Height of the pdf page that contains this token.

    Returns:
        BoundingBox: A bounding box equivalent of the bounding polygon

    Note: When Google DocAI does OCR, it renders our pdf pages as images, on a different scale factor.
    So redacting the vertices that it gives us won't work unless we know their scale factor. We don't, that's 
    why google gave the normalized_vertices, which tell us the exact percentage of wherer something is, and then 
    we'll convert that back into PDF user units for redaction.

    TODO: Our implementation assumes that the pdf pages being OCR-ed by google are perfectly axis-aligned, meaning 
    that it's perfectly horizontal and vertical, no rotation or skew to the image. Whilst that's great 
    for our current implementation, in the real world there could be some tilt and rotation. You can learn more 
    about how to fix this within one of our write-ups, it's actually pretty easy. It's just more about understanding the rationale
    rather than writing the code.
    """
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

  def google_doc_to_data(pdf_doc: pymupdf.Document, pdf_path: str, use_cache=True) -> DocumentData:
    """Makes a google OCR request and turns the data into what we need for our workflow

    Args:
        pdf_doc (pymupdf.Document): PDF document itself
        pdf_path (str): Path to the pdf document

    Returns:
        DocumentData: Data for the pdf document in our custom form

    Note: Are \n and special characters like that going to interfere with our regexes? Maybe.
    I mean in general you expect the PIIs in a document such as a credit card number or account number 
    to be all in one line rather than across lines. I think you can be fine with letting things be for that.
    If it comes up in the future, know that you'd need to get rid of them and try to re-calculate indices, and 
    that seems like a hassle. Also there's probably a way to deal with this without modifying the original document text.
    """

    # Setting up variables for caching logic
    cache_dir = os.path.join(os.path.dirname(__file__), "test_data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    json_file_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
    cache_path = os.path.join(cache_dir, json_file_name)
    doc = None  

    # If we want to try to used a cached api response instead of requesting google directly
    if use_cache: 
       if os.path.isfile(cache_path):
        logger.info(f"Cached JSON file FOUND at '{cache_path}'. Loading it as document!")
        doc = load_document_from_json(cache_path)
       else:
        logger.info(f"Cached JSON file NOT FOUND at '{cache_path}'. Fallback activated, querying Google OCR!")
        doc = request_google_ocr(pdf_path)
        save_document_as_json(doc, cache_path)
    else:
      #  Else make a network request to google directly
       logger.info(f"Directly requesting Google OCR to analyze pdf at '{pdf_path}'.")
       doc = request_google_ocr(pdf_path)
       save_document_as_json(doc, cache_path)

    pages = []
    for index, page in enumerate(doc.pages):
      tokens_per_page = []
      for token in page.tokens:
        # Calculate the token text and skip empty tokens
        token_text = PDFAdapter.extract_text_from_text_anchor(token.layout.text_anchor, doc.text)
        if not token_text.strip():
          continue
        parsed_token = Token(
          text=token_text,
          bbox=PDFAdapter.convert_bounding_poly(token.layout.bounding_poly, pdf_doc[index].rect.width, pdf_doc[index].rect.height),
          # Note: They are similar in structure. I guess you could leave Google's textsegment alone, but since I convert the text segments 
          # for PyMuPDF, you want to keep consistency.
          text_segments=[TextSegment(start_index=t.start_index, end_index=t.end_index) for t in token.layout.text_anchor.text_segments],
        )
        tokens_per_page.append(parsed_token)
      
      # Create PageData object for the current page and add it to our pages list
      page_data = PageData(
        tokens=tokens_per_page
      )
      pages.append(page_data)

    logger.info("Successfully parsed Google DocAI API Response, returning document data!")
    return DocumentData(pages=pages, full_text=doc.text)

  ##########
  # PyMuPDF Related Code
  ##########
  def pymupdf_to_data(doc: pymupdf.Document) -> DocumentData:
    """Parses a PyMuPDF document, reconstructing its full text and assigning start/end indices for each token (word) relative to where it's located in the tex.
    
    Args:
        doc (pymupdf.Document): The PyMuPDF document object that we're parsing text from

    Returns:
        DocumentData: A custom data model containing the reconstructed full document text and a list of PageData objects, each holding its parsed tokens.
        
    Notes on Text Reconstructiona dn Indexing:
    - **Reconstruction:** PyMupDF's `get_text("words")` provides individual words and their bounding boxes. 
      To form the `DocumentData.full_text`, these words are concatenated.
    - **Spacing:** A single space (" ") is deliberately inserted between each word. This is vital for:
      - **Regex Accuracy and PII detection:** Some regexes are going to rely on spaces e.g. credit card numbers. Also 
      also it's necessary in order to actually re-construct something at least similar to the original text.
      - **Named Entity Recognition:** NER models are typically trained on text that have word separation, which makes spacing optimal. 
    - **Indexing:** The `start_index` and `end_index` for each token reflect it's exact span within the `DocumentData.full_text`. 
      The `end_index` is exclusive (half-open). The indexing logic correctly accounts for the inserted spaces, ensuring that `token.text_segments`
      accurately points to the word's contents only.

    Example Walkthrough:
    document_text = "I ate three pizzas."
      tokens = ["I" , "ate", "three", "pizzas."]
      1. {start=0, end=1}; notice that "end" is just the length of the string. Now index=1 should point at some empty space. That's when you would concatenate an empty space at the end 
        of the document text. So when you update document_text, do document_text += f"{token_text} ", which is the token's text and a space at the end.
        The document_text = "I "
      2. {start=end+1=2, end=start+len(token_text)=5}; notice that start is just start=end+1. Then notice how end is just end=start+len(token). Now the end index should point at an empty space like it always does.
        To make that happen, you will do document_text += f"{token_text} ". Now the document_text = "I ate "
      3. {start=end+1=6, end=start+len(token_text)=11}, concatenate like document_text += token_text + " ", which is equivalent to what we've done earlier
      4. {start=end+1=12, end=start+len(token_text)=19}. I guess you could still concatenate the whitespace at the end, or choose not to. It doesn't really matter since 
      the application isn't going to be accessing the whitespace position after the last letter of the last token.
    """
    document_text = ""
    page_data_list = []
    for page_num, page in enumerate(doc):
      # Using get_text("words") returns a list of lists:
      # [x0,y0,x1,y1, "word", block_no, line_no, word_no]
      tokens = page.get_text("words")
      parsed_tokens = []
      start = 0 # represents the start pointer
      end = 0 # represents the end pointer 
      for token_info in tokens:
        token_text = token_info[4]
        if token_text.strip() == "": # Skip any words/tokens that don't have meaningful text.
          continue

        end = start + len(token_text)
        segment = TextSegment(
          start_index=start,
          end_index=end
        )
        document_text += token_text + " "
        parsed_tokens.append(Token(
          text=token_text,
          bbox=BoundingBox(
            x0=round(token_info[0], 2),
            y0=round(token_info[1], 2),
            x1=round(token_info[2], 2),
            y1=round(token_info[3], 2)
          ),
          text_segments=[segment]
        ))

        start = end + 1

      page_data_list.append(PageData(
        tokens=parsed_tokens
      ))
      
    return DocumentData(pages=page_data_list, full_text=document_text)