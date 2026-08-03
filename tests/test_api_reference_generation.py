from __future__ import annotations

from pathlib import Path

import pytest

from tools.generate_api_reference import (
    ERROR_MANIFEST,
    ROOT_MANIFEST,
    SECTIONS,
    _doc_raises,
    _examples,
    _validate_links,
    validate_claim_test_ids,
)


@pytest.mark.hermetic
def test_reference_inventory_is_exact_and_private_free() -> None:
    pages = tuple(name for names in SECTIONS.values() for name in names)
    assert len(pages) == 29
    assert set(pages) == set(ROOT_MANIFEST) | set(ERROR_MANIFEST)
    assert not any(name.startswith("_") for name in pages)


@pytest.mark.hermetic
def test_claim_registry_rejects_invented_prd_test_id() -> None:
    valid = [{"claims": [{"claimId": "REF-A", "testIds": ["TC-091-09"]}]}]
    validate_claim_test_ids(valid)
    mutant = [{"claims": [{"claimId": "REF-A", "testIds": ["TC-091-12"]}]}]
    with pytest.raises(ValueError, match="unknown-prd-test-id"):
        validate_claim_test_ids(mutant)


@pytest.mark.hermetic
def test_raises_parser_exposes_missing_and_extra_error_mutants() -> None:
    complete = """Summary.

Raises:
    ConfigError: Invalid input.
    ApiError: Failed request.
"""
    assert _doc_raises(complete) == ("ConfigError", "ApiError")
    assert _doc_raises(complete.replace("    ApiError: Failed request.\n", "")) != (
        "ConfigError",
        "ApiError",
    )
    assert _doc_raises(complete + "    CommandError: Unexpected.\n") != (
        "ConfigError",
        "ApiError",
    )


@pytest.mark.hermetic
def test_examples_reject_capability_use_and_unassigned_open(tmp_path: Path) -> None:
    capability = tmp_path / "capability.py"
    capability.write_text("def bad(value):\n    return value.url\n", encoding="utf-8")
    with pytest.raises(ValueError, match="capability-url-used"):
        _examples(capability)
    unassigned = tmp_path / "unassigned.py"
    unassigned.write_text("def bad(session):\n    session.open()\n", encoding="utf-8")
    with pytest.raises(ValueError, match="open-result-not-assigned"):
        _examples(unassigned)


@pytest.mark.hermetic
def test_reference_link_validator_rejects_broken_link(tmp_path: Path) -> None:
    page = tmp_path / "page.md"
    page.write_text("[missing](missing.md)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken-link"):
        _validate_links(tmp_path)
