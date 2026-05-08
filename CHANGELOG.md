# Changelog

## 0.4.4

- Fixed live viewport capture restore errors caused by Blender camera offset array properties.

## 0.4.3

- Changed frame capture to use live 3D View screenshots instead of OpenGL scene renders.
- Scene Camera capture now temporarily switches the 3D View to the selected camera before capturing.

## 0.4.2

- Added a Sculpt Timelapse camera picker for Scene Camera capture.
- Scene Camera capture now uses the selected camera each frame, allowing mid-session camera changes.

## 0.4.1

- Fixed add-on enable errors caused by reading scene data during Blender's restricted registration context.

## 0.4.0

- Added idle-aware capture pause with a 30 second default threshold.
- Added capture source selection for active 3D View or scene camera.
- Prefilled project and session fields with contextual defaults.
- Replaced separate file format and JPEG quality controls with JPG 80%, JPG 90%, and PNG presets.

## 0.3.2

- Fixed stale operator references after Blender removes modal operator RNA data.

## 0.3.1

- Fixed Blender 5.1 modal timer compatibility when `Event.timer` is unavailable.

## 0.3.0

- Added project/session folder organization.
- Added `session.json` metadata for portable captures.
- Moved video encoding out of Blender.
- Updated `encode_timelapse.ps1` to read session metadata automatically.

## 0.2.0

- Added configurable encoding settings in the Blender panel.
- Added a standalone PowerShell FFmpeg helper.

## 0.1.0

- Initial viewport frame capture add-on.
