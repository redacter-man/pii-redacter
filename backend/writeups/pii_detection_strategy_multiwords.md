# PII Detection Strategy for Multi-Word Patterns

## The Problem
Word-level text extraction works well for single-token PII like SSNs (`123-45-6789`) or routing numbers (`021000021`). However, space-separated PII creates challenges:

- **Credit cards**: `4532 1234 5678 9012` becomes 4 separate words
- **Addresses**: `123 Main Street, Apt 4B` becomes 5+ separate words  
- **Phone numbers**: `(555) 123 4567` becomes 3-4 separate words

## Decent Approach: Line-Based Detection

**Strategy**: Reconstruct text into lines, run regex patterns, then map matches back to individual words for redaction.

### Steps:
1. **Extract words** with coordinates using `page.get_text("words")`
2. **Group words into lines** by Y-coordinate proximity
3. **Run PII regex patterns** on reconstructed line text
4. **Map matches back to words** for precise redaction

### Why This Works Better:
- **Context preservation**: Credit card `4532 1234 5678 9012` stays together on same line
- **Reduces false positives**: Prevents redacting unrelated `12` when routing number is `123456789012`
- **Real-world accuracy**: Addresses like `1425 Oak Drive, Unit 12B` get detected as complete entities

## Alternative Approach (Less Recommended)
Iterate through all words and check if each appears in any PII pattern. However, this creates false positives:
- Credit card `4532 1234 5678 9012` could incorrectly redact unrelated `45` elsewhere
- Address `1425 Oak Drive` could redact random `14` in a date

## Considerations
I don't know if this makes a difference for pdf parsed pages though?


Y-coordinate redaction could be something interesting but that happens later.


## Real-World Examples
- **Bank statements**: Credit cards, account numbers, addresses all typically appear on single lines
- **Tax documents**: SSNs, employer IDs, addresses maintain line integrity  
- **Medical records**: Patient IDs, phone numbers, addresses follow standard formatting

The line-based approach respects document structure while ensuring comprehensive PII coverage.