from pathlib import Path
import yaml

def load_config(path: str | Path = "src/config.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    return yaml.safe_load(p.read_text())
