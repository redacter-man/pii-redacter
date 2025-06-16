## Real World Example:

## Requirements and Introduction:
Let's create a program that scans pdf files, searches for certain PIIs, and then redacts those PIIs from the document. The redaction should look like a black box was drawn over the text. The PIIs we want to redact are:
  - Social security number
  - Bank account number
  - Routing number for bank account
  - Credit-Card numbers
  - Credit Scores
  - Other sensitive financial info and PIIs you'd find on a form but these are the main ones. 
  - Also it should be implemented within Python.

## High-Overview of User Journey
Here's how the workflow will work:
1. Client sends a Zip file containing the pdfs to be redacted.
2. Server unzips the zip file, identifies PIIs in each one, and redacts the zip files within the documents by deleting the text and drawing a black box in the pdf to indicate that something was redacted.
3. Server will zip up these output files and send them back to the user.

## Input Types to Expect
**Case 1: Text-based PDFs**
- Text is selectable/extractable (e.g., digital W4 forms, bank statements)
- Use PDF parsing libraries, no OCR needed
- May contain logos/images but text content is the focus

**Case 2: Image-based PDFs (requires OCR)**
- **Subcase 2a: Handwritten forms** - Scanned forms with handwritten responses (e.g., filled-out paper W4)
- **Subcase 2b: Machine-printed scans** - Photos/scans of printed documents (e.g., CIA docs, printed bank statements)

The key decision points become:
1. Can I extract selectable text? → Case 1
2. If OCR needed, is it primarily handwritten responses or printed text? → Case 2a vs 2b

---
## Workflow Strategies
The key insight here is that we should use a **detection-first approach** where we can automatically classify the PDF type and route it through the appropriate processing pipeline. I'll first show a unified workflow that we can use, and then the separate smaller workflows that make it up.

### Unified Workflow Strategy

#### Step 1: PDF Analysis And Classification
Here we do an initial pdf inspection:
  - Check if text is selectable/extractable.
  - Analyze text-to-image ratio.
  - Detect if OCR layer already exists.

Then create some classification logic:
- Text-based: $> 80%$ of the content is selectable context. Again this is that fillable federal W4 form.
- Image-based:
  1. A scanned hand-written document. Here the document probably needs OCR for hand-writing as we're assuming the PIIs are all hand-written as they probably are.
  2. A scanned digital document. Here the document probably needs OCR for machine-print. Here we're assuming the PIIs are all machine-print.

Though one approach is the idea of extracting all text (printed+handwritten). I mean this is pretty intuitive and it may be the only option we have. I can't really think of a document (either form or some kind of invoice or document), where you're going to be needing to detect PIIs that are hand-written and machine-printed. It's typically a document where you're filling out info or a document that has all of your info already. Assuming this, parsing both would be cool , but it would add a lot of extra OCR text "noise" (unnecessary) data into our parser.

#### Step 2: Content Extraction and Location Mapping.
- Use Regex patterns for PII detection.
- Map detected PIIs back to exact coordinates in the PDF. 

#### Step 3: Redaction and Output
- Draw black rectangles over PII locations. Of course make sure to also delete the original text that constructs the PII to ensure that the data is deleted.
- Preserve original PDF structure and formatting (this is kind of implied).
- Package the redacted versions of the PDFs into a zip file.



## Technology Stack 

### Core PDF Processing 
- **PyMuPDF (fitz):** Loading of PDF documents.

### OCR and Image Processing
There are a couple of selections in this part: 
- **Tesseract + pytesseract:** An open source OCR solution that mainly handles printed text. You can try to train it to recognize hand-written digits, but from what I'm seeing it's kind of error prone and can break a bit. For machine-printed documents, we'll try to use Tesseract! **Pillow (PIL)** is an image processing library, and it complements Tesseract.
- **PaddleOCR:** An open source OCR solution that handles printed text and hand written text. Though you'll need to specify the particular model for doing hand-written characters. Rumors say it can dual wield both machine printed and hande written characters in one pass, but I've yet to see it.
- **TrOCR:** A Microsoft backed OCR solution that handles handwritten text only.

The OCR is probably the hardest part of the project, which is not a surprise. The fact that we're dealing with The priority is having the ability to handle both print and hand-written text. Most OCR libraries aren't going to tell you whether the text that was parsed was printed or hand-written after the recognition step. I guess maybe a solution could be developing your own machine learning model that detects whether a character is machine-printed or hand written, then it does the OCR. Then we'd calculate the proportion of content that's hand written or machine printed. I mean this is all assuming a approach where we treat the image-based pdf as either text-based or hand-written, and then specific target one of them for OCR to minimize noise from extra data coming in. However, it feels like the easiest thing to do is if it's actually just an image-based pdf, run it with machine-printed and hand-written OCR. I can think of 2 scuffed approaches:

1. Approach 1 (Two OCR passes): Then apply machine-print OCR and redact any remaining information. If it's an image-based pdf, apply hand-written OCR first and redact any PIIs. This is kind of inefficient since you're doing two passes.
2. Approach 2: PaddleOCR supports both hand-written and machine 

