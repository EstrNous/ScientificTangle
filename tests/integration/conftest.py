import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = ROOT / "services" / "knowledge"
for path in (ROOT, KNOWLEDGE_ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
