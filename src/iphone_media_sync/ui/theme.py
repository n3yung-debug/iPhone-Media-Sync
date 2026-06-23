"""A purple color theme (dark) applied app-wide via a Qt style sheet."""

from __future__ import annotations

# Palette
BG = "#1e1830"          # window background (deep purple-charcoal)
BG_ALT = "#271f3d"      # panels / inputs
BG_RAISED = "#2f2649"   # hovered / raised surfaces
BORDER = "#3d3160"      # subtle borders
TEXT = "#ece8f5"        # primary text
TEXT_MUTED = "#b3a9cc"  # secondary text
ACCENT = "#9d6bff"      # primary purple
ACCENT_HOVER = "#b389ff"
ACCENT_PRESSED = "#7d4fe0"
SELECTION = "#5a3da6"   # selected item background

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-size: 13px;
}}

QToolBar {{
    background-color: {BG_ALT};
    border: none;
    border-bottom: 1px solid {BORDER};
    spacing: 6px;
    padding: 4px;
}}

QStatusBar {{
    background-color: {BG_ALT};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {BG_ALT};
    color: {TEXT_MUTED};
    padding: 8px 18px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {ACCENT};
    color: white;
}}
QTabBar::tab:hover:!selected {{
    background: {BG_RAISED};
    color: {TEXT};
}}

/* Buttons */
QPushButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}
QPushButton:disabled {{
    background-color: {BG_RAISED};
    color: {TEXT_MUTED};
}}

/* Lists / thumbnail grids */
QListWidget {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    color: {TEXT};
    border-radius: 6px;
    padding: 4px;
}}
QListWidget::item:selected {{
    background-color: {SELECTION};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {BG_RAISED};
}}

/* Inputs */
QSpinBox, QLineEdit {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {ACCENT};
}}
QSpinBox:focus, QLineEdit:focus {{ border: 1px solid {ACCENT}; }}

QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BG_ALT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QCheckBox::indicator:hover {{ border: 1px solid {ACCENT_HOVER}; }}

/* Progress bar */
QProgressBar {{
    background-color: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    text-align: center;
    color: {TEXT};
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}

/* Scroll areas + bars */
QScrollArea {{ border: none; }}
QScrollBar:vertical {{
    background: {BG_ALT};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 6px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{
    background: {BG_ALT};
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 6px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

/* Dialogs / message boxes */
QDialog, QMessageBox {{ background-color: {BG}; }}

QToolTip {{
    background-color: {BG_RAISED};
    color: {TEXT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 4px;
}}
"""


def apply_theme(app) -> None:
    """Apply the purple theme to a QApplication."""
    app.setStyleSheet(STYLESHEET)
