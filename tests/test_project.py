"""Tests for project files: translations, brand icons, manifest (spec.md 9)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from custom_components import solax_adapter_box_g2
from custom_components.solax_adapter_box_g2.const import DOMAIN

INTEGRATION = Path(solax_adapter_box_g2.__file__).parent


def _keys(tree: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        keys |= _keys(value, path) if isinstance(value, dict) else {path}
    return keys


def _translation(language: str) -> dict[str, Any]:
    return json.loads((INTEGRATION / "translations" / f"{language}.json").read_text("utf-8"))


def test_translations_have_the_same_keys() -> None:
    """German and English translations cover exactly the same texts."""
    assert _keys(_translation("de")) == _keys(_translation("en"))


def test_every_flow_error_is_translated() -> None:
    """Every error key of the config flow has a text (spec.md 4a)."""
    errors = _translation("en")["config"]["error"]
    assert set(errors) == {"cannot_connect", "invalid_response", "unknown"}


def test_brand_icons() -> None:
    """The brand icons have the sizes HACS and Home Assistant expect."""
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        with Image.open(INTEGRATION / "brand" / name) as image:
            assert image.size == (size, size)


def test_manifest() -> None:
    """The manifest names the domain, a config flow and a version."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text("utf-8"))
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.0.1"


def test_config_schema_is_config_entry_only() -> None:
    """YAML configuration is rejected in favour of the UI (hassfest)."""
    assert hasattr(solax_adapter_box_g2, "CONFIG_SCHEMA")
