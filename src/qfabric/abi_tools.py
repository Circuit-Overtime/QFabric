from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .abi import Effect, Frame, MessageType, Metadata, Schema, Status, encode_frame


def build_golden_vectors(schema_path: Path) -> dict[str, object]:
    raw_schema = schema_path.read_bytes()
    schema = Schema(json.loads(raw_schema))

    add_request = {"a": -(1 << 31), "b": (1 << 31) - 1}
    add_payload = schema.encode("AddRequest", add_request)
    add_frame = encode_frame(
        Frame(
            Metadata(
                message_type=MessageType.REQUEST,
                effect=Effect.PURE,
                status=Status.OK,
                task_id=schema.tasks["add"].task_id,
                invocation_id=0x0102030405060708,
                epoch=7,
                contract_id=11,
                relative_deadline_us=50_000,
            ),
            add_payload,
        )
    )

    probe_request = {
        "sequence": (1 << 64) - 1,
        "temperature": 12.5,
        "gain": -0.25,
        "offsets": [-(1 << 15), 0, (1 << 15) - 1],
        "enabled": True,
    }
    probe_payload = schema.encode("ProbeRequest", probe_request)
    probe_frame = encode_frame(
        Frame(
            Metadata(
                message_type=MessageType.REQUEST,
                effect=Effect.PURE,
                status=Status.OK,
                task_id=schema.tasks["abi_probe"].task_id,
                invocation_id=(1 << 64) - 1,
                epoch=(1 << 32) - 1,
            ),
            probe_payload,
        )
    )

    response = {"accepted": True, "checksum": 0x89ABCDEF}
    response_payload = schema.encode("ProbeResponse", response)
    response_frame = encode_frame(
        Frame(
            Metadata(
                message_type=MessageType.RESPONSE,
                effect=Effect.PURE,
                status=Status.OK,
                task_id=schema.tasks["abi_probe"].task_id,
                invocation_id=(1 << 64) - 1,
                epoch=(1 << 32) - 1,
            ),
            response_payload,
        )
    )

    return {
        "schema_version": 1,
        "protocol_version": 1,
        "schema_sha256": hashlib.sha256(raw_schema).hexdigest(),
        "vectors": [
            {
                "name": "add-request-integer-boundaries",
                "type": "AddRequest",
                "value": add_request,
                "payload_hex": add_payload.hex(),
                "frame_hex": add_frame.hex(),
            },
            {
                "name": "probe-request-composite",
                "type": "ProbeRequest",
                "value": probe_request,
                "payload_hex": probe_payload.hex(),
                "frame_hex": probe_frame.hex(),
            },
            {
                "name": "probe-response",
                "type": "ProbeResponse",
                "value": response,
                "payload_hex": response_payload.hex(),
                "frame_hex": response_frame.hex(),
            },
        ],
    }


def write_golden_vectors(vectors: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(vectors, indent=2, sort_keys=True) + "\n", encoding="utf-8")
