# @generated {"contract_id":"runa-sdk-contract","generator_path":"tools/runa-contract-generator.mjs","generator_sha256":"75de6242dde7fccfc9251d371020c5dc5ffb96a65399647b6d54d2c8850202e1","generator_version":"0.2.0","snapshot_path":"runa-sdk-contract.snapshot.json","snapshot_sha256":"f6ec19dbf8e96e3280da37f6f7b435163088b875c92d3ae2551e83902000a34a","snapshot_version":"1.4.0"}
import json as _json
from .wire_types import GeneratedWireValue

def deserialize_generated_response(text: str) -> GeneratedWireValue:
    return _json.loads(text)
