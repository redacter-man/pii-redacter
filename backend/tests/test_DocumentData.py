import pytest
from typing import List, Tuple, NamedTuple


######## =================
# Utility Classes For Testing for testing token overlap algorithm we drafted
######## ===============
# NOTE: Kind of sucks that I'm not testing the real classes or functions from DocumentData.py, but the test results give strong evidence
# that the token overlap algorithm works, and that this indexedd-based way of searching for PIIs and target strings has some water to it.


# TODO: Test the real classes and functions later.
class Token(NamedTuple):
  text: str
  start: int
  end: int
  # NOTE: The only thing that separates this from the actual thing is that
  # we don't have text segments holding the indices.


class PIIMatch(NamedTuple):
  text: str
  start: int
  end: int
  pattern_type: str


def create_tokens(word_positions: List[Tuple[str, int, int]]):
  return [Token(word, start, end) for word, start, end in word_positions]


def find_overlapping_tokens(tokens: List[Token], pii: PIIMatch) -> List[Token]:
  """Find tokens that overlap with PII using specified algorithm"""
  overlapping = []
  for token in tokens:
    if pii.start < token.end and pii.end > token.start:
      overlapping.append(token)
  return overlapping


class TestTokenDetection:
  def test_simple_credit_card_no_gaps(self):
    # 1. Create text
    # 2. Create tokens from text
    # 3. Create the PII, all text within the range should be marked for;

    # text = "My card is 1234567890123456 here"
    # Note:

    tokens = create_tokens(
      [
        ("My", 0, 2),
        ("card", 3, 7),
        ("is", 8, 10),
        ("1234567890123456", 11, 27),
        ("here", 28, 32),
      ]
    )
    pii = PIIMatch("1234567890123456", 11, 27, "credit_card")
    redacted_tokens = find_overlapping_tokens(tokens, pii)
    assert len(redacted_tokens) == 1
    assert redacted_tokens[0].text == "1234567890123456"

  def test_credit_card_with_spaces(self):
    # text = "Card: 1234 5678 9012 3456 end"
    tokens = create_tokens(
      [
        ("Card:", 0, 5),
        ("1234", 6, 10),
        ("5678", 11, 15),
        ("9012", 16, 20),
        ("3456", 21, 25),
        ("end", 26, 29),
      ]
    )
    pii = PIIMatch("1234 5678 9012 3456", 6, 25, "credit_card")
    redacted_tokens = find_overlapping_tokens(tokens, pii)

    assert len(redacted_tokens) == 4
    assert [t.text for t in redacted_tokens] == ["1234", "5678", "9012", "3456"]

  def test_partial_token_overlap(self):
    # text = "prefix1234 5678 9012 3456suffix"
    tokens = create_tokens(
      [
        ("prefix1234", 0, 10),
        ("5678", 11, 15),
        ("9012", 16, 20),
        ("3456suffix", 21, 31),
      ]
    )
    pii = PIIMatch("1234 5678 9012 3456", 6, 25, "credit_card")
    redacted_tokens = find_overlapping_tokens(tokens, pii)

    expected_result = ["prefix1234", "5678", "9012", "3456suffix"]
    assert [t.text for t in redacted_tokens] == expected_result

  def test_false_positive(self):
    # text = "Address: 123 South Burger St. Card: 1234 4567 8901 2345"
    tokens = create_tokens(
      [
        ("Address:", 0, 8),
        ("123", 9, 12),
        ("South", 13, 18),
        ("Burger", 19, 25),
        ("St.", 26, 29),
        ("Card:", 30, 35),
        ("1234", 36, 40),
        ("4567", 41, 45),
        ("8901", 46, 50),
        ("2345", 51, 55),
      ]
    )
    pii = PIIMatch("1234 4567 8901 2345", 36, 55, "credit_card")
    redacted_tokens = find_overlapping_tokens(tokens, pii)
    expected_result = [
      "1234",
      "4567",
      "8901",
      "2345",
    ]

    # Shouldn't have 123, but should have the rest of the numbers
    assert len(expected_result) == 4
    assert [t.text for t in redacted_tokens] == expected_result
