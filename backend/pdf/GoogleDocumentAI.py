import os
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1
from google.cloud.documentai_v1.types import Document
from google.protobuf.field_mask_pb2 import FieldMask


# Set environment variable for authentication
path_to_service_json = os.path.join(
    os.path.dirname(__file__), "..", "credentials.json"
)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path_to_service_json

# Setup project ID, processor ID, and location;
project_id = "redacter-463315"
processor_id = "7796afb6598ad259"
location = "us"

# Set `api_endpoint` if you use a location other than "us".
opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

# Initialize Document AI client and get a reference to the processor
client = documentai_v1.DocumentProcessorServiceClient(client_options=opts)
full_processor_name = client.processor_path(project_id, location, processor_id)
request = documentai_v1.GetProcessorRequest(name=full_processor_name)
processor = client.get_processor(request=request)


def request_google_ocr(file_path: str) -> Document:
  """Make a request to the Document AI API to do OCR and process a document"""
  if not os.path.isfile(file_path):
    raise FileNotFoundError(f"No file found at path '{file_path}'")

  # Step by step:
  # 1. Read the file into memory
  with open(file_path, "rb") as f:
    file_content = f.read()

  # Only care about two pieces of data
  field_mask = FieldMask(paths=["text", "pages.tokens"])

  # 2. Load it as a RawDocument (binary data essentially) and set it as a pdf
  raw_document = documentai_v1.RawDocument(
    content=file_content, mime_type="application/pdf"
  )

  # 3. Create the request with the processor
  request = documentai_v1.ProcessRequest(
    name=processor.name, raw_document=raw_document, field_mask=field_mask
  )
  document = client.process_document(request=request).document

  return document


def save_document_as_json(document: Document, output_path: str) -> None:
  """Save a Document AI Document object as a JSON file"""
  os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Ensure directory exists

  json_string = Document.to_json(document)
  with open(output_path, "w", encoding="utf-8") as f:
    f.write(json_string)  # Write JSON string directly to file


def load_document_from_json(json_path: str) -> Document:
  """Load a Document AI Document object from a JSON file"""
  with open(json_path, "r", encoding="utf-8") as f:
    json_string = f.read()
    document = Document.from_json(json_string)  # Load json string into Document object

  return document
