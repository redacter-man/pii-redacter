"""
The __init__.py file marks a directory as a Python package, allowing you to import modules from it as if it were a standalone module.
Even if the file is empty, Python treats the folder like a package, enabling imports like from mypackage import mymodule.
This file is essential for older versions of Python (<3.3), but it's still a good practice to include it explicitly for clarity and
package control. You can also place package-level variables or initialization code inside it if needed — such as setting up logging or defining what gets exposed via __all__.
"""
