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
    """Redacts a single pdf file"""

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