from pdf.PDFRedactor import PDFRedactor
import os


def main():
  print("Started PDF Processing Application")

  input_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "Mask2.pdf")
  output_path = os.path.join(
    os.path.dirname(__file__), "pdf", "test_data", "Mask2_redacted.pdf"
  )

  if os.path.exists(input_path):
    PDFRedactor.process_single_pdf(input_path, output_path)
  else:
    print("File DNE")


if __name__ == "__main__":
  main()
