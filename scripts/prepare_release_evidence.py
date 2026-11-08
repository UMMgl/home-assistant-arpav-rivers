"""Build private candidate evidence or verify a public candidate without publishing."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, **kwargs: object) -> None:
    subprocess.run(list(args), check=True, **kwargs)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_bom(bom: dict[str, object]) -> None:
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.7":
        raise ValueError("Release SBOM must explicitly declare CycloneDX 1.7")
    error = JsonStrictValidator(SchemaVersion.V1_7).validate_str(json.dumps(bom))
    if error:
        raise ValueError(f"Invalid CycloneDX 1.7 SBOM: {error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library-dir", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run("git", "diff-index", "--quiet", "HEAD", "--", cwd=ROOT)
    candidate = ROOT
    if args.library_dir:
        candidate = output / "candidate"
        run(sys.executable, str(ROOT / "scripts/export_public_release.py"),
            "--destination", str(candidate), "--source-sha", sha)
    manifest = json.loads((candidate / "custom_components/arpav_rivers/manifest.json").read_text())
    requirement = "veneto-hydro-client==0.1.0"
    if manifest.get("requirements") != [requirement]:
        raise ValueError("Candidate must declare the exact transport dependency")
    run(sys.executable, str(candidate / "scripts/check_public_hygiene.py"), str(candidate))

    with tempfile.TemporaryDirectory(prefix="arpav-release-") as temporary:
        scratch = Path(temporary)
        runtime = scratch / "runtime"
        run(sys.executable, "-m", "venv", str(runtime))
        python = runtime / "bin/python"
        lib = args.library_dir.resolve() if args.library_dir else None
        if lib:
            provenance = json.loads((lib / "UPSTREAM_PROVENANCE.json").read_text())
            for relative, expected in provenance["files"].items():
                if digest(lib / relative) != expected:
                    raise ValueError(f"Transport snapshot differs from upstream: {relative}")
            (output / "transport-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
            dist = output / "library-dist"
            run(sys.executable, "-m", "build", str(lib), "--outdir", str(dist))
            wheel, = dist.glob("*.whl")
            sdist, = dist.glob("*.tar.gz")
            unpacked = scratch / "built"
            unpacked.mkdir()
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(unpacked / "wheel")
                metadata_name, = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
                if "License-Expression: Apache-2.0" not in archive.read(metadata_name).decode():
                    raise ValueError("Wheel license metadata must be Apache-2.0")
            with tarfile.open(sdist) as archive:
                archive.extractall(unpacked / "sdist", filter="data")
            run(sys.executable, str(candidate / "scripts/check_public_hygiene.py"), str(unpacked))
            run(str(python), "-m", "pip", "install", str(wheel))
        else:
            dist = output / "library-dist"
            run(str(python), "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
                "--dest", str(dist), requirement)
            wheel, = dist.glob("*.whl")
            run(str(python), "-m", "pip", "install", str(wheel))
        freeze = subprocess.check_output([str(python), "-m", "pip", "freeze"], text=True)
        # Freeze may contain a temporary wheel file URL; record a stable distribution pin.
        freeze = "\n".join(requirement if line.lower().startswith("veneto-hydro-client @") else line
                           for line in freeze.splitlines()) + "\n"
        (output / "runtime-requirements.txt").write_text(freeze)
        audit_requirements = freeze
        if lib:
            # Unpublished first-party code is covered by source tests/static analysis.
            # All installed third-party runtime versions remain strictly audited.
            audit_requirements = "\n".join(line for line in freeze.splitlines()
                                           if not line.startswith("veneto-hydro-client==")) + "\n"
        audit_input = output / "dependency-audit-input.txt"
        audit_input.write_text(audit_requirements)
        run(sys.executable, "-m", "pip_audit", "-r", str(audit_input), "--no-deps", "--disable-pip",
            "--strict", "--format=json", "--output", str(output / "dependency-audit.json"))
        library_bom = output / "veneto-hydro-client.cdx.json"
        run(sys.executable, "-m", "cyclonedx_py", "environment", str(python), "--sv", "1.7",
            "--output-reproducible", "--validate", "-o", str(library_bom))
        bom = json.loads(library_bom.read_text())
        # The venv bootstrap installer is not a dependency shipped by these artifacts.
        installer_refs = {item["bom-ref"] for item in bom["components"] if item["name"] == "pip"}
        bom["components"] = [item for item in bom["components"] if item["bom-ref"] not in installer_refs]
        bom["dependencies"] = [item for item in bom["dependencies"] if item["ref"] not in installer_refs]
        for dependency in bom["dependencies"]:
            dependency["dependsOn"] = [ref for ref in dependency.get("dependsOn", []) if ref not in installer_refs]
        components = bom["components"]
        names = {item["name"].lower().replace("_", "-") for item in components}
        if not {"veneto-hydro-client", "aiohttp", "defusedxml"} <= names:
            raise ValueError("SBOM is missing runtime dependencies")
        source_property = {"name": "arpav:validated-source-sha", "value": sha}
        library_ref, = [item["bom-ref"] for item in components if item["name"] == "veneto-hydro-client"]
        library_component, = [item for item in components if item["bom-ref"] == library_ref]
        bom["components"] = [item for item in components if item["bom-ref"] != library_ref]
        bom["metadata"]["component"] = dict(library_component)
        bom["metadata"]["component"]["properties"] = [source_property]
        bom["metadata"]["component"]["licenses"] = [{"license": {"id": "Apache-2.0"}}]
        validate_bom(bom)
        library_bom.write_text(json.dumps(bom, indent=2) + "\n")
        bom["metadata"]["component"] = {
            "type": "application", "name": "HA ARPAV River Level", "version": manifest["version"],
            "bom-ref": "arpav_rivers", "properties": [source_property],
            "licenses": [{"license": {"id": "Apache-2.0"}}],
        }
        bom["components"] = components
        bom["dependencies"].append({"ref": "arpav_rivers", "dependsOn": [library_ref]})
        validate_bom(bom)
        (output / "arpav-rivers.cdx.json").write_text(json.dumps(bom, indent=2) + "\n")

    archive_path = output / "arpav-rivers.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        integration = candidate / "custom_components/arpav_rivers"
        for path in sorted(integration.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                if path.is_symlink():
                    raise ValueError(f"Symlink not permitted in HACS artifact: {path}")
                archive.write(path, path.relative_to(candidate))
        for name in ("LICENSE", "NOTICE", "SAFETY.md"):
            archive.write(candidate / name, name)
    for name, artifact in [("arpav-rivers.cdx.json", archive_path)]:
        path = output / name
        bom = json.loads(path.read_text())
        bom["metadata"]["component"]["hashes"] = [{"alg": "SHA-256", "content": digest(artifact)}]
        validate_bom(bom)
        path.write_text(json.dumps(bom, indent=2) + "\n")
    path = output / "veneto-hydro-client.cdx.json"
    bom = json.loads(path.read_text())
    bom["metadata"]["component"]["hashes"] = [{"alg": "SHA-256", "content": digest(wheel)}]
    validate_bom(bom)
    path.write_text(json.dumps(bom, indent=2) + "\n")
    # Include a hash for every exported file, every built artifact and every report.
    files = {str(path.relative_to(output)): digest(path) for path in sorted(output.rglob("*")) if path.is_file()}
    (output / "evidence.json").write_text(json.dumps({
        "schema": "arpav-release-evidence-v1", "validated_source_sha": sha,
        "scope": "private-preparation" if args.library_dir else "public-candidate",
        "dependency_audit_scope": "third-party runtime; first-party source tests/static analysis" if args.library_dir
                                  else "published runtime distributions",
        "files": files,
        "remaining_gates": ["Public identity and protections", "PyPI publisher and library release",
                            "HACS/hassfest and install/upgrade/rollback on public exact SHA",
                            "Explicit release approval"],
    }, indent=2, sort_keys=True) + "\n")
    print(f"Release evidence ready: {sha}; no publication performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
