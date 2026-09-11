import json
import os
from pathlib import Path

def get_inference_models(inference_path: str) -> list[str]:
    """
    Looks for metadata.json in the inference_path or its parent directory.
    Parses it to find models used in the inference.
    Returns a list of physical model directory paths.
    """
    p = Path(inference_path)
    if p.is_file():
        p = p.parent
        
    # Check current and parent directories for metadata.json
    meta_paths = [
        p / "metadata.json",
        p.parent / "metadata.json",
        p.parent.parent / "metadata.json"
    ]
    
    meta_file = None
    for mp in meta_paths:
        if mp.exists():
            meta_file = mp
            break
            
    if not meta_file:
        return []
        
    models_found = []
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Standard metaswap/inference metadata format usually contains "models" 
        # or specific keys inside "jobs" or "nodes".
        # We will parse aggressively to find anything that looks like a model path.
        
        def _find_models_in_dict(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if k.lower() in ("model", "model_path", "modelpath", "active_model", "model_dir"):
                        if isinstance(v, str) and "metaswap" in v:
                            models_found.append(v)
                    elif isinstance(v, (dict, list)):
                        _find_models_in_dict(v)
            elif isinstance(d, list):
                for item in d:
                    _find_models_in_dict(item)

        _find_models_in_dict(data)
        
        # Deduplicate
        return list(set(models_found))
    except Exception as e:
        print(f"Failed to parse {meta_file}: {e}")
        return []

def get_inference_name(inference_path: str) -> str:
    """
    Attempts to extract the inference job name from the path.
    Example: .../inference/074_rdw_1260_eng_vishwamitra_srcosrc_v001/exr/...
    """
    p = Path(inference_path)
    if p.name == "exr":
        return p.parent.name
    if p.parent.name == "exr":
        return p.parent.parent.name
    return p.name
