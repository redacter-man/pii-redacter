import re
from .PageData import PageData, TextElement
from typing import List

class PiiDetector:
  """Handles all the operations related to recognizing string patterns from PDF page text
  in order to identify target PIIs.
  Note: This class probably doesn't have to be instantiated, everything here could likely be
  static since I can't really find a use for instantiating things.
  """

  def is_valid_ssn(str: str) -> bool:
    """Returns true if a string is a valid SSN number. In form AAA-BB-CCCC."""
    return re.search( r"\d{3}-\d{2}-\d{4}", str)

  def is_valid_bank_account_number(str: str) -> bool:
    """
    Heuristic: Treats any digit sequence of 10 to 17 digits as a bank account number.
    
    Notes:
    - Bank account numbers have no universal format.
    - This is a cautious guess assuming longer digit sequences are sensitive.
    - 9-digit numbers are assumed to be routing numbers, so I kind of wanted to keep it that way.
    """
    return re.search(r"\d{10,17}", str)

  def is_valid_bank_routing_number(str: str) -> bool:
    """Returns true if string is a valid bank routing number. Most US routing numbers are just 9-digit sequences.

    """
    return re.search(r"\d{9}", str)
  
  def contains_credit_score(str: str) -> bool:
    """
    Returns True if the string indicates a credit score disclosure.
    Avoid redacting 3-digit numbers blindly. We rely on keywords instead.
    """
    text_lower = str.lower()
    if "credit score" in text_lower:
        return True
    
    # fuzzy match with common patterns (e.g., "credit score is", "credit score: 720")
    if re.search(r"credit score[:\s]+(?:is\s+)?\d{3}", text_lower):
        return True

  def contains_credit_report(str: str) -> bool:
    """
    Returns True if the string mentions a credit report status.
    Basic keyword-based match. There's no strong structure here.
    """
    return "credit report" in str.lower()

  def detect_page_piis(page_data: PageData) -> List[TextElement]:
    """Receives text data about a particular page on a PDF and sends back PIIs. 
    Note: This will likely evolve when we start reading handwriting with ocr, and I'm guessing then, an 
    ssn like 123-456-789 will probably be sectioned off into separate words.
    """
    detected_piis = []
    for block in page_data.blocks:
      for line in block.lines:
        for element in line.elements:
          text = element.text
          if match := PiiDetector.is_valid_ssn(text):
            element.detected_as = "SSN"
            element.text = match.group()
            detected_piis.append(element)
          elif match := PiiDetector.is_valid_bank_account_number(text):
            element.detected_as = "Account Number"
            element.text = match.group()
            detected_piis.append(element)
          elif match := PiiDetector.is_valid_bank_routing_number(text):
            element.detected_as = "Routing Number"
            element.text = match.group()
            detected_piis.append(element)
            
            #Note: searches for these words, then redacts instead of the whole sentence/phrase
          elif match := re.search(r"\b(?:execeptional|excellent|very good|good|fair|poor)\b", text, re.IGNORECASE):
            element.detected_as = "Credit Report"
            element.text = match.group()
            detected_piis.append(element)
          elif  match := re.search(r"credit score[:\s]*(?:is\s*)?(\d{3})", text, re.IGNORECASE):
            
            #Note: doing this because it'll just redact the score instaead of the whole sentence/phrase
            element.detected_as = "Credit Score"
            element.text = match.group(1)
            detected_piis.append(element)


    return detected_piis
