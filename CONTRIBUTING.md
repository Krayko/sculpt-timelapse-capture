# Contributing

## Local Validation

Run the source checks:

```powershell
python scripts\validate_package.py
```

If Blender is installed, run the official extension validation and build:

```powershell
.\scripts\build_extension.ps1 -BlenderExe "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
```

## Release Checklist

1. Update `version` in `blender_manifest.toml`.
2. Run `python scripts\validate_package.py`.
3. Run `.\scripts\build_extension.ps1`.
4. Install the generated zip in Blender and test start/stop capture.
5. Attach the generated zip to the GitHub release.
