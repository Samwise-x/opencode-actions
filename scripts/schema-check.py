#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def type_ok(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    raise ContractError(f"unsupported schema type: {expected}")


def validate(schema: dict[str, Any], value: Any, path: str = "$") -> None:
    if "oneOf" in schema:
        matches = 0
        errors: list[str] = []
        for branch in schema["oneOf"]:
            try:
                validate(branch, value, path)
                matches += 1
            except ContractError as exc:
                errors.append(str(exc))
        if matches != 1:
            raise ContractError(
                f"{path}: expected exactly one oneOf branch, matched {matches}; "
                + "; ".join(errors)
            )
        return

    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{path}: expected constant {schema['const']!r}, got {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{path}: {value!r} is not in enum {schema['enum']!r}")

    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(type_ok(value, item) for item in allowed):
            raise ContractError(f"{path}: expected type {allowed!r}, got {type(value).__name__}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ContractError(f"{path}: missing required property {key!r}")

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        if additional is False:
            unknown = sorted(set(value) - set(properties))
            if unknown:
                raise ContractError(f"{path}: unknown properties: {', '.join(unknown)}")

        for key, item in value.items():
            child = properties.get(key)
            if child is not None:
                validate(child, item, f"{path}.{key}")

    if isinstance(value, list):
        if schema.get("uniqueItems"):
            seen: set[str] = set()
            for index, item in enumerate(value):
                marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if marker in seen:
                    raise ContractError(f"{path}[{index}]: duplicate item")
                seen.add(marker)
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate(item_schema, item, f"{path}[{index}]")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if minimum is not None and len(value) < int(minimum):
            raise ContractError(f"{path}: string shorter than minLength={minimum}")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            raise ContractError(f"{path}: string does not match pattern {pattern!r}")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractError(f"{path}: invalid date-time {value!r}") from exc

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise ContractError(f"{path}: {value} is below minimum {minimum}")


def validate_files(schema_path: Path, document_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    document = json.loads(document_path.read_text(encoding="utf-8"))
    validate(schema, document)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a JSON document against the repository's supported schema subset.")
    parser.add_argument("schema")
    parser.add_argument("document")
    args = parser.parse_args()
    try:
        validate_files(Path(args.schema), Path(args.document))
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"contract validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
