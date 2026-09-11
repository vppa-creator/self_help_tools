import os
import shutil
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from .sym_resolver import resolve_mls_symlink, extract_faces_dir
from .metadata_parser import get_inference_name

class PackagerThread(QThread):
    progress_signal = Signal(int, int) # current, total
    log_signal = Signal(str, str) # message, color
    finished_signal = Signal(bool) # success

    def __init__(self, user_path: str, mls_paths: list[str], inf_paths: list[str], model_paths: list[str], dry_run: bool):
        super().__init__()
        self.user_path = Path(user_path)
        self.mls_paths = [p for p in mls_paths if p.strip()]
        self.inf_paths = [p for p in inf_paths if p.strip()]
        self.model_paths = [p for p in model_paths if p.strip()]
        self.dry_run = dry_run
        
        self.total_files = 0
        self.copied_files = 0
        self.summary_lines = []

    def run(self):
        try:
            self.log_signal.emit(f"=== Starting Package Run {'(DRY RUN)' if self.dry_run else ''} ===", "#58a6ff")
            if not self.dry_run:
                os.makedirs(self.user_path, exist_ok=True)
                
            self._process_mls()
            self._process_inferences()
            self._process_models()
            self._write_summary()
            
            self.log_signal.emit("=== Packaging Complete ===", "#3fb950")
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"Error during packaging: {e}", "#ff6b6b")
            self.finished_signal.emit(False)

    def _process_mls(self):
        if not self.mls_paths: return
        self.log_signal.emit("\n--- Processing MLS ---", "#d2a8ff")
        
        for path in self.mls_paths:
            self.log_signal.emit(f"Resolving: {path}", "#cccccc")
            resolved = resolve_mls_symlink(path)
            target_dir = extract_faces_dir(resolved)
            
            if not target_dir or not os.path.exists(target_dir):
                self.log_signal.emit(f"  ✗ Could not find valid physical path for {path}", "#ff6b6b")
                continue
                
            # e.g., target_dir = /.../ingest__074_rdw_1330_eng_vishwamitra_aligned01/faces
            target_path = Path(target_dir)
            parent_name = target_path.parent.name # ingest__074_rdw_1330_eng_vishwamitra_aligned01
            
            dest_dir = self.user_path / "MLS" / parent_name / "faces"
            self.log_signal.emit(f"  Source: {target_dir}", "#8b949e")
            self.log_signal.emit(f"  Dest:   {dest_dir}", "#8b949e")
            
            self.summary_lines.append(f"MLS Name: {parent_name}")
            
            files_to_copy = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
            
            if not self.dry_run:
                os.makedirs(dest_dir, exist_ok=True)
                
            for f in files_to_copy:
                src = os.path.join(target_dir, f)
                dst = os.path.join(dest_dir, f)
                if not self.dry_run:
                    shutil.copy2(src, dst)
                self.copied_files += 1

    def _process_inferences(self):
        if not self.inf_paths: return
        self.log_signal.emit("\n--- Processing Inferences ---", "#d2a8ff")
        
        for path in self.inf_paths:
            inf_name = get_inference_name(path)
            self.summary_lines.append(f"Inference Name: {inf_name}")
            
            p = Path(path)
            if p.is_file() or p.name.endswith(".exr"):
                src_dir = p.parent
            else:
                src_dir = p
                
            if not src_dir.exists():
                self.log_signal.emit(f"  ✗ Source dir does not exist: {src_dir}", "#ff6b6b")
                continue
                
            dest_dir = self.user_path / "Inferences" / inf_name
            self.log_signal.emit(f"  Source: {src_dir}", "#8b949e")
            self.log_signal.emit(f"  Dest:   {dest_dir}", "#8b949e")
            
            files_to_copy = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
            
            if not self.dry_run:
                os.makedirs(dest_dir, exist_ok=True)
                
            for f in files_to_copy:
                src = os.path.join(src_dir, f)
                dst = os.path.join(dest_dir, f)
                if not self.dry_run:
                    shutil.copy2(src, dst)
                self.copied_files += 1

    def _process_models(self):
        if not self.model_paths: return
        self.log_signal.emit("\n--- Processing Models ---", "#d2a8ff")
        
        for path in self.model_paths:
            p = Path(path)
            # path could be: .../mlc_dfw_vishwamitra_D01_1k_v2/v003/model
            # or .../mlc_dfw_vishwamitra_D01_1k_v2/v003
            if p.name == "model":
                model_dir = p
                v_dir = p.parent
            else:
                v_dir = p
                model_dir = p / "model"
                
            model_name = v_dir.parent.name
            version = v_dir.name
            self.summary_lines.append(f"Model Used: {model_name}/{version}")
            
            dest_v_dir = self.user_path / "Models" / model_name / version
            dest_model_dir = dest_v_dir / "model"
            
            self.log_signal.emit(f"  Targeting Model: {model_name}/{version}", "#8b949e")
            
            if not self.dry_run:
                os.makedirs(dest_model_dir, exist_ok=True)
                
            files_to_copy = [
                (v_dir / "config.yaml", dest_v_dir / "config.yaml"),
                (model_dir / "config.json", dest_model_dir / "config.json"),
                (model_dir / "history.json", dest_model_dir / "history.json"),
                (model_dir / "model.pt", dest_model_dir / "model.pt")
            ]
            
            for src, dst in files_to_copy:
                if src.exists():
                    self.log_signal.emit(f"    Copying {src.name}", "#8b949e")
                    if not self.dry_run:
                        shutil.copy2(str(src), str(dst))
                    self.copied_files += 1
                else:
                    self.log_signal.emit(f"    ✗ Missing: {src.name}", "#ff6b6b")

    def _write_summary(self):
        if self.dry_run or not self.summary_lines:
            return
            
        summary_path = self.user_path / "package_summary.txt"
        self.log_signal.emit(f"\n--- Writing Summary to {summary_path.name} ---", "#d2a8ff")
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=== PACKAGER SUMMARY ===\n\n")
            for line in self.summary_lines:
                f.write(line + "\n")
