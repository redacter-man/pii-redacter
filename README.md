# PII Redaction Tool

## Introduction

The PII Redaction Tool is a command-line Python application designed to automatically detect and redact Personally Identifiable Information (PII) from PDF documents. The application handles both text-based and image-based PDFs, providing comprehensive coverage for various document types, including handwritten and printed forms.

### Key Features

- **Multi-format PDF Support**: Processes both text-based and image-based PDF files
- **Comprehensive PII Detection**: Identifies and redacts multiple types of sensitive information
- **Bounding Box Redaction**: Precise redaction using bounding box coordinates
- **Detailed Logging**: Generates reports of detected PII and redaction tokens
- **Organized Output**: Creates structured output directories with original, redacted, and analysis files

### Supported PII Types

The application currently detects and redacts the following types of PII:

- Social Security Numbers (SSN)
- Phone Numbers
- Bank Routing Numbers
- Account Numbers
- Credit Scores
- Credit Score Ratings
- Email Addresses
- Credit Card Numbers

## Tech Stack

### Core Technologies

- **Python**: Primary programming language
- **PyMuPDF**: Text-based PDF parsing and processing
- **Google Cloud Document AI API**: OCR processing for image-based PDFs and handwritten content

### Dependencies

- **PyMuPDF**: For extracting text from text-based PDFs and handling PDF manipulations
- **Google Cloud Document AI**: For optical character recognition (OCR) on image-based PDFs
- **Regular Expressions**: Pattern matching for PII detection
- **Standard Python Libraries**: File handling, ZIP processing, and CLI operations

### Infrastructure Requirements

- **Google Cloud Platform**: Access to Document AI API
- **Python Environment**: Python 3.x with pip package management
- **File System**: Local storage for input processing and output generation

## Project Structure

```
pii-redaction-tool/
├── app.py                 # Main entry point and CLI interface
├── pdf/                   # PDF processing modules
│   ├── __init__.py
│   ├── ocr_processor.py   # Google Doc AI integration
│   ├── text_extractor.py  # PyMuPDF text extraction
│   ├── pii_detector.py    # Regex-based PII detection
│   └── redactor.py        # Bounding box redaction logic
├── jobs/                  # Output directory for processed files
├── requirements.txt       # Python dependencies
├── config/                # Configuration files
└── README.md              # Basic project information
```

## Main User Workflows

### Workflow 1: Single PDF Processing

1. **Input**: User provides path to a single PDF file via CLI
2. **Analysis**: Application determines if PDF is text-based or image-based
3. **Processing**: 
   - Text-based PDFs: Direct text extraction using PyMuPDF
   - Image-based PDFs: OCR processing using Google Document AI API
4. **PII Detection**: Regex patterns scan extracted text for sensitive information
5. **Redaction**: Bounding box coordinates are used to redact identified PII
6. **Output Generation**: Creates job directory containing:
   - Original PDF file
   - Redacted PDF file

### Workflow 2: Batch ZIP Processing

1. **Input**: User provides path to ZIP file containing multiple PDFs
2. **Extraction**: Application unzips files to the temporary processing directory
3. **Batch Processing**: Each PDF in the archive follows the single PDF workflow
4. **Consolidated Output**: Creates a directory in the jobs folder, identified by the date and time the job was scheduled, which contains:
   - Folder of input PDFs before redaction, called `input`
   - Folder of input PDFs after redaction, called `output`

### Workflow 3: Output Review and Analysis

1. **Job Directory Access**: User navigates to generated jobs directory
2. **File Comparison**: Review original vs. redacted PDFs
3. **PII Analysis**: Examine detected PII reports for accuracy
4. **Quality Assurance**: Verify redaction completeness and accuracy

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- Google Cloud Platform account with Document AI API enabled
- pip package manager

### Installation Steps

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd pii-redaction-tool
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Google Cloud Setup** - detailed setup instructions [here](https://github.com/redacter-man/pii-redacter/issues/3)
   - Create a Google Cloud project
   - Enable the Document AI API
   - Create a service account and download the JSON key file
   - Set the environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
     ```

4. **Verify Installation**
   ```bash
   python app.py --help
   ```

### Configuration

1. **API Configuration**: Ensure Google Cloud credentials are properly configured
2. **Output Directory**: The `jobs/` directory will be created automatically
3. **Regex Patterns**: PII detection patterns can be customized in the `pdf/pii_detector.py` module

## Usage
For basic usage, you would manually modify the path of the input pdf file in the source code. If you want to unzip a zipfile you'd have to use the zipfile processing function that we defined in `PDFRedactor.py`.


## Output Structure
For each processed document, the application creates a job directory with the following structure:
```
jobs/
└── job_<timestamp>/
    ├── input/
    │   ├── original_document1.pdf      # Original input file
    │   └── original_document2.pdf
    ├── output/      
    │   ├── masked-original_document1.pdf      # PII-redacted version
    │   └── masked-original_document2.pdf
    └── masked-<zip-file-name>.zip
```

## Development

### Adding New PII Types
1. Update regex patterns in `pdf/pii_detector.py`
2. Add corresponding test cases
3. Update documentation with new PII type.

## Future Enhancements
- Additional PII type detection
- Web-based interface
- Batch processing optimization
- Custom redaction patterns
- Integration with cloud storage services
