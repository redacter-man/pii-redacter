'''
Defines data classes that help us standardize the data we get from PyMuPDF, and the OCR library (or multiple) we use.

Data classes in python are just there to store data, not do actual operations. Think of them as types or interfaces that help us know what 
type of data that we're dealing with.
'''
from typing import List, Dict, Optional
from rich.tree import Tree
from dataclasses import dataclass
from rich.console import Console
from rich.tree import Tree

@dataclass
class BoundingBox:
    """Normalized bounding box coordinates. The point (x0, y0) would be the top left corner of a bounding box and (x1, y1) would be the bottom right corner of the bounding box."""
    x0: float
    y0: float 
    x1: float
    y1: float

@dataclass  
class Token:
    """Individual token (word/span level) with position and content information
    - text: The actual text content as a string that was parsed.
    - bbox: Bounding box of the token
    - confidence: An optional OCR confidence score, which will be filled in cases where OCR is applied.
    - detected_as: An optional parameter that is assigned when a Token is detected as a PII. We record 
    what PII we believe it was e.g. 'SSN', 'Routing Number', 'Account Number'.
    - page_index: The page number this token belongs to (0-indexed)
    - token_index: The position of this token within the document text
    """
    text: str
    bbox: BoundingBox
    confidence: Optional[float] = None
    detected_as: Optional[str] = None
    page_index: int = 0
    token_index: int = 0

@dataclass
class Page:
    """Complete page data containing tokens and page dimensions
    - tokens: List of tokens on this page
    - width: width of the pdf page 
    - height: height of the pdf page
    - page_index: The page number (0-indexed)
    - source: Where the data came from (e.g., "pymupdf", "GoogleOCR")
    """
    tokens: List[Token]
    width: float
    height: float
    page_index: int
    source: str

    @property
    def is_empty(self) -> bool:
        """Indicates whether the page has tokens or not"""
        return len(self.tokens) == 0

@dataclass
class Document:
    """Complete document data containing all pages and full text
    - pages: List of pages in the document
    - full_text: Complete text content of the document
    - source: Where the data came from
    """
    pages: List[Page]
    full_text: str
    source: str

    @property
    def all_tokens(self) -> List[Token]:
        """Get all tokens from all pages in document order"""
        all_tokens = []
        for page in self.pages:
            all_tokens.extend(page.tokens)
        return all_tokens

    @property
    def detected_pii_tokens(self) -> List[Token]:
        """Get all tokens that were detected as PII"""
        return [token for token in self.all_tokens if token.detected_as is not None]

#### Defining Conversion functions for different PDF parsing methods #####
def pymupdf_to_document(doc) -> Document:
    """Convert PyMuPDF document to our unified Document format"""
    pages = []
    full_text_parts = []
    
    for page_num, page in enumerate(doc):
        # Using get_text("words") returns a list of lists:
        # [x0,y0,x1,y1, "word", block_no, line_no, word_no]
        tokens_data = page.get_text("words")
        
        tokens = []
        page_text_parts = []
        
        for token_idx, token_data in enumerate(tokens_data):
            if token_data[4].strip() == "":  # Skip empty tokens
                continue 
            
            token = Token(
                text=token_data[4],
                bbox=BoundingBox(
                    x0=round(token_data[0], 2),
                    y0=round(token_data[1], 2),
                    x1=round(token_data[2], 2),
                    y1=round(token_data[3], 2)
                ),
                page_index=page_num,
                token_index=len(full_text_parts)
            )
            tokens.append(token)
            page_text_parts.append(token_data[4])
        
        if tokens:  # Only add pages that have tokens
            page_obj = Page(
                tokens=tokens,
                width=page.rect.width,
                height=page.rect.height,
                page_index=page_num,
                source="pymupdf"
            )
            pages.append(page_obj)
            full_text_parts.extend(page_text_parts)
    
    return Document(
        pages=pages,
        full_text=" ".join(full_text_parts),
        source="pymupdf"
    )

