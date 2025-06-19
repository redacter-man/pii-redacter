import zipfile, os
from pdf.PDFProcessor import PDFProcessor
from pdf.PiiDetector import PiiDetector
from pdf.PageData import print_page_data


class PDFRedactor:
  """A class with static methods that will do the orchestration between the helper classes."""

  def process_zip(zip_path: str) -> None:
    # Main entry point in the program, this starts the entire workflow, but the idea would be this redacts all pdf files within the zipfile

    # Step 1: Check if the path points to a zip file
    if not os.path.isfile(zip_path):
      raise FileNotFoundError(
        f"Failed to open zip file at path {zip_path}; Does not exist!"
      )

    # Step 2: Setup folder environment where PDF input and output data will be stored for this particular job
    # job_id = int(time.time())
    job_id = "test"
    job_dir = os.path.join(os.path.dirname(__file__), "jobs", job_id)
    input_dir = os.path.join(job_dir, "input")
    output_dir = os.path.join(job_dir, "output")
    os.makedirs(job_dir, exists_ok=True)
    os.mkdir(input_dir)
    os.mkdir(output_dir)

    # Step 3: Extract pdf files from zip file and save them to job's input and output dir
    # Note: I don't know if this works with nested directories or not yet, but right now assume the zip file has only pdfs
    with zipfile.ZipFile(zip_path, "r") as zip_file:
      zip_file.extractall(input_dir)

    # Step 4: Redact all zip files in /jobs/{jobId}/{output_dir} and save redacted zip files /jobs/{jobId}/{output}
    # Note: Ideally it'd be nice for it to look like this so that I can easily compare multiple tests. The process_single_pdf function should modify the pdf in-place.
    for filename in os.listdir(input_dir):
      full_path = os.path.join(input_dir, filename)
      output_path = os.path.join(output_dir, filename)
      PDFRedactor.process_single_pdf(full_path, output_path)

  def process_single_pdf(pdf_path: str, output_path: str) -> None:
    """Redacts a single pdf file

    Step by Step Algorithm:
    1. Load the PDF in memory using the PDFProcessor class
    2. Attempt to extract text from the pdf. If there was no text, then it's likely an
      image-based pdf. In that case, apply hand-written OCR model to the pdf.Now try to extract text from it.

    3. Now that we have the text, we need to do some PII redactions. You need to map the text for
      any piis to a coordinate system. If you're doing OCR, you may have to deal with the image
      coordinate system meaning you may have to map things over. If dealing with the MuPDF
      system, it's going to be a bit more easier for the PDFProcessor class.

    ### Challenging Issue: Coordinates and Mapping

    My vision for this workflow is that with each word or text that is extracted, we'll have it in form:
      - (text, x, y, width, height), where
      - text: The actual text that's detected in string form
      - x: X-coordinate of the top left corner of the bounding box of that text.
      - y: Y-coordinate of the top left corner of the bounding box of that text.
      - width: Width of the bounding box
      - height: height of the bounding box.

    Now here are some issues and todos we need to tackle:
    - We need to update the extract_text() method to return data in that form we just came up with. This is done with page.get_text("words"). It's not exactly in the form
      we want, but it seems like we have enough data to do bounding box redactions so that's good enough. Everything will become uniform later.
    - When applying OCR, the coordinate system of an image is different from the coordinate system of a PDF or MuPDF. We'll want to
      convert those coordinates and dimensions to that of MuPDF, or we'll want to apply those redactions within the OCR engine then
    - I think most OCRs, or at least PaddleOCR will be returning data like the line number, block number.
    """

    pdf_processor: PDFProcessor = PDFProcessor(pdf_path, output_path)
    for page in pdf_processor.pdf_doc:
      # List of objects in form: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
      # Or dictionary form is fine too

      page_data = pdf_processor.extract_text(page)
      

      if page_data.is_empty:
        # Apply OCR:
        #   1. Apply hand-written OCR model
        #   2. Apply machine print OCR model
        # Combine the results into one array. 
        # Note: When applying OCR, you're probably going to turn the pdf page into an image, and then your image is going to detect the bounding boxes of the text in the image, which 
        # is on a different coordinate field, with different stuff to work with. You have two different options:
        #   1. You can either convert the bounding boxes back into PyMuPDF's format, which requires some kind of transformation matrix.
        #   2. Or you could save and redact the text elements within the image itself. Then save the image to pdf form. This is probably 
        #      Quite a bit easier, and maybe a little more reliable. In this case though, we'd have two clean conditional branches which would be nice.
        print("Apply OCR")

      # At this point we have some type of data
      print("Parsed PDF Text: ")
      print_page_data(page_data)
      
      print("Detected PII Elements")
      pii_elements = PiiDetector.detect_page_piis(page_data)
      for pii in pii_elements:
        
        # redacts the text so only the PII is redacted and not the label as well
        pdf_processor.redact_pdf_text(page, pii.text)  
      page.apply_redactions()
    
    # Save and close the changes; pdf is outputted to the output path now
    pdf_processor.save_and_close()