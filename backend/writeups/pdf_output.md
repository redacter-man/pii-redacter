

## PDF Layout Terminology

### What are blocks in PDF layout terminology

A block is a grouping of content that forms a logical or visual unit such as:
- A paragraph
- A table
- A text column
- An image
- A form field
- A separate region of text visually separated by whitespace or layout

Blocks are used to structure content spatially, making it easier to:
- Reconstruct document layouts
- Perform region-specific OCR
- Extract text meaningfully (insteaed of line-by-line gibberish)

## Understanding PyMuPDF Output Structure
```json
{
  "width": "floating point representing the width of the pdf page",
  "height": "floating point representing the height of the pdf page",

  // An array of blocks. Blocks
  "blocks": [
    // ...
    {
      // Id number for a given block; type indicates the type of "block" so PyMuPDF probably has a list somewhere.
      "number": 0,
      "type": 0, 
      // 4 coordinates for the bounding box containing this block
      "bbox": (a,b,c,d)

      // Array of "lines" so lines of text in the block.
      "lines": [
        // ...

        // A singular line
        {
          "wmode": 0, // Writing mode
          "dir": (1.0, 0.0), // Text direction as a vector, this is horizontal
          "bbox": (a,b,c,d), // Bounding box of the line
          // Array of "spans" or words for the line
          "spans": [
            {
              "size": <some_data>,
              "flags": <some_data>, // bitmask representing font flags or something
              "bidi": <some_data>,
              "char_flags": <some_data>, 
              "font": <some_data>,
              "color": <some_data>,
              "alpha": <some_data>,
              "ascender": <some_data>,
              "descender": <some_data>,
              "text": 'SSN: 123-45-7890',
              "bbox": (x0, y0, x1, y1) // bounding box of the word
              "origin": (x, y) // Top-level corner coordinates of the bounding box
            }
            
          ]
        }
        // ...
      ]
    }
    // ...
  ]
}
```

Notice that even though there's a space between `SSN:` or `123-45-7890`, PyMuPDF parses the entire thing within a single "span" (borrowed from web development domain) or text-chunk. Now that we have an idea of what kind of data we're dealing with, we can more easily know what data we're dealing with when parsing text directly and also dealing with piis. 

So if you were trying to detect something like an SSN, we should apply search for a match within the span. Now we're looking a bit far ahead, but we should probably also be familiar with the way the OCR library PaddleOCR sends back pdf page data.

Also looking further ahead, it seems maybe credit card number detection could be a little easier since they may appear on one line.

## Understanding OCR Output Structure
