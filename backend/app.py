from pdf.PDFRedactor import PDFRedactor
import os


def main():
    print("Started PDF Processing Application")

    input_path = os.path.join(os.path.dirname(__file__), "pdf", "test_data", "credit-app-3.pdf")

    if os.path.exists(input_path):
        # Process the PDF and get the output directory
        output_dir = PDFRedactor.process_single_pdf(input_path)
        print(f"Processing complete! Check output directory: {output_dir}")
    else:
        print("File DNE")
  
if __name__ == "__main__":
    main()