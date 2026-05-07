# Sculpt Timelapse Capture

Sculpt Timelapse Capture is a Blender 5.1+ add-on for recording long sculpting sessions as portable frame sessions.

## Workflow

The add-on captures frames only. Video encoding is handled later with the included PowerShell script so sessions can be moved, archived, and encoded outside Blender.

Each capture creates a folder like:

```text
timelapse_sessions/
  Face_Sculpt/
    2026-05-06_203000_blockout/
      frame_000001.jpg
      frame_000002.jpg
      session.json
      encode_timelapse.ps1
```

## Blender Usage

1. Install the extension zip in Blender with `Edit > Preferences > Add-ons > Install from Disk`.
2. Enable **Sculpt Timelapse Capture**.
3. Optional: set global defaults in the add-on preferences.
4. Open the 3D View sidebar with `N`.
5. Use the **Timelapse** tab to set the project, session name, root folder, interval, and image format.
6. Click **Start Capture** before sculpting and **Stop Capture** when finished.

JPEG is the default because it keeps 4-12 hour sessions manageable on disk. PNG is available when you need lossless source frames.

## Encoding

If **Copy Encoder Script to Sessions** is enabled in add-on preferences, each session folder contains `encode_timelapse.ps1`.

From PowerShell inside a session folder:

```powershell
.\encode_timelapse.ps1
```

Or from the add-on folder:

```powershell
.\encode_timelapse.ps1 -SessionDir "D:\path\to\session"
```

The script reads `session.json` to detect JPG/PNG and recommended FPS. Optional overrides:

- `-Fps 24`
- `-Format png`
- `-Output "D:\Videos\face_sculpt.mp4"`
- `-FfmpegPath "C:\ffmpeg\bin\ffmpeg.exe"`
- `-NoOverwrite`

## Development

Validate the source package:

```powershell
python scripts\validate_package.py
```

Build with Blender's official extension tooling:

```powershell
.\scripts\build_extension.ps1 -BlenderExe "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
```

GitHub Actions runs source validation and creates a source zip on pushes and pull requests. Release zips should be built locally with Blender's extension command, then attached to a GitHub release.
