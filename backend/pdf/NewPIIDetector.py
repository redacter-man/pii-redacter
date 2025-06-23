from typing import List
import re
from .DocumentData import DocumentData, PIIMatch, PIIType, Token

class PIIDetector:
  """The class that detects PIIs and returns tokens that have been identified as PIIs.
  There are two parts to this:
  1. We need a workflow that detects a given pattern as a PII within the document text. 
  This is via regex, and we will find the start and ending indices for that regex match
  or maybe even multiple matches. There could be multiple matches of SSNs at different 
  positions of the string so you need to find all of them within each regex-pattern detection
  function.

  2. After you have all of your detected PIIs, we'll need to find the tokens that are 
  overlapping with those PIIs. We'll add those tokens to a list and return that list so that 
  the rest of the program can continue with the redaction workflow
  """


  def extract_piis_helper(document_text: str, pii_pattern: str, pii_type: PIIType) -> List[PIIMatch]:
    """Helper function that extracts piis from the document's text.

    Args:
        document_text (str): The full documenttext.
        pii_pattern (str): A regex pattern for a given PII.
        pii_type (PIIType): The corresponding enum for that PII type.

    Returns:
        List[PIIMatch]: A list of PIIs that matched the PII pattern.
    """
    matches = []
    for match in re.finditer(pii_pattern, document_text):
      matches.append(PIIMatch(
        text=match.group(), 
        start=match.start(),
        end=match.end(),
        pii_type=pii_type
      ))
    return matches
  
  def extract_piis(document_text: str):
    
    pii_matches = []

    # Question: I feel like this is suboptimized that i'm
    # iterating through document text each time
    ssn_pattern = r'\d{3}-\d{2}-\d{4}'
    routing_number_pattern = r"\d{9}"
    pii_matches += PIIDetector.extract_piis_helper(ssn_pattern)
    pii_matches += PIIDetector.extract_piis_helper(routing_number_pattern)
    
    # This pattern is special. We'll have to create a separate 
    # function so that while we do match the pii, we'll refine 
    # the indices S.T. it doesn't include the label "credit score:".
    # As a result, during the token marking process, we won't mark the token 
    # containing the label for redaction. So yeah a custom function for that I guess

    credit_score_pattern = "credit score[:\s]+(?:is\s+)?\d{3}"
    
    '''
    
    
    '''




    pass
    

  def get_pii_tokens(doc_data: DocumentData) -> List[Token]:
    # Main entry point 
    pass

  # Required by us:
  # Detect SSN
  # Detect Routing Number 
  # Detect Account Number
  # Detect Credit report 
  # Detect credit score

  # Optional:
  # Detect credit card number
  # Detect telephone number
  # Detect email address
  # Detect address 
  # Detect full name
  # Detect date of birth

  def get_all_PIIs(doc_data: DocumentData) -> List[Token]:

    pass
