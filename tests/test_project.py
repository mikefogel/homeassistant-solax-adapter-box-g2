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


def test_every_exception_is_translated() -> None:
    """Errors shown in the UI have a message in both languages (spec.md 8)."""
    for language in ("en", "de"):
        exceptions = _translation(language)["exceptions"]
        assert set(exceptions) == {"cannot_connect", "invalid_response"}, language


def test_raw_value_attributes_are_translated() -> None:
    """The int16 and bits attributes have translated names (spec.md 6a)."""
    for language in ("en", "de"):
        sensors = _translation(language)["entity"]["sensor"]
        for key in ("raw_data", "raw_info", "raw_set"):
            assert set(sensors[key]["state_attributes"]) == {"int16", "bits"}, (language, key)


def test_brand_icons() -> None:
    """The brand icons have the sizes HACS and Home Assistant expect (spec.md 9)."""
    for prefix in ("", "dark_"):
        for name, size in ((f"{prefix}icon.png", 256), (f"{prefix}icon@2x.png", 512)):
            with Image.open(INTEGRATION / "brand" / name) as image:
                assert image.size == (size, size), name


def test_brand_logos() -> None:
    """Logos are landscape with a height of 128 / 256 px, light and dark (spec.md 9)."""
    for prefix in ("", "dark_"):
        for name, height in ((f"{prefix}logo.png", 128), (f"{prefix}logo@2x.png", 256)):
            with Image.open(INTEGRATION / "brand" / name) as image:
                width, actual_height = image.size
                assert actual_height == height, name
                assert width > height, name
                assert image.mode == "RGBA", name


def test_manifest() -> None:
    """The manifest names the domain, a config flow and a version."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text("utf-8"))
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.2.0"


def test_config_schema_is_config_entry_only() -> None:
    """YAML configuration is rejected in favour of the UI (hassfest)."""
    assert hasattr(solax_adapter_box_g2, "CONFIG_SCHEMA")
