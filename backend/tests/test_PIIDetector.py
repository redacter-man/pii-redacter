import pytest
import re
from unittest.mock import Mock, patch, mock_open
from typing import List
from pdf.PIIDetector import PIIDetector
from pdf.DocumentData import (
  DocumentData,
  PageData,
  Token,
  TextSegment,
  BoundingBox,
  PIIMatch,
  PIIType,
)


class TestPIIDetector:
  """Test suite for the PIIDetector Class"""

  def test_ssn_regex_pattern(self):
    """Test SSN regex pattern matches valid formats"""
    ssn_pattern = PIIDetector._PII_PATTERNS[PIIType.SSN]
    compiled_pattern = re.compile(ssn_pattern)

    # Valid SSN formats
    valid_ssns = ["123-45-6789", "987-65-4321", "000-00-0000"]

    # Invalid SSN formats
    invalid_ssns = [
      "12-345-6789",  # Wrong format
      "123-456-789",  # Wrong format again
      "123456789",  # No dashes
      "123-45-678a",  # Contains letter
      "123-4a-6789",  # Contains letter in middle
    ]

    # Make sure all valid formats are flagged and equal the text being tested
    for ssn in valid_ssns:
      match = compiled_pattern.search(ssn)
      assert match is not None, f"Should match valid SSN: {ssn}"
      assert match.group() == ssn

    # Ensure invalid formats aren't being flagged
    for ssn in invalid_ssns:
      match = compiled_pattern.search(ssn)
      assert match is None, f"Should not match invalid SSN: {ssn}"

  def test_routing_number_regex_pattern(self):
    """Test routing number regex pattern with word boundaries"""
    routing_pattern = PIIDetector._PII_PATTERNS[PIIType.ROUTING_NUMBER]
    compiled_pattern = re.compile(routing_pattern)

    # Valid routing numbers (exactly 9 digits)
    valid_routing = ["123456789", "987654321", "000000000"]

    # Invalid routing numbers
    invalid_routing = [
      "12345678",  # Too short
      "1234567890",  # Too long
      "123456789a",  # Contains letter
    ]

    # Test word boundary - should not match partial numbers
    # In form (test_text, expected_match_text)
    boundary_tests = [
      ("Account: 123456789 Balance", "123456789"),  # Should match
      ("ID: 000123456789", None),  # Should not match (part of larger number)
      ("123456789000", None),  # Should not match (part of larger number)
      ("The routing number is 123456789.", "123456789"),  # Should match
    ]

    for routing in valid_routing:
      match = compiled_pattern.search(routing)
      assert match is not None, f"Should match valid routing number: {routing}"
      assert match.group() == routing

    for routing in invalid_routing:
      match = compiled_pattern.search(routing)
      assert match is None, f"Should not match invalid routing number: {routing}"

    for text, expected in boundary_tests:
      match = compiled_pattern.search(text)

      # If we expect a match, then ensure the match from the regex actually exists
      # and it matches our target data.
      if expected:
        assert match is not None, f"Should find routing number in: {text}"
        assert match.group() == expected
      else:
        # Else, we don't expect a match so ensure match is literally nothing
        assert match is None, f"Should not find routing number in: {text}"

  def test_account_number_regex_pattern(self):
    """Test account number regex pattern (10-17 digits with word boundaries)"""
    account_pattern = PIIDetector._PII_PATTERNS[PIIType.ACCOUNT_NUMBER]
    compiled_pattern = re.compile(account_pattern)

    # Valid account numbers (10-17 digits)
    valid_accounts = [
      "1234567890",  # 10 digits (minimum)
      "12345678901234567",  # 17 digits (maximum)
      "123456789012345",  # 15 digits (middle)
    ]

    # Invalid account numbers
    invalid_accounts = [
      "123456789",  # 9 digits (too short)
      "123456789012345678",  # 18 digits (too long)
      "12345678a0",  # Contains letter
    ]

    # Test word boundaries
    boundary_tests = [
      ("Account: 1234567890 Type", "1234567890"),
    ]

    # Same workflow as when we tested routing numbers
    for account in valid_accounts:
      match = compiled_pattern.search(account)
      assert match is not None, f"Should match valid account number: {account}"
      assert match.group() == account

    for account in invalid_accounts:
      match = compiled_pattern.search(account)
      assert match is None, f"Should not match invalid account number: {account}"

    for text, expected in boundary_tests:
      match = compiled_pattern.search(text)
      if expected:
        assert match is not None, f"Should find account number in: {text}"
        assert match.group() == expected
      else:
        assert match is None, f"Should not find account number in: {text}"

  def test_credit_score_regex_pattern(self):
    """Test credit score regex pattern"""
    credit_score_pattern = PIIDetector._PII_PATTERNS[PIIType.CREDIT_SCORE]
    compiled_pattern = re.compile(credit_score_pattern, re.IGNORECASE)

    # Valid credit score formats
    # Note: Label
    valid_formats = [
      ("credit score: 750", "credit score: 750"),  # lower cased basic spacing
      ("Credit Score: 680", "Credit Score: 680"),  # case mixed
      ("credit score:720", "credit score:720"),  # zero spaces after colon
      ("Credit Score:  800", "Credit Score:  800"),  # multiple spaces after colon
    ]

    # Invalid formats
    invalid_formats = [
      "credit score: 75",  # Only 2 digits
      "score: 750",  # Missing "credit"
      "credit rating: 750",  # Different word
    ]

    for text, expected in valid_formats:
      match = compiled_pattern.search(text)
      assert match is not None, f"Should match credit score format: {text}"
      assert match.group() == expected

    for text in invalid_formats:
      match = compiled_pattern.search(text)
      assert match is None, f"Should not match invalid format: {text}"

  def test_credit_score_rating(self):
    credit_score_rating_pattern = PIIDetector._PII_PATTERNS[PIIType.CREDIT_SCORE_RATING]
    compiled_pattern = re.compile(credit_score_rating_pattern, re.IGNORECASE)

    valid_formats = [
      (
        "credit report: good",
        "credit report: good",
      ),  # lower cased, one space after colon
      ("Credit Report: Very Good", "Credit Report: Very Good"),  # case mixed
      ("Credit Report:Excellent", "Credit Report:Excellent"),  # No space after colon
      (
        "Credit Report:     fair",
        "Credit Report:     fair",
      ),  # Multiple spaces after colon
    ]

    # Invalid formats
    invalid_formats = [
      "credit report: 750",  # a number
    ]

    for text, expected in valid_formats:
      match = compiled_pattern.search(text)
      assert match is not None, f"Should match credit report format: {text}"
      assert match.group() == expected

    for text in invalid_formats:
      match = compiled_pattern.search(text)
      assert match is None, f"Should not match invalid format: {text}"

  def test_phone_number_regex_pattern(self):
    """Test phone number regex pattern with various formats"""
    phone_pattern = PIIDetector._PII_PATTERNS[PIIType.PHONE_NUMBER]
    compiled_pattern = re.compile(phone_pattern)

    # Valid phone number formats
    valid_phones = [
      "1234567890",  # No separators
      "123-456-7890",  # Hyphen separators
      "123.456.7890",  # Dot separators
      "123 456 7890",  # Space separators
      "(123)456-7890",  # Parentheses with hyphen
      "(123) 456-7890",  # Parentheses with space and hyphen
      "(123)4567890",  # Parentheses, no separator after
    ]

    # Invalid phone number formats
    invalid_phones = [
      "12345678",  # Too short
      "123-45-67890",  # Wrong separator placement
      "123-456-789a",  # Contains letter
      "abc-def-ghij",  # All letters
    ]

    for phone in valid_phones:
      match = compiled_pattern.search(phone)
      assert match is not None, f"Should match valid phone number: {phone}"
      assert match.group() == phone

    for phone in invalid_phones:
      match = compiled_pattern.search(phone)
      assert match is None, f"Should not match invalid phone number: {phone}"

  def test_email_regex_pattern(self):
    """Test email regex pattern"""
    email_pattern = PIIDetector._PII_PATTERNS[PIIType.EMAIL]
    compiled_pattern = re.compile(email_pattern)

    # Valid email formats
    valid_emails = [
      "user@example.com",
      "test.email@domain.org",
      "user+tag@example.co.uk",
      "user_name@example-domain.com",
      "123@example.com",
      "user@sub.domain.com",
    ]

    # Invalid email formats
    invalid_emails = [
      "userexample.com",  # Missing @
      "@example.com",  # Missing user part
      "user@",  # Missing domain
      "user@.com",  # Missing domain name
      "user@example",  # Missing TLD
      "user@example.c",  # TLD too short
    ]

    for email in valid_emails:
      match = compiled_pattern.search(email)
      assert match is not None, f"Should match valid email: {email}"
      assert match.group() == email

    for email in invalid_emails:
      match = compiled_pattern.search(email)
      assert match is None, f"Should not match invalid email: {email}"

  def test_credit_card_regex_pattern(self):
    """Test credit card regex pattern"""
    cc_pattern = PIIDetector._PII_PATTERNS[PIIType.CREDIT_CARD_NUMBER]
    compiled_pattern = re.compile(cc_pattern)

    # Valid credit card formats
    valid_cards = [
      "1234567890123456",  # No separators
      "1234 5678 9012 3456",  # Space separators
      "1234-5678-9012-3456",  # Hyphen separators
    ]

    # Invalid credit card formats
    invalid_cards = [
      "123456789012345",  # Too short (15 digits)
      "12345678901234567",  # Too long (17 digits)
      "1234-5678-9012-345a",  # Contains letter
      "1234 5678 9012 345",  # Last group too short
    ]

    for card in valid_cards:
      match = compiled_pattern.search(card)
      assert match is not None, f"Should match valid credit card: {card}"
      assert match.group() == card

    for card in invalid_cards:
      match = compiled_pattern.search(card)
      assert match is None, f"Should not match invalid credit card: {card}"

  @pytest.mark.parametrize(
    "text,expected_type,expected_value",
    [
      ("My SSN is 123-45-6789.", PIIType.SSN, "123-45-6789"),
      ("Routing: 123456789", PIIType.ROUTING_NUMBER, "123456789"),
      ("Account: 123456789012", PIIType.ACCOUNT_NUMBER, "123456789012"),
      ("Credit Score: 750", PIIType.CREDIT_SCORE, "Credit Score: 750"),
      (
        "Credit report: Excellent",
        PIIType.CREDIT_SCORE_RATING,
        "Credit report: Excellent",
      ),
      ("Card: 4111 1111 1111 1111", PIIType.CREDIT_CARD_NUMBER, "4111 1111 1111 1111"),
      ("Phone: (123) 456-7890", PIIType.PHONE_NUMBER, "(123) 456-7890"),
      ("Email: test@example.com", PIIType.EMAIL, "test@example.com"),
    ],
  )
  def test_combined_pii_regex(self, text, expected_type, expected_value):
    pattern = PIIDetector._COMBINED_PII_PATTERN
    match = pattern.search(text)
    assert match is not None, f"No match found for {expected_type}"
    assert match.lastgroup == expected_type.name
    assert match.group(expected_type.name) == expected_value
