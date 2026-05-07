import ast
import sys
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "blender_manifest.toml"


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_manifest():
    if not MANIFEST.exists():
        fail("Missing blender_manifest.toml")

    with MANIFEST.open("rb") as handle:
        return tomllib.load(handle)


def validate_manifest(manifest):
    required = ["schema_version", "id", "version", "name", "tagline", "type", "blender_version_min"]
    for key in required:
        if not manifest.get(key):
            fail(f"Manifest is missing required key: {key}")

    if len(manifest["tagline"]) > 64:
        fail("Manifest tagline must be 64 characters or shorter")

    build_paths = manifest.get("build", {}).get("paths", [])
    if not build_paths:
        fail("Manifest build.paths must list package files")

    if "blender_manifest.toml" in build_paths:
        fail("build.paths must not include blender_manifest.toml")

    for relative_path in build_paths:
        path = ROOT / relative_path
        if not path.exists():
            fail(f"build.paths references a missing file: {relative_path}")


def validate_python():
    addon_path = ROOT / "__init__.py"
    source = addon_path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(addon_path))


def validate_zip_layout(manifest):
    build_paths = ["blender_manifest.toml", *manifest.get("build", {}).get("paths", [])]
    missing = [path for path in build_paths if not (ROOT / path).exists()]
    if missing:
        fail(f"Cannot package missing files: {', '.join(missing)}")


def main():
    manifest = load_manifest()
    validate_manifest(manifest)
    validate_python()
    validate_zip_layout(manifest)
    print("Package source validation passed")


if __name__ == "__main__":
    main()
