from dotenv import load_dotenv
import os
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1

load_dotenv()


# TODO(developer): Update and uncomment these variables before running the sample.
project_id = "redacter-463315"

# Processor ID as hexadecimal characters.
# Not to be confused with the Processor Display Name.
processor_id = "7796afb6598ad259"

# Processor location. For example: "us" or "eu".
location = "us"

# Path for file to process.
file_path = os.path.join(os.path.dirname(__file__), "test_data", "1040-1.pdf")

# Set `api_endpoint` if you use a location other than "us".
opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

# Initialize Document AI client.
client = documentai_v1.DocumentProcessorServiceClient(client_options=opts)

# Get the Fully-qualified Processor path.
full_processor_name = client.processor_path(project_id, location, processor_id)

# Get a Processor reference.
request = documentai_v1.GetProcessorRequest(name=full_processor_name)
processor = client.get_processor(request=request)

# `processor.name` is the full resource name of the processor.
# For example: `projects/{project_id}/locations/{location}/processors/{processor_id}`
print(f"Processor Name: {processor.name}")

# Read the file into memory.
with open(file_path, "rb") as image:
    image_content = image.read()

# Load binary data.
# For supported MIME types, refer to https://cloud.google.com/document-ai/docs/file-types
raw_document = documentai_v1.RawDocument(
    content=image_content,
    mime_type="application/pdf",
)

# Send a request and get the processed document.
request = documentai_v1.ProcessRequest(name=processor.name, raw_document=raw_document)
result = client.process_document(request=request)
document = result.document

# Read the text recognition output from the processor.
# For a full list of `Document` object attributes, reference this page:
# https://cloud.google.com/document-ai/docs/reference/rest/v1/Document
print("The document contains the following text:")
print(document.text)