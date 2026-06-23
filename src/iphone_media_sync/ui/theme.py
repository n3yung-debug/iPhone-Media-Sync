"""Purple UI themes (dark + light), applied app-wide via a Qt style sheet."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str
    bg_alt: str
    bg_raised: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    selection: str


DARK = Palette(
    bg="#1e1830",
    bg_alt="#271f3d",
    bg_raised="#2f2649",
    border="#3d3160",
    text="#ece8f5",
    text_muted="#b3a9cc",
    accent="#9d6bff",
    accent_hover="#b389ff",
    accent_pressed="#7d4fe0",
    selection="#5a3da6",
)

LIGHT = Palette(
    bg="#f5f1fb",
    bg_alt="#ece4f7",
    bg_raised="#e0d4f2",
    border="#c9b6e8",
    text="#241b33",
    text_muted="#6b5b86",
    accent="#7c4dff",
    accent_hover="#9168ff",
    accent_pressed="#6336e0",
    selection="#c9b0ff",
)

THEMES = {"dark": DARK, "light": LIGHT}

# Module-level defaults used by lightweight widgets (e.g. grid placeholder
# tiles). These follow the dark palette; the tiles are tiny so it's not worth
# re-theming them live.
BG_RAISED = DARK.bg_raised
TEXT_MUTED = DARK.text_muted


def build_stylesheet(p: Palette) -> str:
    return f"""
QWidget {{
    background-color: {p.bg};
    color: {p.text};
    font-size: 13px;
}}

QToolBar {{
    background-color: {p.bg_alt};
    border: none;
    border-bottom: 1px solid {p.border};
    spacing: 6px;
    padding: 4px;
}}

QStatusBar {{
    background-color: {p.bg_alt};
    border-top: 1px solid {p.border};
    color: {p.text_muted};
}}

QTabWidget::pane {{
    border: 1px solid {p.border};
    border-radius: 6px;
    top: -1px;
}}
QTabBar::tab {{
    background: {p.bg_alt};
    color: {p.text_muted};
    padding: 8px 18px;
    border: 1px solid {p.border};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {p.accent};
    color: white;
}}
QTabBar::tab:hover:!selected {{
    background: {p.bg_raised};
    color: {p.text};
}}

QPushButton {{
    background-color: {p.accent};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: {p.accent_hover}; }}
QPushButton:pressed {{ background-color: {p.accent_pressed}; }}
QPushButton:disabled {{
    background-color: {p.bg_raised};
    color: {p.text_muted};
}}

QListWidget {{
    background-color: {p.bg_alt};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    color: {p.text};
    border-radius: 6px;
    padding: 4px;
}}
QListWidget::item:selected {{
    background-color: {p.selection};
    color: white;
}}
QListWidget::item:hover {{
    background-color: {p.bg_raised};
}}

QLineEdit, QSpinBox, QComboBox, QDateEdit {{
    background-color: {p.bg_alt};
    border: 1px solid {p.border};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {p.accent};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
    border: 1px solid {p.accent};
}}

QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p.border};
    border-radius: 4px;
    background: {p.bg_alt};
}}
QCheckBox::indicator:checked {{
    background: {p.accent};
    border: 1px solid {p.accent};
}}
QCheckBox::indicator:hover {{ border: 1px solid {p.accent_hover}; }}

QProgressBar {{
    background-color: {p.bg_alt};
    border: 1px solid {p.border};
    border-radius: 6px;
    text-align: center;
    color: {p.text};
    height: 18px;
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: 5px;
}}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {p.bg_alt}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {p.border};
    border-radius: 6px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {p.accent}; }}
QScrollBar:horizontal {{ background: {p.bg_alt}; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {p.border};
    border-radius: 6px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{ background: {p.accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

QDialog, QMessageBox {{ background-color: {p.bg}; }}

QToolTip {{
    background-color: {p.bg_raised};
    color: {p.text};
    border: 1px solid {p.accent};
    border-radius: 4px;
    padding: 4px;
}}
"""


def apply_theme(app, theme: str = "dark") -> None:
    """Apply a named purple theme ('dark' or 'light') to a QApplication."""
    palette = THEMES.get(theme, DARK)
    app.setStyleSheet(build_stylesheet(palette))
