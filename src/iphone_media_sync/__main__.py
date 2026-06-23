"""Entry point: ``python -m iphone_media_sync``."""

from __future__ import annotations

import sys


def main() -> int:
    # Imported lazily so that `--help`-style failures don't require a full Qt
    # install just to print an error.
    from PySide6.QtWidgets import QApplication

    from .ui.main_window import MainWindow
    from .ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("iPhone Media Sync")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
