import pytest
from unittest.mock import MagicMock
from pdf.PDFAdapter import PDFAdapter
from pdf.DocumentData import BoundingBox, TextSegment, Token, PageData, DocumentData


def make_mock_page(words):
  # Makes a mock pymupdf.Page object that returns the words we need.
  mock_page = MagicMock()
  mock_page.get_text.return_value = words
  return mock_page


def test_pymupdf_to_data_single_page():
  # Simulate PyMuPDF page.get_text("words") output for a single page
  fake_words = [[10, 10, 50, 20, "Hello", 0, 0, 0], [60, 10, 100, 20, "World", 0, 0, 1]]
  mock_doc = [make_mock_page(fake_words)]

  document_data = PDFAdapter.pymupdf_to_data(mock_doc)

  # Verify document's full text
  assert document_data.full_text == "Hello World"

  # 1. Verify that there are two tokens in the document
  # 2. Verify the contents of said tokens and their indices
  tokens = document_data.pages[0].tokens
  assert len(tokens) == 2
  assert tokens[0].text == "Hello"
  assert tokens[0].bbox == BoundingBox(10, 10, 50, 20)
  assert tokens[0].text_segments == [TextSegment(start_index=0, end_index=5)]

  assert tokens[1].text == "World"
  assert tokens[1].bbox == BoundingBox(60, 10, 100, 20)
  assert tokens[1].text_segments == [TextSegment(start_index=6, end_index=11)]


def test_pymupdf_to_data_multiple_pages():
  # Page 1: "Foo Bar"
  words_page1 = [[0, 0, 10, 10, "Foo", 0, 0, 0], [12, 0, 22, 10, "Bar", 0, 0, 1]]
  # Page 2: "Baz Qux"
  words_page2 = [[0, 0, 10, 10, "Baz", 0, 0, 0], [12, 0, 22, 10, "Qux", 0, 0, 1]]
  mock_doc = [make_mock_page(words_page1), make_mock_page(words_page2)]

  document_data = PDFAdapter.pymupdf_to_data(mock_doc)

  # The full_text should be the concatenation of all tokens with spaces, across pages
  assert document_data.full_text == "Foo Bar Baz Qux"

  # Check page 1 tokens
  tokens1 = document_data.pages[0].tokens
  assert tokens1[0].text == "Foo"
  assert tokens1[0].text_segments == [TextSegment(start_index=0, end_index=3)]
  assert tokens1[1].text == "Bar"
  assert tokens1[1].text_segments == [TextSegment(start_index=4, end_index=7)]

  # Check page 2 tokens
  tokens2 = document_data.pages[1].tokens
  # Indices should continue from previous page
  assert tokens2[0].text == "Baz"
  assert tokens2[0].text_segments == [TextSegment(start_index=8, end_index=11)]
  assert tokens2[1].text == "Qux"
  assert tokens2[1].text_segments == [TextSegment(start_index=12, end_index=15)]
