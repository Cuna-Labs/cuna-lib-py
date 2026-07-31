from __future__ import annotations

import shutil
from pathlib import Path

from tools.duplicate_abstraction_gate import evaluate


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    for name in ("src", "tools", "tests", ".runa"):
        source = Path(name)
        destination = root / name
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".ruff_cache",
                ),
            )
    return root


def test_duplicate_abstraction_gate_accepts_current_governed_owners() -> None:
    report = evaluate(Path("."))
    assert report["verdict"] == "pass", report
    assert report["conceptCount"] == 5


def test_duplicate_abstraction_gate_rejects_semantic_owner_mutations(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)

    duplicate_uuid = root / "src/runa/duplicate_uuid.py"
    duplicate_uuid.write_text(
        'PATTERN = r"^[0-9a-f]{8}-duplicate$"\n',
        encoding="utf-8",
    )
    report = evaluate(root)
    assert report["verdict"] == "fail"
    assert any(
        finding["category"] == "uuid_owner_drift"
        for finding in report["findings"]  # type: ignore[union-attr]
    )

    duplicate_uuid.unlink()
    duplicate_security = root / "src/runa/duplicate_security.py"
    duplicate_security.write_text(
        "def contains_denied(value: object) -> bool:\n    return False\n",
        encoding="utf-8",
    )
    report = evaluate(root)
    assert any(
        finding["category"] == "security_owner_drift:contains_denied"
        for finding in report["findings"]  # type: ignore[union-attr]
    )

    duplicate_security.unlink()
    duplicate_hash = root / "tools/duplicate_hash.py"
    duplicate_hash.write_text(
        "import hashlib\n\ndef digest(value: bytes) -> str:\n"
        "    return hashlib.sha256(value).hexdigest()\n",
        encoding="utf-8",
    )
    report = evaluate(root)
    assert any(
        finding["category"] == "file_hash_owner_drift"
        for finding in report["findings"]  # type: ignore[union-attr]
    )


def test_duplicate_abstraction_gate_rejects_missing_parity_or_interface_oracles(
    tmp_path: Path,
) -> None:
    root = _fixture(tmp_path)
    parity = root / "tests/test_public_models_errors_config.py"
    parity.write_text(
        parity.read_text(encoding="utf-8").replace(
            "test_sync_async_public_parameter_parity",
            "removed_sync_async_public_parameter_parity",
        ),
        encoding="utf-8",
    )
    transport = root / "src/runa/_internal/transport.py"
    transport.write_text(
        transport.read_text(encoding="utf-8").replace(
            "class AsyncHttpTransport",
            "class RemovedAsyncHttpTransport",
        ),
        encoding="utf-8",
    )
    categories = {
        finding["category"]
        for finding in evaluate(root)["findings"]  # type: ignore[union-attr]
    }
    assert "sync_async_parity_oracle_missing" in categories
    assert "transport_interface_incomplete" in categories
