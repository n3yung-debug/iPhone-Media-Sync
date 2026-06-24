"""Entry point: ``python -m iphone_media_sync``."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .core.config import APP_DIR

LOG_DIR = APP_DIR / "logs"
LOG_PATH = LOG_DIR / "app.log"


def setup_logging() -> Path:
    """Configure root logging to a rotating file (and stderr). Returns the path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)
    return LOG_PATH


def main() -> int:
    log_path = setup_logging()
    logging.getLogger(__name__).info("Starting iPhone Media Sync (log: %s)", log_path)

    # Imported after logging is configured.
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import __version__
    from .core.config import Config
    from .ui.main_window import MainWindow
    from .ui.resources import APP_ICON
    from .ui.theme import apply_theme

    app = QApplication(sys.argv)
    app.setApplicationName("iPhone Media Sync")
    app.setApplicationVersion(__version__)
    if APP_ICON.exists():
        app.setWindowIcon(QIcon(str(APP_ICON)))
    apply_theme(app, Config.load().theme)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
