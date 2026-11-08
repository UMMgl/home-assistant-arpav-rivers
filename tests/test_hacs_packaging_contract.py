from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_DIR = ROOT / "custom_components"
DOMAIN = "arpav_rivers"
DISPLAY_NAME = "HA ARPAV River Level"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_https_url(value: str) -> None:
    parsed = urlparse(value)
    assert parsed.scheme == "https"
    assert parsed.netloc


def test_hacs_repository_manifest_is_present_and_minimal() -> None:
    hacs = _load_json(ROOT / "hacs.json")
    assert hacs["name"] == DISPLAY_NAME
    assert hacs["country"] == "IT"
    assert isinstance(hacs.get("homeassistant"), str)


def test_repository_contains_one_custom_integration() -> None:
    integrations = sorted(
        path.name
        for path in INTEGRATIONS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    )
    assert integrations == [DOMAIN]


def test_integration_manifest_contains_required_metadata() -> None:
    manifest = _load_json(INTEGRATIONS_DIR / DOMAIN / "manifest.json")
    required = {
        "domain",
        "documentation",
        "issue_tracker",
        "codeowners",
        "name",
        "version",
    }
    assert required <= manifest.keys()
    assert manifest["domain"] == DOMAIN
    assert manifest["name"] == DISPLAY_NAME
    assert manifest["codeowners"]
    _assert_https_url(manifest["documentation"])
    _assert_https_url(manifest["issue_tracker"])


def test_runtime_files_stay_inside_integration_directory() -> None:
    integration = INTEGRATIONS_DIR / DOMAIN
    for name in (
        "__init__.py",
        "client.py",
        "config_flow.py",
        "coordinator.py",
        "health.py",
        "manifest.json",
        "observations.py",
        "runtime_const.py",
        "sensor.py",
        "types.py",
    ):
        assert (integration / name).is_file(), name


def test_local_brand_icon_is_valid_png() -> None:
    icon = INTEGRATIONS_DIR / DOMAIN / "brand" / "icon.png"
    assert icon.is_file()
    assert icon.stat().st_size > len(PNG_SIGNATURE)
    with icon.open("rb") as handle:
        assert handle.read(len(PNG_SIGNATURE)) == PNG_SIGNATURE


def test_public_artifact_has_no_obvious_secret_files() -> None:
    forbidden_names = {
        ".env",
        "secrets.yaml",
        "credentials.json",
        "service-account.json",
    }
    matches = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.name.lower() in forbidden_names
    ]
    assert matches == []
