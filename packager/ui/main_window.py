import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTabWidget, QTextEdit, QCheckBox,
    QProgressBar, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from packager.core.metadata_parser import get_inference_models
from packager.core.copier import PackagerThread

class PackagerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Packager Tool")
        
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ---------------------------------------------------------
        # Top Header: Target Directory
        # ---------------------------------------------------------
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Target Package Directory (<userpath>):"))
        
        self.userpath_edit = QLineEdit()
        self.userpath_edit.setPlaceholderText("Drag and drop or browse target destination directory...")
        header_layout.addWidget(self.userpath_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_userpath)
        header_layout.addWidget(browse_btn)
        
        main_layout.addLayout(header_layout)
        
        # ---------------------------------------------------------
        # Tabs
        # ---------------------------------------------------------
        self.tabs = QTabWidget()
        
        # --- MLS Tab ---
        mls_tab = QWidget()
        mls_layout = QVBoxLayout(mls_tab)
        mls_layout.addWidget(QLabel("Enter MLS symlink paths (one per line):"))
        self.mls_text = QTextEdit()
        self.mls_text.setPlaceholderText("/jobs/GPWRL/...")
        mls_layout.addWidget(self.mls_text)
        self.tabs.addTab(mls_tab, "MLS")
        
        # --- Inference Tab ---
        inf_tab = QWidget()
        inf_layout = QVBoxLayout(inf_tab)
        inf_layout.addWidget(QLabel("Enter Inference EXR paths (one per line):"))
        self.inf_text = QTextEdit()
        self.inf_text.setPlaceholderText("/jobs/GPWRL/...")
        self.inf_text.textChanged.connect(self._on_inference_changed)
        inf_layout.addWidget(self.inf_text)
        
        self.extract_models_cb = QCheckBox("Auto-Extract Models to Models Tab")
        self.extract_models_cb.setChecked(True)
        inf_layout.addWidget(self.extract_models_cb)
        self.tabs.addTab(inf_tab, "Inference")
        
        # --- Models Tab ---
        mod_tab = QWidget()
        mod_layout = QVBoxLayout(mod_tab)
        mod_layout.addWidget(QLabel("Models to copy (auto-populated or manual):"))
        self.mod_text = QTextEdit()
        self.mod_text.setPlaceholderText("/jobs/GPWRL/ASSET/utility/face_cache/...")
        mod_layout.addWidget(self.mod_text)
        self.tabs.addTab(mod_tab, "Models")
        
        main_layout.addWidget(self.tabs)
        
        # ---------------------------------------------------------
        # Bottom Controls
        # ---------------------------------------------------------
        control_layout = QHBoxLayout()
        
        self.dry_run_cb = QCheckBox("Dry Run (Simulate copy, do not write files)")
        self.dry_run_cb.setChecked(True)
        control_layout.addWidget(self.dry_run_cb)
        
        control_layout.addStretch()
        
        self.package_btn = QPushButton("📦 Package All")
        self.package_btn.setStyleSheet("background-color: #2ea043; color: white; font-weight: bold; padding: 8px 16px;")
        self.package_btn.clicked.connect(self._run_packaging)
        control_layout.addWidget(self.package_btn)
        
        main_layout.addLayout(control_layout)
        
        # ---------------------------------------------------------
        # Log & Progress
        # ---------------------------------------------------------
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #0d1117; color: #c9d1d9; font-family: Consolas, monospace;")
        main_layout.addWidget(self.log_area)

    def _browse_userpath(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Target Package Directory")
        if dir_path:
            self.userpath_edit.setText(dir_path)

    def _on_inference_changed(self):
        if not self.extract_models_cb.isChecked():
            return
            
        paths = [p.strip() for p in self.inf_text.toPlainText().split('\n') if p.strip()]
        if not paths:
            return
            
        all_models = []
        for path in paths:
            models = get_inference_models(path)
            all_models.extend(models)
            
        # Deduplicate
        all_models = list(set(all_models))
        
        # Add to models tab, avoiding duplicates with what's already there
        existing = [p.strip() for p in self.mod_text.toPlainText().split('\n') if p.strip()]
        new_models = [m for m in all_models if m not in existing]
        
        if new_models:
            current_text = self.mod_text.toPlainText().strip()
            if current_text:
                current_text += "\n"
            current_text += "\n".join(new_models)
            self.mod_text.setText(current_text)
            self._log(f"Auto-extracted {len(new_models)} model(s) from inference metadata.", "#58a6ff")

    def _log(self, msg: str, color: str = "#8b949e"):
        self.log_area.append(f'<span style="color:{color}">{msg}</span>')

    def _run_packaging(self):
        userpath = self.userpath_edit.text().strip()
        if not userpath:
            QMessageBox.warning(self, "Missing Path", "Please provide a Target Package Directory.")
            return
            
        mls_paths = self.mls_text.toPlainText().split('\n')
        inf_paths = self.inf_text.toPlainText().split('\n')
        mod_paths = self.mod_text.toPlainText().split('\n')
        
        is_empty = not any(p.strip() for p in mls_paths + inf_paths + mod_paths)
        if is_empty:
            QMessageBox.warning(self, "Empty", "Please provide at least one path in the MLS, Inference, or Models tab.")
            return

        self.package_btn.setEnabled(False)
        self.log_area.clear()
        
        dry_run = self.dry_run_cb.isChecked()
        
        self.worker = PackagerThread(
            user_path=userpath,
            mls_paths=mls_paths,
            inf_paths=inf_paths,
            model_paths=mod_paths,
            dry_run=dry_run
        )
        self.worker.log_signal.connect(self._log)
        self.worker.finished_signal.connect(self._on_packaging_done)
        self.worker.start()

    def _on_packaging_done(self, success: bool):
        self.package_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Done", "Packaging completed successfully!")
