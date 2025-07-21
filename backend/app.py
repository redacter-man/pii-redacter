from pdf.PDFRedactor import PDFRedactor
import os
from datetime import datetime

def main(): 
  print("Started PDF Processing Application")

  # work_dir = os.path.join(os.path.dirname(__file__), "output", "test_run")
  # input_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "01-text-mask.pdf")
  # PDFRedactor.process_single_pdf(work_dir, input_path)

  zip_file_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "test-text-only.zip")

  id = datetime.now().isoformat(timespec="seconds").replace(":", "-")
  work_dir = os.path.join(os.path.dirname(__file__), "output", f"jobs_{id}")
  if not os.path.isfile(zip_file_path):
    raise FileNotFoundError(f"PII-Redactor: Zip File at path '{zip_file_path}' doesn't exist.")
  PDFRedactor.process_zip(work_dir, zip_file_path)
  





  

if __name__ == "__main__":
  main()
