import logging


logger = logging.getLogger("PDF App")
logging.basicConfig(level=logging.INFO)

# Prevent duplicate logs if this module gets imported multiple times
if not logger.handlers:
  # Console handler
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)

  # File handler
  file_handler = logging.FileHandler("app.log")
  file_handler.setLevel(logging.DEBUG)

  # Formatter
  formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
  console_handler.setFormatter(formatter)
  file_handler.setFormatter(formatter)

  # Add handlers to logger
  logger.addHandler(console_handler)
  logger.addHandler(file_handler)

# Optional: prevent log propagation to root logger
logger.propagate = False
