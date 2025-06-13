# initial testing
## installing dependencies
__NOTE:__ something is weird with venvs on windows, so don't do that any more. you can just install all the python packages globally:
```bash
pip install -r requirements.txt
```
## installing necessary apps
make sure you have `Python` and `Tesseract-OCR` installed from the Company Portal

the installer puts python on your path but not tesseract. it should install to the path `C:\Program Files\Tesseract-OCR`. If it doesn't install there, you will need to change the `tesseract_cmd` variable that is set at the top of the main function in the script so that it targets where your `tesseract.exe` is located.
## other necessities
zipped folder of pdfs called `Masking.zip` in the directory in which you have the script
## running the script
then run the script to test
```bash
python .\helloworld.py
```