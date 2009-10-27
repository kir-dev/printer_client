"""Creates a Windows executable from the source files"""

from distutils.core import setup
import py2exe

setup(
    options={
        "py2exe": {
            "dist_dir": "../dist",
            "dll_excludes": ["MSVCP90.dll"],
            "bundle_files": 1,
            "compressed": True
            }
        },
    windows=[{
        "script": "main.py",
        "dest_base": "PrinterClient",
        "icon_resources": [(1, "HP-Printer.ico")]
        }],
    zipfile=None,
    )
