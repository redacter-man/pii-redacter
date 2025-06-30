from pdf.PDFRedactor import PDFRedactor
import os, time


def test_all_pdfs():
  job_base_dir = os.path.join(os.path.dirname(__file__), "jobs")
  test_data_dir = os.path.join(os.path.dirname(__file__), "pdf", "test_data")
  os.makedirs(job_base_dir, exist_ok=True)

  job_id = 0
  for element in os.listdir(test_data_dir):
      input_path = os.path.join(test_data_dir, element)
      if os.path.isfile(input_path) and element.lower().endswith(".pdf"):
          work_dir = os.path.join(job_base_dir, f"{job_id}")
          os.makedirs(work_dir, exist_ok=True)
          print(f"Processing {input_path} into {work_dir}")
          PDFRedactor.process_single_pdf(work_dir, input_path)
          job_id += 1
  return 

   

def main():
  print("Started PDF Processing Application")


  job_id = int(time.time())
  job_base_dir = os.path.join(os.path.dirname(__file__), "jobs")
  job_dir = os.path.join(job_base_dir, f"{job_id}")
  os.makedirs(job_dir, exist_ok=True)

  # Standard workflow
  
  input_path = os.path.join(
    os.path.dirname(__file__), "pdf", "test_data", "06-ocr-essay.pdf"
  )

  if os.path.isfile(input_path):
    PDFRedactor.process_single_pdf(job_dir, input_path)
  else:
    print("File DNE")


if __name__ == "__main__":
  main()
