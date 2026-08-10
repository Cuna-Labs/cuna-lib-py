# @generated {"contract_id":"runa-sdk-contract","generator_path":"tools/runa-contract-generator.mjs","generator_sha256":"879fbef4d654c1f7769e1724c065133d6744bbda6b913d5bd3cd5b8104ce31e4","generator_version":"0.2.0","projection_path":"runa-sdk.projection.json","projection_sha256":"2721f5b7de5a033e5cc34dc6efb53ddf74e6110cd71168c0075bdb5679063791","projection_version":"1.7.0","snapshot_path":"runa-sdk-contract.snapshot.json","snapshot_sha256":"3e2af6adcd6a6348c78e703b756d1a8a95c4baf17700dd919f6dd4f7a5112f86","snapshot_version":"1.7.0"}
import json as _json
from .wire_types import GeneratedWireValue

def serialize_generated_request(value: GeneratedWireValue) -> str:
    return _json.dumps(value, ensure_ascii=False, separators=(",", ":"))
