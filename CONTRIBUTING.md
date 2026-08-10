# Contributing

## Branches

- `main` is released, deployable truth.
- `develop/sdk-foundation` is integration. Feature branches merge there before release.

## Ground rules

- Use English in code, comments, documentation, and commit messages.
- The SDK talks only to the Cuna endpoint (`https://api.getcuna.com` by default).
  It must never reach a non-Cuna provider directly or print an API key.
- Every behavior must trace to its accepted product requirement and canonical contract.
- Run formatting, lint, strict typing, tests, package checks, and security gates before review.
- Do not manually edit generated contract files.

## Canonical contract

Clone with submodules, or initialize an existing checkout before running any SDK gate:

```console
git submodule update --init --recursive
```

The `contracts` gitlink is the only contract source. It is pinned to the approved canonical
contract commit; do not copy contract documents into this repository or read a sibling SDK or
infrastructure tree. Contract binding generation requires Node.js 24 and must use only the
canonical generator, with an empty output directory:

```console
node contracts/tools/runa-contract-generator.mjs --language python --output src/runa/_internal/contract/generated
python tools/contract_gate.py
```

Commit the gitlink and the byte-exact generated output together. The gate verifies the pinned
commit, approved provenance, snapshot digest, generator identity, reproducibility, and canonical
attestation before the SDK test suite runs.
