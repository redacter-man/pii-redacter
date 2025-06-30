from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class PIIType(Enum):
  """Enums representing the type of PIIs that could be detected."""

  SSN = "SSN"
  ROUTING_NUMBER = "Routing Number"
  ACCOUNT_NUMBER = "Account Number"
  CREDIT_SCORE_RATING = "Credit Score Rating"
  CREDIT_SCORE = "Credit Score"

  # Optional: Haven't been done yet
  CREDIT_CARD_NUMBER = "Credit Card Number"
  PHONE_NUMBER = "Phone Number"
  EMAIL = "Email"
  ADDRESS = "Address"
  NAME = "Name"


@dataclass
class PIIMatch:
  """Data structure representing a PII that we detected from the document's full text.
  - content: The string that was matched by the regex.
  - start_index: Starting index of the match in the document's full text.
  - end_index: Ending index of the match in the document's full text.
  - detected_as: The type of PII that we detected this amatch as.
  """

  text: str
  start_index: int
  end_index: int
  pii_type: PIIType

  def __repr__(self):
    return f"PIIMatch(type={self.pii_type.name}), text='{self.text}'"


@dataclass
class BoundingBox:
  """Bounding box coordinates. The point (x0, y0) would be the top left corner
  of a bounding box and (x1, y1) would be the bottom right corner.

  Note: Bounding boxes are essential to knowing where on a page a particular
  text element is located, and therefore are crucial for redaction.
  """

  x0: float
  y0: float
  x1: float
  y1: float


@dataclass
class TextSegment:
  """Represents a contiguous span of text in the document with index positions.

  Note: This handles cases where a single logical token might be split across multiple
  regions (e.g., across line breaks or columns). For google document AI API, there will be
  some tokens that have multiple text segments. However for regular pymupdf, tesseract-ocr,
  and other libraries, you'll likely only have one textsegment that indicates the start
  and ending string in the document's full text.
  """

  start_index: int  # Start position in Document.full_text
  end_index: int  # End position in Document.full_text


@dataclass
class Token:
  """Class representing an individual text element (token/word).

  - text: The actual text content as a string that was parsed.
  - bbox: Bounding box of the text element on the page.
  - text_segments: List of segments this element spans in the full document text.
                  Most elements will have one segment, but some may span multiple
                  (e.g., hyphenated words across lines).
  - detected_as: Optional parameter assigned when detected as PII.
  """

  text: str
  bbox: BoundingBox
  text_segments: List[TextSegment]
  detected_as: Optional[PIIType] = None

  def __repr__(self):
    return f"Token(detected_as={self.detected_as.name}), text='{self.text}'"

  def char_indices(self) -> List[Tuple[int, int]]:
    """Get all (start, end) index pairs for this element in document text."""
    return [(seg.start_index, seg.end_index) for seg in self.text_segments]

  def overlaps_with_span(self, start_idx: int, end_idx: int) -> bool:
    """Check if this element overlaps with a given character span."""
    for segment in self.text_segments:
      if start_idx < segment.end_index and end_idx > segment.start_index:
        return True
    return False


@dataclass
class PageData:
  """Data structure representing all text data extracted from a single page.

  - tokens: All text elements on this page (tokens/words).

  Note: Could optimize this S.T. you have the full text of each page. As a result
  doing a regex would only of a regex of each page. Though if you want to test that
  out, later setup some tests that keep track of the performance of your app in terms
  of detecting PIIs and whatnot. Then only after can you feel safe about implementing
  new methods like that.
  """

  tokens: List[Token]

  def get_tokens_in_span(self, start_idx: int, end_idx: int) -> List[Token]:
    """Get all tokens that overlap with the given character span."""
    return [t for t in self.tokens if t.overlaps_with_span(start_idx, end_idx)]


@dataclass
class DocumentData:
  """Contains the text data for all pages in a document.

  - pages: List of page data.
  - full_text: Complete document text in reading order ideally.

  Note: It ideally should be in reading order, but most of the time you should be
  able to get a good result with pymupdf, tesseract, etc. The main thing is that
  the indices of your tokens should be with respect the full_text character array.
  """

  pages: List[PageData]
  full_text: str