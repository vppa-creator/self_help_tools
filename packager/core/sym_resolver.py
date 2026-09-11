import os
from pathlib import Path

def resolve_mls_symlink(path: str) -> str:
    """
    Resolves a symlink exactly 1 level deep using os.readlink.
    If it's not a symlink, returns the original path.
    """
    try:
        if os.path.islink(path):
            target = os.readlink(path)
            if not os.path.isabs(target):
                target = os.path.normpath(os.path.join(os.path.dirname(path), target))
            return target
        return path
    except OSError:
        return path

def extract_faces_dir(resolved_path: str) -> str | None:
    """
    Steps backward from the resolved path to find the directory 
    that actually contains the 'faces' dir or the ingest dir.
    Example: 
    Path: /.../face_cache/ingest__074_rdw_1330_eng_vishwamitra_aligned01/faces/e_...####.png
    Returns: /.../face_cache/ingest__074_rdw_1330_eng_vishwamitra_aligned01/faces
    """
    p = Path(resolved_path)
    
    # If the path points to a file, get its parent
    if p.is_file() or p.name.endswith(".png") or p.name.endswith(".exr"):
        p = p.parent
        
    # Traverse up to see if we are in 'faces'
    if p.name == "faces":
        return str(p)
        
    for parent in p.parents:
        if parent.name == "faces":
            return str(parent)
            
    # Fallback to whatever directory it is
    return str(p)
