from pdf.DocumentData import Token, TextSegment, BoundingBox, PageData

def make_token(text, start, end):
    # Create a simple token, we'll keep bounding box constant and only one text segment.
    # Very simple and common case.
    return Token(
        text=text,
        bbox=BoundingBox(0, 0, 10, 10),
        text_segments=[TextSegment(start, end)]
    )

def test_token_overlaps_with_span():
    # Create a token and just pretend it's in a larger string, starting at index 5,
    # and ending at index 10 (exclusive)
    token = make_token("Hello", 5, 10)
    assert token.overlaps_with_span(0, 6)       # Overlap at start
    assert token.overlaps_with_span(9, 15)      # Overlap at end
    assert token.overlaps_with_span(5, 10)      # Complete overlap
    assert token.overlaps_with_span(0, 20)      # Token inside span
    assert not token.overlaps_with_span(0, 5)   # No overlap (before)
    assert not token.overlaps_with_span(10, 15) # No overlap (after)

def test_page_data_get_tokens_in_span():
    tokens = [
        make_token("A", 0, 1),
        make_token("B", 2, 4),
        make_token("C", 5, 8)
    ]

    page = PageData(tokens=tokens)
    # Span overlaps with "B" and "C"
    result = page.get_tokens_in_span(3, 6)
    assert tokens[1] in result
    assert tokens[2] in result
    assert tokens[0] not in result