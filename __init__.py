import datetime
import json
import os
import re
import shutil
import time
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import AddonPreferences, Operator, Panel, PropertyGroup


ADDON_ID = __package__ or __name__


def _resolved_path(path_value):
    if not path_value:
        return ""
    return bpy.path.abspath(path_value)


def _extension_for_format(image_format):
    return ".png" if image_format == "PNG" else ".jpg"


def _slug(value, fallback):
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "", value or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned).replace(" ", "_")
    return cleaned or fallback


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _addon_preferences(context):
    addon = context.preferences.addons.get(ADDON_ID)
    if addon:
        return addon.preferences
    return None


def _default_project_name():
    blend_path = bpy.data.filepath
    if blend_path:
        return Path(blend_path).stem
    return "Untitled_Project"


def _effective_project_name(settings):
    return settings.project_name.strip() or _default_project_name()


def _session_metadata(context, settings, ended_at=None):
    image_format = settings.image_format
    extension = _extension_for_format(image_format).lstrip(".")
    session_path = Path(settings.session_dir)

    return {
        "schema_version": 1,
        "addon": "Sculpt Timelapse Capture",
        "project_name": settings.active_project_name or _effective_project_name(settings),
        "session_name": settings.active_session_name,
        "blend_file": bpy.data.filepath,
        "started_at": settings.started_at,
        "ended_at": ended_at,
        "session_dir": str(session_path),
        "frame_pattern": f"frame_%06d.{extension}",
        "first_frame": f"frame_000001.{extension}",
        "frame_count": settings.frame_count,
        "interval_seconds": settings.interval_seconds,
        "image_format": image_format,
        "file_extension": extension,
        "jpeg_quality": settings.jpeg_quality if image_format == "JPEG" else None,
        "hide_overlays": settings.hide_overlays,
        "recommended_fps": settings.recommended_fps,
        "recommended_output": "timelapse.mp4",
        "blender_version": bpy.app.version_string,
    }


def _write_session_metadata(context, settings, ended_at=None):
    if not settings.session_dir:
        return

    metadata_path = Path(settings.session_dir) / "session.json"
    metadata = _session_metadata(context, settings, ended_at=ended_at)
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
        handle.write("\n")


def _copy_encoder_script(session_dir):
    source = Path(__file__).with_name("encode_timelapse.ps1")
    if not source.exists():
        return
    shutil.copy2(source, Path(session_dir) / "encode_timelapse.ps1")


def _find_view3d_context(window):
    screen = window.screen if window else None
    if screen is None:
        return None

    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue

        region = next((item for item in area.regions if item.type == "WINDOW"), None)
        space = next((item for item in area.spaces if item.type == "VIEW_3D"), None)
        if region and space:
            return area, region, space

    return None


class SCT_AddonPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    default_output_root: StringProperty(
        name="Default Timelapse Root",
        description="Root folder used for new timelapse sessions",
        subtype="DIR_PATH",
        default="//timelapse_sessions",
    )
    default_interval_seconds: FloatProperty(
        name="Default Interval",
        description="Default seconds between captured frames",
        default=20.0,
        min=1.0,
        soft_max=120.0,
        unit="TIME",
    )
    default_image_format: EnumProperty(
        name="Default Format",
        description="Default image format for captured frames",
        items=(
            ("JPEG", "JPEG", "Small files, best default for long sessions"),
            ("PNG", "PNG", "Lossless frames with larger files"),
        ),
        default="JPEG",
    )
    default_jpeg_quality: IntProperty(
        name="Default JPEG Quality",
        description="Default JPEG quality for captured frames",
        default=90,
        min=1,
        max=100,
    )
    default_hide_overlays: BoolProperty(
        name="Hide Overlays by Default",
        description="Temporarily hide viewport overlays while each frame is captured",
        default=True,
    )
    default_recommended_fps: IntProperty(
        name="Recommended Encode FPS",
        description="Playback frame rate written to session metadata",
        default=30,
        min=1,
        max=120,
    )
    copy_encoder_script: BoolProperty(
        name="Copy Encoder Script to Sessions",
        description="Copy encode_timelapse.ps1 into each session folder",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "default_output_root")
        layout.prop(self, "default_interval_seconds")
        layout.prop(self, "default_image_format")
        if self.default_image_format == "JPEG":
            layout.prop(self, "default_jpeg_quality")
        layout.prop(self, "default_hide_overlays")
        layout.prop(self, "default_recommended_fps")
        layout.prop(self, "copy_encoder_script")


