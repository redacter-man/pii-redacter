from typing import List, Tuple
import re, os 
from .DocumentData import DocumentData, PIIMatch, PIIType, Token
from .logger_config import logger

class PIIDetector:
  """The class that detects PIIs and returns tokens that have been identified as PIIs.
  There are two parts to this:
  1. We need a workflow that detects a given pattern as a PII within the document text. 
  This is via regex, and we will find the start and ending indices for that regex match
  or maybe even multiple matches. There could be multiple matches of SSNs at different 
  positions of the string so you need to find all of them within each regex-pattern detection
  function.

  To do this the consensus seems to be a single combined regex with named capturing groups (?P<name>...).
  This approach will do it in one pass, but also have enough ability to differentiate which regexes were matched.
  We'd also be able to handle the special cases of credit score and credit report.

  2. After you have all of your detected PIIs, we'll need to find the tokens that are 
  overlapping with those PIIs. We'll add those tokens to a list and return that list so that 
  the rest of the program can continue with the redaction workflow
  """

  _PII_PATTERNS = {
    # Required Patterns
    PIIType.SSN: r'\d{3}-\d{2}-\d{4}',

    # Added \b (word boundary) which prevents partial matching (e.g. "123456789" within a larger number "000123456789").
    PIIType.ROUTING_NUMBER: r'\b\d{9}\b', 

    PIIType.ACCOUNT_NUMBER: r'\b\d{10,17}\b', # Example: 10-17 digits

    # Ideally want to match "credit score: " and a 3 digit number after, the whole thing. 
    PIIType.CREDIT_SCORE: r"credit score[:\s]+(?:is\s+)?\d{3}",
    
    # Ideally want to match credit report: "very good|excellent|fair|poor" something like that
    PIIType.CREDIT_SCORE_RATING: "TODO ",

    # Optional Patterns
    PIIType.CREDIT_CARD_NUMBER: r'\b(?:\d{4}[ -]?){3}\d{4}\b', 

    # \(?          # Optional opening parenthesis (escaped with \)
    # \d{3}        # Exactly three digits
    # \)?          # Optional closing parenthesis (escaped with \)
    # [-.\s]?      # Optional separator: hyphen, dot, or whitespace
    # \d{3}        # Exactly three digits
    # [-.\s]?      # Optional separator: hyphen, dot, or whitespace
    # \d{4}        # Exactly four digits
    PIIType.PHONE_NUMBER: r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    PIIType.EMAIL: r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
  }

  '''
  Combine simple patterns into one regex for efficient scanning. We'll use 
  named groups (?P<NAME>pattern) to identify which PII type matched.
  We include "credit score", but of course we'll handle its specific index
  Note: 
  1. This is the core of the efficiency, this precompiles the regex for faster repeated use.
  2. "|".join(...) combines all patterns into a single regex using the OR operator.
  3. f"(?P<pii_type.name>{pattern}) creates a named capturing group:
    - (?P<name>): Matches `pattern` and assigns it to the group named `name`
    - We use PIITYPE.name (e.g. "SSN", "ROUTING_NUMBER") as the group name, which allows us to easily identify which specific
      PII pattern matched after re.finditer finds a match.
  '''
  _COMBINED_PII_PATTERN = re.compile(
    "|".join(f"(?P<{pii_type.name}>{pattern})" for pii_type, pattern in _PII_PATTERNS.items())
  )


  def _extract_direct_piis(document_text: str) -> List[PIIMatch]:
    """Extracts PIIs where the entire regex match is the PII itself."""
    matches = []
    for match in PIIDetector._COMBINED_PII_PATTERN.finditer(document_text):
        pii_type_name = match.lastgroup
        if pii_type_name:
            pii_type = PIIType[pii_type_name]
            matches.append(PIIMatch(
                text=match.group(pii_type_name),
                start_index=match.start(pii_type_name),
                end_index=match.end(pii_type_name),
                pii_type=pii_type
            ))
    return matches

  # 1. Iterates through the entire document text only once for all simple PII types
  # 2. match.lastgroup conveniently returns the name of the last (or rightmost named capturing group that matched)
  # 3. match.group(pii_type_name) gets the amtched text for that specific group.
  # 4. Then match.start(pii_type_name) and match.end(pii_type_name) to get the 
  #    exact start and end indices of the specific group's match.
  def _extract_credit_score_value(document_text: str) -> List[PIIMatch]:
      """
      Extracts only the numerical value of a credit score (e.g., '750')
      and its precise start/end indices, excluding the preceding label.
      """
      # (?:...) is a non-capturing group for the label part
      # (\d{3}) is a capturing group for the 3-digit score itself
      credit_score_regex = r"(?:credit score[:\s]+(?:is\s+)?)(\d{3})"
      matches = []
      for match in re.finditer(credit_score_regex, document_text, re.IGNORECASE):
          # group(1) refers to the content of the first capturing group (\d{3})
          matches.append(PIIMatch(
              text=match.group(1),
              start_index=match.start(1), # Start index of the capturing group
              end_index=match.end(1),     # End index of the capturing group
              pii_type=PIIType.CREDIT_SCORE
          ))
      return matches

  def _extract_credit_score_rating(document_text: str) -> List[PIIMatch]:
      """
      Extracts credit score ratings (e.g., 'Excellent', 'Good')
      and their precise start/end indices, potentially excluding a preceding label.
      """
      # Pattern for the rating words, potentially preceded by "credit report:"
      # Order of alternatives in (?:...) matters for "Very Good" vs "Good"
      rating_regex = r"(?:credit report[:\s]+)?(Excellent|Very Good|Good|Fair|Poor)\b"
      matches = []
      for match in re.finditer(rating_regex, document_text, re.IGNORECASE):
          # group(1) refers to the content of the first capturing group (the rating words)
          matches.append(PIIMatch(
              text=match.group(1),
              start_index=match.start(1),
              end_index=match.end(1),
              pii_type=PIIType.CREDIT_SCORE_RATING
          ))
      return matches

  def extract_pii_matches(document_text: str) -> List[PIIMatch]:
      """
      Extracts all PII matches from the document text using a combination of
      a single-pass regex for direct matches and specialized functions for complex patterns.
      """
      all_pii_matches = []
      temp_document_text = document_text

      # 1. Extract PIIs where the entire match is the PII
      all_pii_matches.extend(PIIDetector._extract_direct_piis(document_text))

      # 2. Extract special PIIs that require index refinement (e.g., stripping a label)
      all_pii_matches.extend(PIIDetector._extract_credit_score_value(document_text))
      all_pii_matches.extend(PIIDetector._extract_credit_score_rating(document_text))
      
      # Sort all matches by their start index. Generally makes searching a little easier.
      all_pii_matches.sort(key=lambda x: x.start_index)
      return all_pii_matches

  def get_pii_tokens(job_dir: str, doc_data: DocumentData) -> List[Tuple[int, Token]]:
      """Given the document text and list of the tokens  associated with that text,
      we return tokens that should be redacted because they overlap with detected PIIs.
      
      Returns:
          List[Token]: List of unique tokens that overlap with detected PIIs and should be redacted.

      Note: Naive approach, yet will probably  still be effective
      """
      pii_matches_path = os.path.join(job_dir, "pii_matches.txt")
      pii_tokens_path = os.path.join(job_dir, "pii_tokens.txt")

      pii_matches: List[PIIMatch] = PIIDetector.extract_pii_matches(doc_data.full_text)
      pii_tokens = []

      for index, page in enumerate(doc_data.pages):
          for token in page.tokens:
              for pii in pii_matches:
                if token.overlaps_with_span(pii.start_index, pii.end_index):
                  # Mark the token as detected and add to result if not already added via previous piis
                  if token.detected_as is None:
                      token.detected_as = pii.pii_type.value
                      pii_tokens.append((index, token))
                      # logger.info(f"Mark token: {token}")
                  break  # No need to check other segments for this token because it's already been marked via a previous pii


      # Log piis and tokens into files 
      with open(pii_matches_path, "w") as pii_matches_f:
         for match in pii_matches:  
          pii_matches_f.write(f"{match} \n")
      with open(pii_tokens_path, "w") as pii_tokens_f:
         for token_obj in pii_tokens:
          index, token = token_obj
          pii_tokens_f.write(f"{token.text} \n")
        
      return pii_tokens    
  
