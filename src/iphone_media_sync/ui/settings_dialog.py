"""Settings dialog: destinations, dedupe/delete options, foldering, theme."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..core.config import Config

_TEMPLATES = ["{year}/{date}", "{year}/{month}", "{date}", "{year}"]


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 560)
        self._config = config

        self._targets = QListWidget()
        self._targets.addItems(config.backup_targets)
        add_btn = QPushButton("Add folder…")
        remove_btn = QPushButton("Remove selected")
        add_btn.clicked.connect(self._add_target)
        remove_btn.clicked.connect(self._remove_target)

        target_buttons = QHBoxLayout()
        target_buttons.addWidget(add_btn)
        target_buttons.addWidget(remove_btn)
        target_buttons.addStretch(1)

        self._folder_template = QComboBox()
        self._folder_template.setEditable(True)
        self._folder_template.addItems(_TEMPLATES)
        self._folder_template.setCurrentText(config.folder_template)
        self._folder_template.setToolTip(
            "Folder layout under each destination. Tokens: {year} {month} {date}."
        )

        self._exact = QCheckBox("Detect exact (byte-identical) duplicates")
        self._exact.setChecked(config.detect_exact)
        self._perceptual = QCheckBox("Detect visually-similar photos")
        self._perceptual.setChecked(config.detect_perceptual)

        self._threshold = QSpinBox()
        self._threshold.setRange(0, 20)
        self._threshold.setValue(config.perceptual_threshold)
        self._threshold.setPrefix("similarity ≤ ")

        self._require_backup = QCheckBox(
            "Only allow deleting phone media that is already backed up"
        )
        self._require_backup.setChecked(config.require_backup_before_delete)

        self._blurry = QDoubleSpinBox()
        self._blurry.setRange(0, 100000)
        self._blurry.setDecimals(0)
        self._blurry.setValue(config.blurry_threshold)
        self._blurry.setToolTip("Photos with sharpness below this are 'blurry' candidates.")

        self._large_video = QSpinBox()
        self._large_video.setRange(1, 100000)
        self._large_video.setSuffix(" MB")
        self._large_video.setValue(config.large_video_mb)

        self._theme = QComboBox()
        self._theme.addItems(["dark", "light"])
        self._theme.setCurrentText(config.theme)

        self._check_updates = QCheckBox("Check for updates on startup")
        self._check_updates.setChecked(config.check_updates)

        form = QFormLayout()
        form.addRow("Folder layout:", self._folder_template)
        form.addRow("Blurry threshold:", self._blurry)
        form.addRow("Large video size:", self._large_video)
        form.addRow("Theme:", self._theme)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Backup destinations (copies go to every folder):"))
        layout.addWidget(self._targets, 1)
        layout.addLayout(target_buttons)
        layout.addSpacing(8)
        layout.addWidget(self._exact)
        layout.addWidget(self._perceptual)
        layout.addWidget(self._threshold)
        layout.addSpacing(8)
        layout.addWidget(self._require_backup)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addWidget(self._check_updates)
        layout.addWidget(buttons)

    def _add_target(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose backup folder")
        if folder:
            self._targets.addItem(folder)

    def _remove_target(self) -> None:
        for item in self._targets.selectedItems():
            self._targets.takeItem(self._targets.row(item))

    def result_config(self) -> Config:
        self._config.backup_targets = [
            self._targets.item(i).text() for i in range(self._targets.count())
        ]
        self._config.folder_template = self._folder_template.currentText().strip() or "{year}/{date}"
        self._config.detect_exact = self._exact.isChecked()
        self._config.detect_perceptual = self._perceptual.isChecked()
        self._config.perceptual_threshold = self._threshold.value()
        self._config.require_backup_before_delete = self._require_backup.isChecked()
        self._config.blurry_threshold = self._blurry.value()
        self._config.large_video_mb = self._large_video.value()
        self._config.theme = self._theme.currentText()
        self._config.check_updates = self._check_updates.isChecked()
        return self._config
