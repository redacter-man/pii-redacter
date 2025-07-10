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
    PIIType.SSN: r"\d{3}-\d{2}-\d{4}",
    # Added \b (word boundary) which prevents partial matching (e.g. "123456789" within a larger number "000123456789").
    PIIType.ROUTING_NUMBER: r"\b\d{9}\b",
    PIIType.ACCOUNT_NUMBER: r"\b\d{10,17}\b",  # Example: 10-17 digits
    # Matches "credit score: <3 digit number>", there could be zero or multiple spaces after the colon
    PIIType.CREDIT_SCORE: r"credit score:\s*\d{3}",
    # Ideally want to match credit report: "very good|excellent|fair|poor"
    # Optional space after colon
    PIIType.CREDIT_SCORE_RATING: r"credit report:\s*(very good|good|excellent|fair|poor|bad)",
    # Optional Patterns
    PIIType.CREDIT_CARD_NUMBER: r"\b(?:\d{4}[ -]?){3}\d{4}\b",
    # \(?          # Optional opening parenthesis (escaped with \)
    # \d{3}        # Exactly three digits
    # \)?          # Optional closing parenthesis (escaped with \)
    # [-.\s]?      # Optional separator: hyphen, dot, or whitespace
    # \d{3}        # Exactly three digits
    # [-.\s]?      # Optional separator: hyphen, dot, or whitespace
    # \d{4}        # Exactly four digits
    PIIType.PHONE_NUMBER: r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    PIIType.EMAIL: r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
  }

  """
  Combine simple patterns into one regex for efficient scanning. We'll use 
  named groups (?P<NAME>pattern) to identify which PII type matched.
  Note: 
  1. This is the core of the efficiency, this precompiles the regex for faster repeated use.
  2. "|".join(...) combines all patterns into a single regex using the OR operator.
  3. f"(?P<pii_type.name>{pattern}) creates a named capturing group:
    - (?P<name>): Matches `pattern` and assigns it to the group named `name`
    - We use PIITYPE.name (e.g. "SSN", "ROUTING_NUMBER") as the group name, which allows us to easily identify which specific
      PII pattern matched after re.finditer finds a match.

  Note: Putting re.IGNORECASE so that we can match stuff like credit score and credit report 
  without having to worry about casing.
  """
  _COMBINED_PII_PATTERN = re.compile(
    "|".join(
      f"(?P<{pii_type.name}>{pattern})" for pii_type, pattern in _PII_PATTERNS.items()
    ),
    re.IGNORECASE,
  )

  # TODO: In general we're able to detect PIIs without labels such as SSNs, credit cards, etc.
  # However for detecting credit scores and credit reports, we'll detect the presence of the
  # label first. Then we only want to redact the value, which is the credit score or the rating.
  # It's quite simple to be able to do this in one pass:

  # 1. Let extract_direct_piis extract all piis and this will mark them at the type of piis

  # then after the loop, loop over all piis again. For any piis that are CREDIT_SCORE or
  # CREDIT_SCORE_RATING, we'd write some code that would update the indices and text
  # so it only includes their values?
  def _extract_direct_piis(document_text: str) -> List[PIIMatch]:
    """Extracts PIIs where the entire regex match is the PII itself."""
    matches = []
    for match in PIIDetector._COMBINED_PII_PATTERN.finditer(document_text):
      pii_type_name = match.lastgroup
      if pii_type_name:
        pii_type = PIIType[pii_type_name]
        matches.append(
          PIIMatch(
            text=match.group(pii_type_name),
            start_index=match.start(pii_type_name),
            end_index=match.end(pii_type_name),
            pii_type=pii_type,
          )
        )
    return matches

  def _refine_pii_matches(pii_matches: List[PIIMatch]):
    """Refines PIIs so that stuff like credit score and credit report only slice the values instead of the labels."""
    for match in pii_matches:
      if match.pii_type == PIIType.CREDIT_SCORE:
        """
            E.g. "Credit score: 860"
            The only thing you'll change is the start index, just increase it 
            so that it points to the first digit of the credit score.
            """
        n = len(match.text)
        while match.start_index < n and not match.text[match.start_index].isdigit():
          match.start_index += 1

        # Note: For each iteration, you may also update the string so that it
        # doesn't contain the previous character if you need. But I'm going to keep it
        # for logging purposes

      elif match.pii_type == PIIType.CREDIT_SCORE_RATING:
        """
            E.g. credit report:  excellent
            Again, we only have to update the start index:
            1. Increase the start_index by 14 positions. As a result it should be positioned at the whitespace to the right of the semicolon (the whitespace could be missing as well so)
               this could be pointing to a letter.
            2. Assuming there could be multiple spaces to the right, we'll keep iterating until our current index doesn't point at whitespace

            Note: If the data is coming from some sources, like PyMuPDF, where we're reconstructing the document 
            text, you're not going to have multiple spaces like we saw here.
            """
        match.start_index += 14
        n = len(match.text)
        while (
          match.start_index < n
          and match.text[match.start_index].isspace()
        ):
          match.start_index += 1

  def extract_pii_matches(document_text: str) -> List[PIIMatch]:
    """
    Extracts all PII matches from the document, refines, and sorts them.
    """
    pii_matches = PIIDetector._extract_direct_piis(document_text)
    PIIDetector._refine_pii_matches(pii_matches)
    pii_matches.sort(key=lambda x: x.start_index)
    return pii_matches

  def get_pii_tokens(job_dir: str, doc_data: DocumentData) -> List[Tuple[int, Token]]:
    """Given the document text and list of the tokens  associated with that text,
    we return tokens that should be redacted because they overlap with detected PIIs.

    Returns:
        List[Token]: List of unique tokens that overlap with detected PIIs and should be redacted.

    Note: Naive approach, yet will probably  still be effective
    """
    # pii_matches_path = os.path.join(job_dir, "pii_matches.txt")
    # pii_tokens_path = os.path.join(job_dir, "pii_tokens.txt")
    # document_text_path = os.path.join(job_dir, "document_text.txt")

    pii_matches: List[PIIMatch] = PIIDetector.extract_pii_matches(doc_data.full_text)
    pii_tokens = []

    # Open both files before the loop
    # pii_matches_f = open(pii_matches_path, "w")
    # pii_tokens_f = open(pii_tokens_path, "w")
    # document_text_f = open(document_text_path, "w")


    # document_text_f.write(repr(doc_data.full_text)) # use repr() to ensure we see hidden characters like \n, \t, etc.
    # document_text_f.close()

    for page_index, page in enumerate(doc_data.pages):
      
      # Find and log the PIIs detected on current page
      # page_pii_matches = [
      #   m
      #   for m in pii_matches
      #   if any(t.overlaps_with_span(m.start_index, m.end_index) for t in page.tokens)
      # ]
      # page_number = page_index + 1

      # for match in page_pii_matches:
      #   pii_matches_f.write(f"Page {page_number}: {match}\n")

      # For pii
      for token in page.tokens:
        for pii in pii_matches:
          if token.overlaps_with_span(pii.start_index, pii.end_index):
            if token.detected_as is None:
              token.detected_as = pii.pii_type.value
              pii_tokens.append((page_index, token))
              # Log redacted token for this page
              # pii_tokens_f.write(f"Page {page_number}: {token.text}\n")
            break  # Already marked
      

    # pii_matches_f.close()
    # pii_tokens_f.close()
    
    
    return pii_tokens
