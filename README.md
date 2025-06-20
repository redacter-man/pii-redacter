# PII Redacter 

## Project Setup
1. Install `Python` from the Infosys Company Portal. 
2. Clone this repo.
2. Go to the backend folder and create a virtual environment using this command or similar: `python3 -m venv .venv`; 
3. Activate virtual environment with `source ./.venv/bin/activate`and do `&& pip install -r requirements.txt`
  - Note: Ignore steps 2 and 3 since virtual environments don't work. Instead just install all things globally. I'm just speaking hypothetically here if things were best practice.
4. Obtain the Google Cloud project's `.json` file containing the credentials.
  - **Note:** Should be ignored by `.env` later.
5. Run the project 
```python ./app.py

```

## Scripts
```bash
# Formats all your code; try to do this before committing. 
ruff format .
```


## Credits
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/)
- [Document AI Google](https://cloud.google.com/document-ai/docs/create-processor)