def google_doc_to_document(doc, pdf_doc) -> Document:
    """Convert Google Document AI response to our unified Document format"""
    pages = []
    full_text_parts = []
    document_text = doc.text
    
    for page_num, page in enumerate(doc.pages):
        # Get original PDF page dimensions for bounding box conversion
        page_width = pdf_doc[page_num].rect.width
        page_height = pdf_doc[page_num].rect.height
        
        tokens = []
        page_text_parts = []
        
        for token in page.tokens:
            # Extract token text from text anchor
            token_text = extract_text_from_text_anchor(token.layout.text_anchor, document_text)
            if not token_text.strip():
                continue
            
            token_obj = Token(
                text=token_text,
                bbox=convert_bounding_poly(token.layout.bounding_poly, page_width, page_height),
                confidence=round(token.layout.confidence, 2),
                page_index=page_num,
                token_index=len(full_text_parts)
            )
            tokens.append(token_obj)
            page_text_parts.append(token_text)
        
        if tokens:  # Only add pages that have tokens
            page_obj = Page(
                tokens=tokens,
                width=page_width,
                height=page_height,
                page_index=page_num,
                source="GoogleOCR"
            )
            pages.append(page_obj)
            full_text_parts.extend(page_text_parts)
    
    return Document(
        pages=pages,
        full_text=" ".join(full_text_parts),
        source="GoogleOCR"
    )

def convert_bounding_poly(bounding_poly, page_width: float, page_height: float) -> BoundingBox:
    """Convert Google Document AI bounding poly to our BoundingBox format"""
    x0 = round(bounding_poly.normalized_vertices[0].x * page_width, 2)
    y0 = round(bounding_poly.normalized_vertices[0].y * page_height, 2)
    x1 = round(bounding_poly.normalized_vertices[2].x * page_width, 2)
    y1 = round(bounding_poly.normalized_vertices[2].y * page_height, 2)
    return BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)

def extract_text_from_text_anchor(text_anchor, document_text: str) -> str:
    """Extracts the text content corresponding to a TextAnchor from the full document"""
    if not text_anchor or not text_anchor.text_segments:
       return ""
    extracted_text = ""
    for segment in text_anchor.text_segments:
      start_index = int(segment.start_index)
      end_index = int(segment.end_index)
      if 0 <= start_index < end_index <= len(document_text):
         extracted_text += document_text[start_index:end_index]
      else:
        # Handle out of bounds indices
        extracted_text += document_text[start_index:min(end_index, len(document_text))]
    return extracted_text

##### For display purposes #####
console = Console()

def print_document(document: Document):
    """Print document structure for debugging"""
    tree = Tree(f"[bold magenta]Document (source={document.source}, pages={len(document.pages)})[/]")
    tree.add(f"[bold blue]Full Text Length: {len(document.full_text)}[/]")
    
    for page in document.pages:
        page_node = tree.add(f"[bold green]Page {page.page_index}[/] [dim]({page.width:.2f}x{page.height:.2f}, {len(page.tokens)} tokens)[/]")
        for token in page.tokens:
            text_label = token.text.replace("\n", "\\n")
            pii_label = f"[red] ({token.detected_as})[/]" if token.detected_as else ""
            confidence_label = f"[yellow] [{token.confidence}][/]" if token.confidence else ""
            page_node.add(f"[white]{text_label}[/]{pii_label}{confidence_label} [dim](bbox={token.bbox})[/]")
    
    console.print(tree)

def print_page(page: Page):
    """Print single page structure for debugging"""
    tree = Tree(f"[bold green]Page {page.page_index}[/] [dim]({page.width:.2f}x{page.height:.2f}, {len(page.tokens)} tokens)[/]")
    for token in page.tokens:
        text_label = token.text.replace("\n", "\\n")
        pii_label = f"[red] ({token.detected_as})[/]" if token.detected_as else ""
        confidence_label = f"[yellow] [{token.confidence}][/]" if token.confidence else ""
        tree.add(f"[white]{text_label}[/]{pii_label}{confidence_label} [dim](bbox={token.bbox})[/]")
    console.print(tree)