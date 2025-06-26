import re
from .PageData import Document, Token
from typing import List, Tuple

class PiiDetector:
    """Handles PII detection using token-based approach with bounding boxes and indices"""

    @staticmethod
    def is_valid_ssn(text: str) -> bool:
        """Returns true if a string is a valid SSN number. In form AAA-BB-CCCC."""
        return bool(re.search(r"\d{3}-\d{2}-\d{4}", text))

    @staticmethod
    def is_valid_bank_account_number(text: str) -> bool:
        """
        Heuristic: Treats any digit sequence of 10 to 17 digits as a bank account number.
        
        Notes:
        - Bank account numbers have no universal format.
        - This is a cautious guess assuming longer digit sequences are sensitive.
        - 9-digit numbers are assumed to be routing numbers.
        """
        return bool(re.search(r"\d{10,17}", text))

    @staticmethod
    def is_valid_bank_routing_number(text: str) -> bool:
        """Returns true if string is a valid bank routing number. Most US routing numbers are just 9-digit sequences."""
        return bool(re.search(r"\d{9}", text))
    
    @staticmethod
    def contains_credit_score(text: str) -> bool:
        """
        Returns True if the string indicates a credit score disclosure.
        Avoid redacting 3-digit numbers blindly. We rely on keywords instead.
        """
        text_lower = text.lower()
        if "credit score" in text_lower:
            return True
        
        # fuzzy match with common patterns (e.g., "credit score is", "credit score: 720")
        if re.search(r"credit score[:\s]+(?:is\s+)?\d{3}", text_lower):
            return True
        return False

    @staticmethod
    def contains_credit_report(text: str) -> bool:
        """
        Returns True if the string mentions a credit report status.
        Basic keyword-based match. There's no strong structure here.
        """
        return "credit report" in text.lower()

    @staticmethod
    def detect_pii_in_document(document: Document) -> List[Token]:
        """
        Detect PII in the entire document using token-based approach.
        This method analyzes the full document text and marks tokens that are part of PII patterns.
        """
        detected_tokens = []
        full_text = document.full_text
        
        # Define PII patterns with their detection methods
        pii_patterns = [
            (r"\d{3}-\d{2}-\d{4}", "SSN"),
            (r"\d{10,17}", "Account Number"),
            (r"\d{9}", "Routing Number"),
            (r"\b(?:execeptional|excellent|very good|good|fair|poor)\b", "Credit Report"),
            (r"credit score[:\s]*(?:is\s*)?(\d{3})", "Credit Score")
        ]
        
        # Find all PII matches in the full text
        for pattern, pii_type in pii_patterns:
            matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
            
            for match in matches:
                start_idx = match.start()
                end_idx = match.end()
                
                # Find tokens that overlap with this PII match
                overlapping_tokens = PiiDetector._find_overlapping_tokens(
                    document.all_tokens, start_idx, end_idx, full_text
                )
                
                # Mark overlapping tokens as PII
                for token in overlapping_tokens:
                    if token.detected_as is None:  # Only mark if not already detected
                        token.detected_as = pii_type
                        detected_tokens.append(token)
        
        return detected_tokens

    @staticmethod
    def _find_overlapping_tokens(tokens: List[Token], start_idx: int, end_idx: int, full_text: str) -> List[Token]:
        """
        Find tokens that overlap with a given text range.
        This is more complex than simple token indices because we need to account for spaces and formatting.
        """
        overlapping_tokens = []
        
        # Build a mapping of character positions to tokens
        char_to_token = {}
        current_pos = 0
        
        for token in tokens:
            # Find the token's position in the full text
            token_start = full_text.find(token.text, current_pos)
            if token_start != -1:
                token_end = token_start + len(token.text)
                
                # Map each character position to this token
                for i in range(token_start, token_end):
                    char_to_token[i] = token
                
                current_pos = token_end
        
        # Find tokens that overlap with the PII range
        for i in range(start_idx, end_idx):
            if i in char_to_token:
                token = char_to_token[i]
                if token not in overlapping_tokens:
                    overlapping_tokens.append(token)
        
        return overlapping_tokens

    @staticmethod
    def detect_pii_in_page(page_tokens: List[Token]) -> List[Token]:
        """
        Legacy method for detecting PII in a single page.
        This is kept for backward compatibility but the document-level detection is preferred.
        """
        detected_tokens = []
        
        for token in page_tokens:
            text = token.text
            
            if PiiDetector.is_valid_ssn(text):
                token.detected_as = "SSN"
                detected_tokens.append(token)
            elif PiiDetector.is_valid_bank_account_number(text):
                token.detected_as = "Account Number"
                detected_tokens.append(token)
            elif PiiDetector.is_valid_bank_routing_number(text):
                token.detected_as = "Routing Number"
                detected_tokens.append(token)
            elif re.search(r"\b(?:execeptional|excellent|very good|good|fair|poor)\b", text, re.IGNORECASE):
                token.detected_as = "Credit Report"
                detected_tokens.append(token)
            elif re.search(r"credit score[:\s]*(?:is\s*)?(\d{3})", text, re.IGNORECASE):
                token.detected_as = "Credit Score"
                detected_tokens.append(token)
        
        return detected_tokens

    @staticmethod
    def get_pii_statistics(document: Document) -> dict:
        """
        Get statistics about detected PII in the document.
        """
        pii_tokens = document.detected_pii_tokens
        pii_counts = {}
        
        for token in pii_tokens:
            pii_type = token.detected_as
            if pii_type in pii_counts:
                pii_counts[pii_type] += 1
            else:
                pii_counts[pii_type] = 1
        
        return {
            "total_pii_tokens": len(pii_tokens),
            "pii_types": pii_counts,
            "pages_with_pii": len(set(token.page_index for token in pii_tokens))
        }
