# @generated {"contract_id":"runa-sdk-contract","generator_path":"tools/runa-contract-generator.mjs","generator_sha256":"879fbef4d654c1f7769e1724c065133d6744bbda6b913d5bd3cd5b8104ce31e4","generator_version":"0.2.0","projection_path":"runa-sdk.projection.json","projection_sha256":"8e832b0038285c410650b6ba1a5e1850db2c977660fe4bd537c9dbe6186ba7b4","projection_version":"1.7.0","snapshot_path":"runa-sdk-contract.snapshot.json","snapshot_sha256":"cb4bf23a37daf7a22a1ffd78a6a48c3dff69a7f0993a01a575557c005621fa57","snapshot_version":"1.7.0"}
import json as _json
from .wire_types import GeneratedWireValue

def deserialize_generated_response(text: str) -> GeneratedWireValue:
    return _json.loads(text)
