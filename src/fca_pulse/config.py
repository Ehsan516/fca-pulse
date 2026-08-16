from pathlib import Path

import yaml

# src/fca_pulse/config.py -> src/fca_pulse -> src -> repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"


def load_feeds() -> dict:
    with open(CONFIG_DIR / "feeds.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_vocab() -> dict:
    with open(CONFIG_DIR / "vocab.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt_template(name):
    path = CONFIG_DIR / "prompts" / name
    return path.read_text(encoding="utf-8")
