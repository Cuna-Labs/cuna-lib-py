# @generated {"contract_id":"runa-sdk-contract","generator_path":"tools/runa-contract-generator.mjs","generator_sha256":"879fbef4d654c1f7769e1724c065133d6744bbda6b913d5bd3cd5b8104ce31e4","generator_version":"0.2.0","projection_path":"runa-sdk.projection.json","projection_sha256":"693dec9fd0d00fb541b4238e47d8f6bbd5211e4f18dcd133ae60b58462b44089","projection_version":"1.7.0","snapshot_path":"runa-sdk-contract.snapshot.json","snapshot_sha256":"6dec7457e26b733b2a29b63b4effa39ec362957e227e67fba16fff17ed1c785c","snapshot_version":"1.7.0"}
import json as _json
from .wire_types import GeneratedWireValue

def deserialize_generated_response(text: str) -> GeneratedWireValue:
    return _json.loads(text)
