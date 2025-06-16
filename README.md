# initial testing
## installing dependencies
__NOTE:__ something is weird with venvs on windows, so don't do that any more. you can just install all the python packages globally:
```bash
pip install -r requirements.txt
```
## installing necessary apps
make sure you have 

## other necessities
zipped folder of pdfs called `Masking.zip` in the directory in which you have the script
## running the script
then run the script to test
```bash
python .\helloworld.py
```

### Project Setup
1. Install `Python` from the company portal. 
2. Install UV via Python's PIP: `pip install uv`.
3. Now we'll use UV as the primary package manager.
4. Install backend packages: `cd backend && uv run sync`
5. When running apps with UV, it starts/creates the venv for you. However, if you still see squiggly lines when viewing code. Open your window to a `.py` file, go to bottom right where your python interpreter is, and change it to point to the `python.exe` file in the `.venv` folder that UV created. Now you should not see any squiggles and Python's autocomplete should work.

### Project Scripts
- TODO: List script for formatting, linting, etc.

```bash
# Formats all backend files; ensure you're in the 'backend' directory
uv run ruff format . 

uv run 

```

### Project
- TODO: Handle case for hand-written text that was shown during project meet.

## Credits
- [Astral UV Documentation](https://docs.astral.sh/uv/)
- [Ruff Documentation with UV](https://docs.astral.sh/ruff/)
- [PaddleOCR Documentation](https://paddlepaddle.github.io/PaddleOCR/main/en/index.html)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/)
- [Pillow Documentation](https://pillow.readthedocs.io/en/stable/)
- [OpenCV Documentation](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [open-cv Python](https://github.com/opencv/opencv-python)