class SCT_Settings(PropertyGroup):
    project_name: StringProperty(
        name="Project",
        description="Project folder name. Leave blank to use the blend file name",
        default="",
    )
    session_name: StringProperty(
        name="Session",
        description="Optional label added to this capture session folder",
        default="",
    )
    output_root: StringProperty(
        name="Root Folder",
        description="Root folder where project and session folders will be created",
        subtype="DIR_PATH",
        default="",
    )
    interval_seconds: FloatProperty(
        name="Interval",
        description="Seconds between captured frames",
        default=20.0,
        min=1.0,
        soft_max=120.0,
        unit="TIME",
    )
    image_format: EnumProperty(
        name="Format",
        description="Image format for captured frames",
        items=(
            ("JPEG", "JPEG", "Small files, best default for long sessions"),
            ("PNG", "PNG", "Lossless frames with larger files"),
        ),
        default="JPEG",
    )
    jpeg_quality: IntProperty(
        name="JPEG Quality",
        description="JPEG quality for captured frames",
        default=90,
        min=1,
        max=100,
    )
    hide_overlays: BoolProperty(
        name="Hide Overlays",
        description="Temporarily hide viewport overlays while each frame is captured",
        default=True,
    )
    recommended_fps: IntProperty(
        name="Encode FPS",
        description="Recommended playback frame rate written to session metadata",
        default=30,
        min=1,
        max=120,
    )
    frame_count: IntProperty(
        name="Captured",
        default=0,
        min=0,
    )
    is_running: BoolProperty(
        name="Running",
        default=False,
    )
    session_dir: StringProperty(
        name="Session Folder",
        default="",
        subtype="DIR_PATH",
    )
    active_project_name: StringProperty(default="")
    active_session_name: StringProperty(default="")
    started_at: StringProperty(default="")
    status: StringProperty(
        name="Status",
        default="Ready",
    )


class SCT_OT_apply_preferences_defaults(Operator):
    bl_idname = "sct.apply_preferences_defaults"
    bl_label = "Apply Defaults"
    bl_description = "Apply add-on preference defaults to this scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        prefs = _addon_preferences(context)
        settings = context.scene.sct_settings
        if prefs is None:
            return {"CANCELLED"}

        settings.output_root = prefs.default_output_root
        settings.interval_seconds = prefs.default_interval_seconds
        settings.image_format = prefs.default_image_format
        settings.jpeg_quality = prefs.default_jpeg_quality
        settings.hide_overlays = prefs.default_hide_overlays
        settings.recommended_fps = prefs.default_recommended_fps
        settings.status = "Defaults applied"
        return {"FINISHED"}


