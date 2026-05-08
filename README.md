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

1. Download the release zip from GitHub Releases.
2. Install the extension zip in Blender with `Edit > Preferences > Add-ons > Install from Disk`.
3. Enable **Sculpt Timelapse Capture**.
4. Optional: set global defaults in the add-on preferences.
5. Open the 3D View sidebar with `N`.
6. Use the **Timelapse** tab to set the project, session name, root folder, interval, and image format.
7. Click **Start Capture** before sculpting and **Stop Capture** when finished.

Use the release asset named like `sculpt_timelapse_capture-0.4.2.zip`. Do not use GitHub's green **Code > Download ZIP** button for installation; that downloads the source repository, not the packaged Blender extension.

Project and Session are prefilled with contextual defaults. Project uses the current `.blend` file name when available, and Session defaults to `sculpt_session`.

Image Quality has three presets:

- `JPG 80%` for smaller long-session captures
- `JPG 90%` for balanced default captures
- `PNG` for lossless frames

Capture Source controls what gets saved:

- `Active View` captures the current 3D View.
- `Scene Camera` captures from the camera selected in the Sculpt Timelapse panel.

When Scene Camera is selected, the Camera picker defaults to Blender's active scene camera when possible. The selected camera is checked on every frame, so it can be changed mid-session.

Pause While Idle is enabled by default. If Blender receives no input for 30 seconds, capture pauses and resumes after new input.

## Root Folder

The **Root Folder** setting is the top-level library where the add-on creates project and session folders. Frames are not saved directly into the root folder.

For example, if Root Folder is:

```text
D:\Blender Timelapses
```

and Project is `Face Sculpt` with Session `blockout`, the add-on creates:

```text
D:\Blender Timelapses\
  Face_Sculpt\
    2026-05-06_203000_blockout\
      frame_000001.jpg
      frame_000002.jpg
      session.json
      encode_timelapse.ps1
```

Use one shared Root Folder if you want all timelapses organized in one place across multiple `.blend` files and projects. Use a project-specific Root Folder if you want captures stored beside a particular project.

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

By default, the encoded video is saved as `timelapse.mp4` in the same session folder as the captured frames:

```text
timelapse_sessions/
  Face_Sculpt/
    2026-05-06_203000_blockout/
      frame_000001.jpg
      session.json
      timelapse.mp4
```

Use `-Output` to save the video somewhere else.

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
