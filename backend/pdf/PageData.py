"""
Defines data classes that help us standardize the data we get from PyMuPDF, and the OCR library (or multiple) we use.

Data classes in python are just there to store data, not do actual operations. Think of them as types or interfaces that help us know what
type of data that we're dealing with.
"""

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
class TextElement:
  """Individual text element (word/span level)
  - text: The actual text content as a string that was parsed.
  - bbox: Bounding box of the text element
  - confidence: An optional OCR confidence score, which will be filled in cases where OCR is applied.
  - detected_as: An optional parameter that is assigned when a TextElement is detected as a PII. We record
  what PII we believe it was e.g. 'SSN', 'Routing Number', 'Account Number'.
  """

  text: str
  bbox: BoundingBox
  confidence: Optional[float] = None
  detected_as: Optional[str] = None


@dataclass
class TextLine:
  """Structure representing a line of text that containing multiple text elements.


  - elements: Elements in that line of text.
  - bbox: Bounding box
  - line_id: ID number of the line

  Note: Whilst I did do that write-up for multiple words, I don't know for sure how efficable this technique truly is, or if it will even help at all.
  But it theory it seems useful to reconstruct lines of text, how we already saw that a span can contain multiple words, so maybe it's not necessary.
  """

  elements: List[TextElement]
  bbox: BoundingBox
  line_id: int

  @property
  def full_text(self) -> str:
    """Reconstruct full line text"""
    return " ".join([elem.text for elem in self.elements])


@dataclass
class TextBlock:
  """Block containing multiple lines

  - bbox: The bounding box of the text box.
  - block_id: The id number of the block
  - block_type: the type of block we're processing
  """

  lines: List[TextLine]
  bbox: BoundingBox
  block_id: int
  block_type: str = "text"  # "text", "image", "table", etc.


@dataclass
class PageData:
  """Complete page text data

  - block: List of text blocks
  - width: width of the pdf page
  - height: height of the pdf page
  - source: Where the data came from.

  Note: "source" probably isn't needed.
  """

  blocks: List[TextBlock]
  width: float
  height: float
  source: str  # "pymupdf", "paddleocr", "trocr"

  @property
  def is_empty(self) -> bool:
    """Indicates whether the page has data or not

    Note: If the array of blocks is 0, it's empty, else has content.

    TODO: Hope that's how it works.
    """
    return len(self.blocks) == 0


#### Defining Conversion functions for different PDF parsing methods #####
def pymupdf_to_unified(page_dict: Dict) -> PageData:
  """Convert PyMuPDF dict output int our unified format"""

  """
    - Iterate through all text blocks:
      - For a given text block, iterate through all lines:
        - for a given line, collect all of its span elements and 
          put them into the elements array. If a line has no span elements (it has no content)
          we just won't put that line in the lines array.
        - At this point we've collected all lines for the text block, and 
          record the text block in the blocks array as long as it has content.
    - Create the PageData object.

    We aren't doing anything fancy, we're just putting the data in a similar hierarchical structure,
    but we're removing a lot of the data and making things more clearer now that we're using data classes.
    """
  blocks = []
  for block_idx, block in enumerate(page_dict["blocks"]):
    if block.get("type") != 0:  # Skip non-text blocks
      continue
    lines = []

    # For a lines in a given block of text; use fallback if no lines.
    for line_idx, line in enumerate(block.get("lines", [])):
      # Iterate through all spans in the line that have content
      # 1. Create that bounding box
      # 2. create that text element.
      # Note: Definitely minimizing metadata unnecessary data, which is good.
      elements = []
      for span in line.get("spans", []):
        if span["text"].strip() == "":
          continue

        bbox = BoundingBox(
          x0=round(span["bbox"][0], 2),
          y0=round(span["bbox"][1], 2),
          x1=round(span["bbox"][2], 2),
          y1=round(span["bbox"][3], 2),
        )
        element = TextElement(text=span["text"], bbox=bbox)
        elements.append(element)

      # If a line has words, record the line because it actaully has content!
      if elements:
        line_bbox = BoundingBox(
          x0=round(line["bbox"][0], 2),
          y0=round(line["bbox"][1], 2),
          x1=round(line["bbox"][2], 2),
          y1=round(line["bbox"][3], 2),
        )

        text_line = TextLine(elements=elements, bbox=line_bbox, line_id=line_idx)
        lines.append(text_line)

    # At thsi point we processed all of the lines. If we actually have lines (which have content)
    # we'll record the text block!
    if lines:
      block_bbox = BoundingBox(
        x0=round(block["bbox"][0], 2),
        y0=round(block["bbox"][1], 2),
        x1=round(block["bbox"][2], 2),
        y1=round(block["bbox"][3], 2),
      )
      text_block = TextBlock(lines=lines, bbox=block_bbox, block_id=block_idx)
      blocks.append(text_block)

  return PageData(
    blocks=blocks,
    width=page_dict["width"],
    height=page_dict["height"],
    source="pymupdf",
  )


##### For display purposes #####

console = Console()


def print_page_data(page_data: PageData):
  tree = Tree(
    f"[bold magenta]Page (width={page_data.width}, height={page_data.height}, source={page_data.source})[/]"
  )
  for block in page_data.blocks:
    block_node = tree.add(
      f"[bold blue]Block {block.block_id}[/] [dim](bbox={block.bbox})[/]"
    )
    for line in block.lines:
      line_node = block_node.add(
        f"[green]Line {line.line_id}[/] [dim](bbox={line.bbox})[/]"
      )
      for elem in line.elements:
        text_label = elem.text.replace("\n", "\\n")
        pii_label = f"[red] ({elem.detected_as})[/]" if elem.detected_as else ""
        line_node.add(f"[white]{text_label}[/]{pii_label} [dim](bbox={elem.bbox})[/]")
  console.print(tree)
