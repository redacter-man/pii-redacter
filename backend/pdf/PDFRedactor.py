import os
import shutil
import pymupdf
from datetime import datetime
from .PageData import Document, Token, pymupdf_to_document
from .PiiDetector import PiiDetector
from .PDFAdapter import PDFAdapter
from .logger_config import logger


class PDFRedactor:
    """Handles PDF redaction using the new token-based data model"""

    @staticmethod
    def process_single_pdf(input_path: str, output_path: str = None) -> str:
        """
        Process a single PDF file for PII redaction.
        
        Args:
            input_path: Path to the input PDF file
            output_path: Path for the redacted PDF (optional, will be auto-generated if None)
            
        Returns:
            Path to the output directory containing all processed files
        """
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.join(os.path.dirname(__file__), "output", f"{pdf_name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Copy input PDF to output directory
        input_copy_path = os.path.join(output_dir, f"{pdf_name}.pdf")
        shutil.copy2(input_path, input_copy_path)
        
        # Determine output path for redacted PDF
        if output_path is None:
            output_path = os.path.join(output_dir, f"redacted_{pdf_name}.pdf")
        
        logger.info(f"Processing PDF: {pdf_name}")
        logger.info(f"Output directory: {output_dir}")
        
        # Load and process the PDF
        pdf_doc = pymupdf.open(input_path)
        
        if not pdf_doc.is_pdf:
            raise ValueError(f"Error: Document at path '{input_path}' is not a PDF!")
        
        # Check if it's an image-based PDF
        is_image_pdf = PDFRedactor._is_image_pdf(pdf_doc)
        
        logger.info(f"'{pdf_name}' loaded successfully: "
                   f"first page size: {pdf_doc[0].rect.width:.2f} x {pdf_doc[0].rect.height:.2f} points")
        
        if is_image_pdf:
            logger.info(f"'{pdf_name}' is likely an image-based PDF. Activating OCR!")
            document = PDFAdapter.google_doc_to_document(input_path, use_cache=True)
        else:
            logger.info(f"'{pdf_name}' is likely a text-based PDF. Using PyMuPDF parsing!")
            document = pymupdf_to_document(pdf_doc)
        
        # Detect PII
        logger.info("Detecting PII in document...")
        pii_tokens = PiiDetector.detect_pii_in_document(document)
        
        # Log PII statistics
        stats = PiiDetector.get_pii_statistics(document)
        logger.info(f"PII Detection Results: {stats}")
        
        # Save tokens and document text
        PDFRedactor._save_processing_files(document, pii_tokens, output_dir)
        
        # Apply redactions
        PDFRedactor._apply_redactions(pdf_doc, pii_tokens, output_path)
        
        # Close the PDF document
        pdf_doc.close()
        
        logger.info(f"Processing complete. Output saved to: {output_dir}")
        return output_dir

    @staticmethod
    def _is_image_pdf(pdf_doc) -> bool:
        """Check if PDF is image-based (no extractable text)"""
        first_page = pdf_doc[0]
        text = first_page.get_text()
        return not text.strip()

    @staticmethod
    def _save_processing_files(document: Document, pii_tokens: list, output_dir: str):
        """Save processing files (tokens, PII, document text)"""
        
        # Save all tokens
        tokens_file = os.path.join(output_dir, "tokens.txt")
        with open(tokens_file, 'w', encoding='utf-8') as f:
            for token in document.all_tokens:
                pii_info = f" [PII: {token.detected_as}]" if token.detected_as else ""
                confidence_info = f" [conf: {token.confidence}]" if token.confidence else ""
                f.write(f"'{token.text}'{pii_info}{confidence_info} (page {token.page_index}, bbox: {token.bbox})\n")
        
        # Save PII tokens only
        pii_file = os.path.join(output_dir, "pii.txt")
        with open(pii_file, 'w', encoding='utf-8') as f:
            for token in pii_tokens:
                f.write(f"'{token.text}' detected as {token.detected_as} (page {token.page_index}, bbox: {token.bbox})\n")
        
        # Save full document text
        document_text_file = os.path.join(output_dir, "document_text.txt")
        with open(document_text_file, 'w', encoding='utf-8') as f:
            f.write(document.full_text)
        
        logger.info(f"Processing files saved to {output_dir}")

    @staticmethod
    def _apply_redactions(pdf_doc, pii_tokens: list, output_path: str):
        """Apply redactions to the PDF based on PII tokens"""
        
        # Group PII tokens by page
        pii_by_page = {}
        for token in pii_tokens:
            page_idx = token.page_index
            if page_idx not in pii_by_page:
                pii_by_page[page_idx] = []
            pii_by_page[page_idx].append(token)
        
        # Apply redactions page by page
        for page_idx, tokens in pii_by_page.items():
            if page_idx >= len(pdf_doc):
                logger.warning(f"Page index {page_idx} is out of bounds for PDF with {len(pdf_doc)} pages")
                continue
                
            page = pdf_doc[page_idx]
            
            for token in tokens:
                # Apply redaction using bounding box
                rect = [token.bbox.x0, token.bbox.y0, token.bbox.x1, token.bbox.y1]
                
                # Validate bounding box is within page bounds
                page_width = page.rect.width
                page_height = page.rect.height
                
                if not (0 <= token.bbox.x0 < token.bbox.x1 <= page_width and 
                       0 <= token.bbox.y0 < token.bbox.y1 <= page_height):
                    logger.warning(f"Redaction bbox {rect} is out of bounds for page {page_idx} "
                                 f"size {page_width:.2f}x{page_height:.2f}. Operation skipped!")
                    continue
                
                # Add redaction annotation
                page.add_redact_annot(rect, fill=(0, 0, 0))
                logger.debug(f"Added redaction for '{token.text}' ({token.detected_as}) on page {page_idx}")
            
            # Apply all redactions for this page
            page.apply_redactions()
        
        # Save the redacted PDF
        pdf_doc.save(output_path, garbage=4, deflate=True)
        logger.info(f"Redacted PDF saved to: {output_path}")

    @staticmethod
    def redact_by_bounding_box(page, bbox, fill_color=(0, 0, 0)):
        """Helper method to redact content using bounding box coordinates"""
        rect = [bbox.x0, bbox.y0, bbox.x1, bbox.y1]
        page.add_redact_annot(rect, fill=fill_color)

    @staticmethod
    def redact_by_text(page, text_to_redact: str):
        """Helper method to redact text by searching for it on the page"""
        instances = page.search_for(text_to_redact)
        for inst in instances:
            page.add_redact_annot(inst, fill=(0, 0, 0))