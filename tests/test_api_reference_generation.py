from __future__ import annotations

from pathlib import Path

import pytest

from tools.generate_api_reference import (
    ERROR_MANIFEST,
    ROOT_MANIFEST,
    SECTIONS,
    _branded_literal,
    _doc_raises,
    _examples,
    _validate_links,
    validate_claim_test_ids,
)


@pytest.mark.hermetic
def test_reference_inventory_is_exact_and_private_free() -> None:
    pages = tuple(name for names in SECTIONS.values() for name in names)
    assert len(pages) == 86
    assert set(pages) == set(ROOT_MANIFEST) | set(ERROR_MANIFEST)
    assert not any(name.startswith("_") for name in pages)


@pytest.mark.hermetic
def test_branded_signature_expectation_names_every_accepted_spelling() -> None:
    """The literal oracle under the reference gate's derived expectation.

    `_branded_literal` projects `WIRE_BRANDS`, so by itself it would agree with a
    narrowed brand list exactly as readily as with the correct one -- a
    parametrized check over the same tuple cannot fail. This is the fixed point
    that does not move with the source: dropping a spelling from the authority
    fails here, and so does reordering it, which would otherwise reverse the
    expectation and the assertion together.

    A brand *appended* to `WIRE_BRANDS` also fails here, deliberately and in the
    same way `test_documentation_states_the_environment_precedence_it_implements`
    does: the reference pages are regenerated from these annotations, so a third
    spelling is not accepted until someone states it.
    """

    assert _branded_literal("agent-auth.v1") == (
        "Literal['cuna.agent-auth.v1', 'runa.agent-auth.v1']"
    )
    assert _branded_literal("terminal.v1") == "Literal['cuna.terminal.v1', 'runa.terminal.v1']"


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
