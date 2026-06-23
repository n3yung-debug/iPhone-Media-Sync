"""Frozen-app entry point for PyInstaller.

Imports the package by its absolute name (so relative imports inside the
package resolve correctly) and runs the app.
"""

import sys

from iphone_media_sync.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