class SCT_OT_start_capture(Operator):
    bl_idname = "sct.start_capture"
    bl_label = "Start Capture"
    bl_description = "Start capturing viewport timelapse frames"
    bl_options = {"REGISTER"}

    _timer = None
    _next_capture = 0.0

    def invoke(self, context, event):
        settings = context.scene.sct_settings
        prefs = _addon_preferences(context)

        if settings.is_running:
            self.report({"WARNING"}, "Timelapse capture is already running")
            return {"CANCELLED"}

        view_context = _find_view3d_context(context.window)
        if view_context is None:
            self.report({"ERROR"}, "Open a 3D View before starting capture")
            return {"CANCELLED"}

        root_value = settings.output_root or (prefs.default_output_root if prefs else "//timelapse_sessions")
        output_root = Path(_resolved_path(root_value))
        project_name = _effective_project_name(settings)
        project_slug = _slug(project_name, "Untitled_Project")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        session_slug = _slug(settings.session_name, "capture")
        session_dir = output_root / project_slug / f"{timestamp}_{session_slug}"

        try:
            session_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            self.report({"ERROR"}, f"Session folder already exists: {session_dir}")
            return {"CANCELLED"}
        except OSError as exc:
            self.report({"ERROR"}, f"Could not create session folder: {exc}")
            return {"CANCELLED"}

        settings.frame_count = 0
        settings.session_dir = str(session_dir)
        settings.active_project_name = project_name
        settings.active_session_name = settings.session_name.strip() or "capture"
        settings.started_at = _now_iso()
        settings.is_running = True
        settings.status = "Capturing"

        try:
            _write_session_metadata(context, settings)
            if prefs is None or prefs.copy_encoder_script:
                _copy_encoder_script(session_dir)
        except OSError as exc:
            settings.status = f"Metadata setup failed: {exc}"
            self.report({"ERROR"}, settings.status)
            settings.is_running = False
            return {"CANCELLED"}

        self._next_capture = 0.0
        self._timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if not context.scene.sct_settings.is_running:
            self._finish(context)
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        now = time.monotonic()
        if now >= self._next_capture:
            self._capture_frame(context)
            self._next_capture = now + context.scene.sct_settings.interval_seconds

        return {"PASS_THROUGH"}

    def _finish(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

        settings = context.scene.sct_settings
        settings.is_running = False
        settings.status = "Stopped"
        _write_session_metadata(context, settings, ended_at=_now_iso())

    def _capture_frame(self, context):
        settings = context.scene.sct_settings
        view_context = _find_view3d_context(context.window)
        if view_context is None:
            settings.status = "No 3D View found"
            return

        area, region, space = view_context
        frame_number = settings.frame_count + 1
        extension = _extension_for_format(settings.image_format)
        filepath = os.path.join(settings.session_dir, f"frame_{frame_number:06d}{extension}")

        render = context.scene.render
        image_settings = render.image_settings
        previous_filepath = render.filepath
        previous_format = image_settings.file_format
        previous_quality = image_settings.quality
        previous_overlays = space.overlay.show_overlays

        try:
            render.filepath = filepath
            image_settings.file_format = settings.image_format
            if settings.image_format == "JPEG":
                image_settings.quality = settings.jpeg_quality

            if settings.hide_overlays:
                space.overlay.show_overlays = False

            with context.temp_override(window=context.window, screen=context.screen, area=area, region=region):
                bpy.ops.render.opengl(write_still=True, view_context=True)

            settings.frame_count = frame_number
            settings.status = f"Captured {frame_number} frame{'s' if frame_number != 1 else ''}"
            _write_session_metadata(context, settings)
        except Exception as exc:
            settings.status = f"Capture failed: {exc}"
            self.report({"ERROR"}, settings.status)
        finally:
            render.filepath = previous_filepath
            image_settings.file_format = previous_format
            image_settings.quality = previous_quality
            space.overlay.show_overlays = previous_overlays


class SCT_OT_stop_capture(Operator):
    bl_idname = "sct.stop_capture"
    bl_label = "Stop Capture"
    bl_description = "Stop capturing timelapse frames"
    bl_options = {"REGISTER"}

    def execute(self, context):
        settings = context.scene.sct_settings
        settings.is_running = False
        settings.status = "Stopping" if settings.session_dir else "Stopped"
        if settings.session_dir:
            _write_session_metadata(context, settings, ended_at=_now_iso())

        return {"FINISHED"}


class SCT_PT_panel(Panel):
    bl_label = "Sculpt Timelapse"
    bl_idname = "SCT_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Timelapse"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.sct_settings

        row = layout.row(align=True)
        row.enabled = not settings.is_running
        row.operator("sct.apply_preferences_defaults", icon="PREFERENCES")

        layout.prop(settings, "project_name")
        layout.prop(settings, "session_name")
        layout.prop(settings, "output_root")

        layout.separator()
        layout.prop(settings, "interval_seconds")
        layout.prop(settings, "image_format", expand=True)

        if settings.image_format == "JPEG":
            layout.prop(settings, "jpeg_quality")

        layout.prop(settings, "hide_overlays")
        layout.prop(settings, "recommended_fps")

        row = layout.row(align=True)
        row.enabled = not settings.is_running
        row.operator("sct.start_capture", icon="REC")

        row = layout.row(align=True)
        row.enabled = settings.is_running
        row.operator("sct.stop_capture", icon="PAUSE")

        layout.separator()
        layout.label(text=f"Status: {settings.status}")
        layout.label(text=f"Frames: {settings.frame_count}")
        if settings.session_dir:
            layout.prop(settings, "session_dir", text="Folder")


classes = (
    SCT_AddonPreferences,
    SCT_Settings,
    SCT_OT_apply_preferences_defaults,
    SCT_OT_start_capture,
    SCT_OT_stop_capture,
    SCT_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.sct_settings = PointerProperty(type=SCT_Settings)


def unregister():
    for scene in bpy.data.scenes:
        if hasattr(scene, "sct_settings"):
            scene.sct_settings.is_running = False

    if hasattr(bpy.types.Scene, "sct_settings"):
        del bpy.types.Scene.sct_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
