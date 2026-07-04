import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RU_PATH = ROOT / "ui" / "src" / "i18n" / "ru.json"
EN_PATH = ROOT / "ui" / "src" / "i18n" / "en.json"


def _flatten_keys(payload: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten_keys(value, path)
        else:
            keys.add(path)
    return keys


def test_i18n_ru_en_key_parity() -> None:
    ru_keys = _flatten_keys(json.loads(RU_PATH.read_text(encoding="utf-8")))
    en_keys = _flatten_keys(json.loads(EN_PATH.read_text(encoding="utf-8")))
    missing_in_en = sorted(ru_keys - en_keys)
    missing_in_ru = sorted(en_keys - ru_keys)
    assert not missing_in_en, f"keys missing in en.json: {missing_in_en[:10]}"
    assert not missing_in_ru, f"keys missing in ru.json: {missing_in_ru[:10]}"
