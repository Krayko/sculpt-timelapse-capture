import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "blender_manifest.toml"


def main():
    with MANIFEST.open("rb") as handle:
        manifest = tomllib.load(handle)

    package_name = f"{manifest['id']}-{manifest['version']}.zip"
    package_path = ROOT / package_name
    build_paths = ["blender_manifest.toml", *manifest["build"]["paths"]]

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in build_paths:
            archive.write(ROOT / relative_path, relative_path)

    print(f"Created {package_path}")


if __name__ == "__main__":
    main()