### PII Detection
- **Regex:** Custom patterns for SSN, credit cards, routing numbers.
- **spaCy (Optional):** An NLP library with pre-trained models for named entity recognition. We may be able to use it to identify addresses, names, and thing slike that.

## Detailed Workflow for Each PDF Processing Case

### Case 1: Text-Based 
1. Extract text using a PyMuPDF
2. Apply PII detection patterns
3. Map PII locations to PDF coordinates
4. Draw redaction boxes and delete the original PII text
5. Save redacted pdf.

**Note:** If you run into limitations with PyMuPDF and the position of text, you should try out pdfplumber as it also preserves positioning information for text. Also detecting whether the pdf has text is pretty easy, just use PyMuPDF to extract text from it, if no text was returned, the pdf probably has no actual text. 

**Note 2 (Future Consideration):** Maybe in the future you'll deal with a text-based form where the main subject is the hand-writing. Maybe someone is using a federal w-4, and writing their answers in on an ipad lmao. I know, kind of niche, but just something to think about in the future.

### Running OCR on Text-Based PDFS: Effects and Risks
Talking about issues, even high quality oCR can be errors like character substitution errors (0 -> O), or something similar. As well as this, OCR mmay not preserve positioning or formatting for complex layouts. And finally it's unnecessary computational over head.

However the pros are that you have a uniform pdf parsing pipeline

### Case 2: Pure Image-Based (Needs OCR)
Here are two steps that should always happen:
1. Convert PDF pages to images. Most of the time this is needed so that the OCR works.
2. Optional: Preprocess the image (contrast, noise reduction) with OpenCV
3. Apply OCR, ideally in the end it should be machine print + hand-written:
  1. First do a pass with TrOCR for hand-written data.
  2. Second attempt machine print.
4. Detect PIIs in OCR results.
5. Map PIIs from OCR back ot PDF coordinates
6. Draw redaction boxes on the original PDF; make sure

## PII Detection Strategy
- SSN: \b\d{3}-?\d{2}-?\d{4}\b
- Credit Cards: \b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b
- Bank Routing numbers (identifies a bank): \b\d{9}\b; it's just a 9 digit code 
- Account numbers: typically 8 to 12 characters, but they can goup to 17 characters.


## Main Challenges being dealt with
1. Redaction Coordinate Mapping Accuracy: We can use PyMuPDF's `get_text("dict")` method which provides a bounding box for each text element. Doing this for all types could get challenging.

2. Text-based pdfs can still get pretty hard with like the segmentation of data. I think I saw a lot of empty data, so handling that wil 
3. Handling Image-Based PDFS:
  1. Already OCR applied, good treat it as text-based.
  2. No-OCR applied: Ideally use a one-pass system that has hand-written and machine print. Else use a common two pass system:
    - Hand written first
    - Then Machine print 

4. Performance at Scale: 
  - First maybe try timing it so that you process multiple pdfs at once. Run each as a separate process. I think this makes sense since a lot of these processes seem to be CPU bound? Have to test things out though

## Example Architecture and Implementation Plan
```Python
class PDFRedactor:
    def __init__(self):
        # Of course you'd need to define these lmao
        self.pii_detector = PIIDetector()
        self.ocr_engine = OCREngine()
        self.pdf_processor = PDFProcessor()
    
    def process_zip(self, zip_path):
        # Main entry point
        pass
    
    def classify_pdf(self, pdf_path):
        # Returns: 'text_based', 'needs_ocr'
        pass
    
    def extract_content(self, pdf_path, pdf_type):
        # Route to appropriate extraction method
        pass
    
    def detect_and_redact(self, pdf_path, content):
        # PII detection + redaction
        pass
```

## Takeaway
The project is actually pretty hard when you realize you have literally no limits on it. Also there are some many different cases for pdf data that can we thrown in:
  1. Text-based PDF: A pdf with selectable text, like a pdf of a textbook. Here target and redact the selectable text, no ocr needed.
  2. Image-based PDF (with digital print): Scans of legal documents that we have to OCR using a machine-print trained OCR model. Target and redact the machine print. 
  3. Image-based PDF (with hand-written characters): Pictures of stuff like notes from a kid's homework that they did on paper. Use OCR model for hand-writing and try to find any thing to redact.
  4. Image-based PDF (print and handwritten): Pictures of forms that people fill out by hand. Here you're not only dealing with machine-printed text, but also hand-written text. In most cases, you can reason that any PIIs are going to be hand-written so you'd want to use a hand-written model to target hand-written data. However how much of the document needs to be hand-written before you decide that it's this case, what's the ratio? This is diffcult, and to handle it you could just do two passes. but how do you know whether an image-based pdf is both print and hand-written? Are you going to do two passes for each image-based pdf? Yeah that's the issue.

## Credits:
- [PyMuPDF Docs](https://pymupdf.readthedocs.io/en/latest/tutorial.html)
- [Pytesseract Docs](https://pypi.org/project/pytesseract/)