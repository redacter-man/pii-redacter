import os, math
import pymupdf
from typing import List
from .GoogleDocumentAI import request_google_ocr, load_document_from_json, save_document_as_json
from .PageData import BoundingBox, Token, Page, Document, convert_bounding_poly, extract_text_from_text_anchor, google_doc_to_document
from pdf.logger_config import logger

# If it's alright, we should probably start moving stuff here
# 1. google ocr to our data model
# 2. pymupdf ocr to our data model, etc. In the future if they want to do tesseract they ake 
class PDFAdapter:
    """Adapter for converting different PDF parsing outputs to our unified Document format"""

    ##########
    # Google Document AI Related Code
    ##########   

    @staticmethod
    def google_doc_to_document(pdf_path: str, use_cache: bool = True) -> Document:
        """
        Makes a google OCR request and turns the data into our Document format
        
        Args:
            pdf_path: Path to the PDF file
            use_cache: Whether to use cached results if available
            
        Returns:
            Document object with all pages and tokens
        """
        pdf_doc: pymupdf.Document = pymupdf.open(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # Setup cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), "test_data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        json_file_name = os.path.splitext(os.path.basename(pdf_path))[0] + ".json"
        cache_path = os.path.join(cache_dir, json_file_name)

        # Get or load Google Document AI response
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

        # Convert to our Document format
        document = google_doc_to_document(doc, pdf_doc)
        
        # Close the PDF document
        pdf_doc.close()
        
        logger.info("Successfully parsed Google DocAI API Response, returning Document")
        return document

    ##########
    # PyMuPDF Related Code
    ##########
    
    @staticmethod
    def pymupdf_to_document(doc: pymupdf.Document) -> Document:
        """
        Convert PyMuPDF document to our Document format
        
        Args:
            doc: PyMuPDF document object
            
        Returns:
            Document object with all pages and tokens
        """
        from .PageData import pymupdf_to_document
        return pymupdf_to_document(doc)

    @staticmethod
    def is_image_pdf(pdf_path: str) -> bool:
        """
        Check if a PDF is image-based (no extractable text)
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if the PDF appears to be image-based
        """
        pdf_doc = pymupdf.open(pdf_path)
        first_page = pdf_doc[0]
        text = first_page.get_text()
        pdf_doc.close()
        return not text.strip()