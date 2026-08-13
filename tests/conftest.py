import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456789")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import Config


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirige el archivo de persistencia a un directorio temporal."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(Config, "DATA_DIR", data_dir)
    monkeypatch.setattr(Config, "ARCHIVO_ESTADO", data_dir / "estados_persistentes.json")
    return data_dir
