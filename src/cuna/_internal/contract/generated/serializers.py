# @generated {"contract_id":"runa-sdk-contract","generator_path":"tools/runa-contract-generator.mjs","generator_sha256":"879fbef4d654c1f7769e1724c065133d6744bbda6b913d5bd3cd5b8104ce31e4","generator_version":"0.2.0","projection_path":"runa-sdk.projection.json","projection_sha256":"145dc0f4ff47d3721d37f475c1c859e6797d1dd08c74736de414a80d69150cbe","projection_version":"1.7.0","snapshot_path":"runa-sdk-contract.snapshot.json","snapshot_sha256":"e7416b1e20843e0a96290428419e1e137d8189e30b7c82c62b011978516126bd","snapshot_version":"1.7.0"}
import json as _json
from .wire_types import GeneratedWireValue

def serialize_generated_request(value: GeneratedWireValue) -> str:
    return _json.dumps(value, ensure_ascii=False, separators=(",", ":"))
