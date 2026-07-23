"""Minimal YAML subset loader for project.axon.yaml (no PyYAML dependency)."""

from __future__ import annotations

from typing import Any


class SimpleYamlError(ValueError):
    pass


def _parse_scalar(raw: str) -> Any:
    text = raw.strip()
    if text in {"", "~", "null", "Null", "NULL"}:
        return None
    if text in {"true", "True", "TRUE"}:
        return True
    if text in {"false", "False", "FALSE"}:
        return False
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def loads_simple_yaml(text: str) -> Any:
    """Parse a constrained YAML subset used by project.axon.yaml contracts."""
    lines: list[tuple[int, str]] = []
    for lineno, original in enumerate(text.splitlines(), start=1):
        if not original.strip() or original.lstrip().startswith("#"):
            continue
        indent = len(original) - len(original.lstrip(" "))
        if indent % 2 != 0:
            raise SimpleYamlError(f"indent must be multiples of 2 at line {lineno}")
        lines.append((indent // 2, original.strip()))

    def parse_block(index: int, level: int) -> tuple[Any, int]:
        if index >= len(lines):
            return None, index
        indent, content = lines[index]
        if indent != level:
            raise SimpleYamlError(f"unexpected indent at token {content!r}")

        if content.startswith("- "):
            items: list[Any] = []
            while index < len(lines) and lines[index][0] == level and lines[index][1].startswith("- "):
                item_raw = lines[index][1][2:].strip()
                index += 1
                if not item_raw:
                    child, index = parse_block(index, level + 1)
                    items.append(child)
                elif index < len(lines) and lines[index][0] > level and ":" in item_raw:
                    # inline key start of mapping list item
                    key, _, rest = item_raw.partition(":")
                    mapping: dict[str, Any] = {}
                    if rest.strip():
                        mapping[key.strip()] = _parse_scalar(rest)
                    child_map, index = parse_mapping_body(index, level + 1, mapping)
                    items.append(child_map)
                else:
                    items.append(_parse_scalar(item_raw))
            return items, index

        return parse_mapping_body(index, level, {})

    def parse_mapping_body(
        index: int,
        level: int,
        mapping: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        while index < len(lines) and lines[index][0] == level and not lines[index][1].startswith("- "):
            _, content = lines[index]
            if ":" not in content:
                raise SimpleYamlError(f"expected key: value at {content!r}")
            key, _, rest = content.partition(":")
            key = key.strip()
            rest = rest.strip()
            index += 1
            if rest:
                mapping[key] = _parse_scalar(rest)
                continue
            if index >= len(lines) or lines[index][0] <= level:
                mapping[key] = None
                continue
            child, index = parse_block(index, level + 1)
            mapping[key] = child
        return mapping, index

    if not lines:
        return {}
    value, next_index = parse_block(0, 0)
    if next_index != len(lines):
        raise SimpleYamlError("dangling content after root document")
    return value
