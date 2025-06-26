from pdf.PDFRedactor import PDFRedactor
import os


def main():
  print("Started PDF Processing Application")


  work_dir = os.path.join(os.path.dirname(__file__), "jobs", "sample_job")


  input_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "06-text-essay.pdf")
  output_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "06-text-essay-redacted.pdf")

  if os.path.exists(input_path):
    PDFRedactor.process_single_pdf(work_dir, input_path)
  else:
    print("File DNE")
  
if __name__ == "__main__":
  main()