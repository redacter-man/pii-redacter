# PII Detection in OCR Documents: Index-Based Approach

## Problem Statement

Traditional word-by-word PII detection works well for single-token patterns like `123-45-6789` (SSN), but fails for multi-token patterns like `4444 4444 4444 4444` (credit card numbers). The challenge is accurately identifying and redacting PII that spans multiple OCR tokens without accidentally redacting unrelated text.

## Current Approach Limitations

### Line Reconstruction Method
The current workflow involves:
1. Reconstructing entire lines from individual tokens
2. Applying regex patterns to detect PII
3. Marking tokens that are substrings of matches for redaction

**Critical Flaw**: This approach can cause false positives. For example:
- Address: `123 South Burger St.`
- Credit Card: `1234 4567 8901 2345`

If both appear on the same reconstructed line, the algorithm might incorrectly mark `123` from the address for redaction when matching the credit card pattern `1234`.

## Proposed Solution: Index-Based Detection

### Core Algorithm

Instead of reconstructing lines, work directly with the full `Document.text` string and token indices:

1. **Pattern Matching**: Apply regex patterns to `Document.text` to find PII matches
2. **Index Extraction**: For each match, obtain `startIndex` and `endIndex`
3. **Token Mapping**: Find all tokens that overlap with the PII span
4. **Redaction**: Mark overlapping tokens for redaction

### Token Overlap Logic

A token should be marked for redaction if:
```
startIndex ∈ [token.start, token.end) OR endIndex ∈ [token.start, token.end)
```

### Example Walkthrough

**Document.text**: `"CIA Agent Leader (John Conway) led the operation"`
**Target PII**: `"John Conway"` (startIndex=18, endIndex=29)
**Tokens**: `["CIA", "Agent", "Leader", "(John", "Conway)", "led", "the", "operation"]`

Token analysis:
- `"CIA"` [0,3]: No overlap → Skip
- `"Agent"` [4,9]: No overlap → Skip  
- `"Leader"` [10,16]: No overlap → Skip
- `"(John"` [17,22]: startIndex(18) ∈ [17,22] → **Mark for redaction**
- `"Conway)"` [23,30]: endIndex(29) ∈ [23,30] → **Mark for redaction**
- Remaining tokens: No overlap → Skip

**Result**: Both `"(John"` and `"Conway)"` are redacted, including parentheses, which provides clean visual redaction.

They are redacted because through our algorithm, we reason that a part of the token as overlapping within the things that we needed to redact and so we had to redact them. There's also the idea that a token could have multiple segments which just measn it's separated across multiple "shards" of the document due to how big the document is. A lot more complicated than it sounds, but if at least one segment overlaps, then we redact the whole thing.

In general, the way I'm handling tokens like they're word-like units, like strings separated by spaces. Even though that's onot entirely what tokens are, it's actually pretty effective for our purposes. Also this algorithm that we're using should be agnostic to whether you're using an OCR library or parsing from PyMuPDF:
1. Get the tokens per page, this is the wordlike unit that should have a bounding box when getting it from data source.
2. Reconstruct full text, and make sure each token has start and end corresponding to the full text. 
3. Do indexed-base search algorithm to find all tokens that are flagged for containing PIIs or make up a PII. 

Even if you're using Tesseract-OCR you should be able to get token-level data from the document.


## Implementation Requirements

### Prerequisites
1. **Complete Text String**: Access to `Document.text` with proper reading order
2. **Token Indices**: Each token must have `start` and `end` indices in `Document.text`
3. **Bounding Boxes**: Each token needs `BoundingPoly` for visual redaction
4. **Page Information**: Page number for each token to handle multi-page documents. Don't need to be a page number, but you just need a way to identify what page to redact a PII on.

### Google Document AI Integration

The Google Document AI API provides these requirements through:
- `Document.text`: Complete document text
- `pages[].tokens[]`: Token list per page
- `token.text_anchor.text_segments`: Index information
- `token.bounding_poly.vertices`: Bounding box coordinates

## Performance Optimizations

### 1. Field Masking
Reduce API response size by requesting only necessary fields:
```python
request = documentai_v1.ProcessRequest(
    name=processor.name,
    raw_document=raw_document,
    field_mask="text,pages,pages.tokens"
)
```

### 2. Entity Extraction Integration
Leverage Document AI's built-in entity extraction:
- Configure processor to extract specific PII types
- Use entity anchors to locate PII spans
- Map entity spans to overlapping tokens
- Apply bounding boxes for redaction

### 3. Token Filtering
Pre-filter tokens to remove empty strings and irrelevant tokens before processing.

## Algorithm Improvements and Considerations

### Strengths
- **Tokenization Resilience**: Handles cases where PII boundaries don't align with token boundaries
- **Multi-token Support**: Effectively processes PII spanning multiple tokens
- **Visual Accuracy**: Uses actual token bounding boxes for precise redaction
- **Contextual Redaction**: Includes adjacent punctuation/formatting for cleaner results

### Potential Issues and Mitigations

1. **Performance**: O(n×m) complexity where n = tokens, m = PII matches
   - **Solution**: Use spatial indexing or binary search on sorted token positions

2. **Edge Cases**: Index boundary conditions
   - **Solution**: Add bounds checking for `startIndex` and `endIndex`

3. **Complex Documents**: Very long documents with distant token spans
   - **Solution**: Process documents in chunks or use hierarchical token structures

4. **False Positives**: Tokens partially overlapping with PII spans
   - **Current approach is acceptable**: Better to over-redact than under-redact for privacy

## Portability Considerations

### Limitations
- Assumes availability of complete document text in reading order
- Requires token-level index mapping
- Depends on accurate bounding box information

### Future-Proofing
Create an abstraction layer that can adapt to different OCR engines:
```python
class OCRDocument:
    def get_full_text(self) -> str
    def get_tokens(self) -> List[Token]
    def get_token_indices(self, token: Token) -> Tuple[int, int]
    def get_bounding_box(self, token: Token) -> BoundingBox
```

## Conclusion

The index-based approach provides a more robust solution for multi-token PII detection compared to line reconstruction methods. While it has complexity trade-offs, the accuracy improvements and integration with Document AI's capabilities make it the preferred approach for production PII redaction systems.

The key insight is leveraging the complete document text as the source of truth for pattern matching, while using token-level information only for determining redaction boundaries and visual coordinates.