from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cloud_verify.sh"


def _bash_available() -> bool:
    bash = shutil.which("bash")
    if bash is None:
        return False
    probe = subprocess.run(
        [bash, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def test_cloud_verify_help_exits_zero() -> None:
    if not _bash_available():
        return
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Upload smoke" not in result.stdout
    assert "Usage:" in result.stdout


def test_cloud_verify_sets_pythonpath_and_upload_smoke() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'export PYTHONPATH="$ROOT_DIR"' in source
    assert "check_upload_smoke" in source
    assert 'fail "/api/documents/upload -> 405 Method Not Allowed"' in source


def test_cloud_verify_main_includes_upload_smoke() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    main_block = source.split("main() {", 1)[1]
    assert "check_upload_smoke" in main_block
    assert "check_documents_catalog_smoke" in main_block
    assert main_block.index("check_upload_smoke") < main_block.index("check_search_smoke")
