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


def _image_format_for_quality(image_quality):
    return "PNG" if image_quality == "PNG" else "JPEG"


def _jpeg_quality_for_quality(image_quality):
    if image_quality == "JPG_80":
        return 80
    if image_quality == "JPG_90":
        return 90
    return None


def _image_quality_label(image_quality):
    labels = {
        "JPG_80": "JPG 80%",
        "JPG_90": "JPG 90%",
        "PNG": "PNG",
    }
    return labels.get(image_quality, image_quality)


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


def _effective_session_name(settings):
    return settings.session_name.strip() or "sculpt_session"


def _ensure_session_defaults(settings):
    if not settings.project_name.strip():
        settings.project_name = _default_project_name()
    if not settings.session_name.strip():
        settings.session_name = "sculpt_session"


def _session_metadata(context, settings, ended_at=None):
    image_format = _image_format_for_quality(settings.image_quality)
    jpeg_quality = _jpeg_quality_for_quality(settings.image_quality)
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
        "capture_source": settings.capture_source,
        "image_format": image_format,
        "image_quality": settings.image_quality,
        "image_quality_label": _image_quality_label(settings.image_quality),
        "file_extension": extension,
        "jpeg_quality": jpeg_quality,
        "hide_overlays": settings.hide_overlays,
        "pause_while_idle": settings.pause_while_idle,
        "idle_threshold_seconds": settings.idle_threshold_seconds,
        "skipped_idle_captures": settings.skipped_idle_captures,
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


def _is_activity_event(event):
    if event.type in {"TIMER", "NONE"}:
        return False
    if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE", "TRACKPADPAN", "TRACKPADZOOM"}:
        return True
    if getattr(event, "value", None) in {"PRESS", "RELEASE", "CLICK", "DOUBLE_CLICK", "CLICK_DRAG"}:
        return True
    return False


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
    default_image_quality: EnumProperty(
        name="Default Image Quality",
        description="Default quality preset for captured frames",
        items=(
            ("JPG_80", "JPG 80%", "Small files for very long sessions"),
            ("JPG_90", "JPG 90%", "Balanced default for sculpt timelapses"),
            ("PNG", "PNG", "Lossless frames with larger files"),
        ),
        default="JPG_90",
    )
    default_capture_source: EnumProperty(
        name="Default Capture Source",
        description="Default source for captured frames",
        items=(
            ("VIEW", "Active View", "Capture the current 3D View"),
            ("CAMERA", "Scene Camera", "Capture from the active scene camera"),
        ),
        default="VIEW",
    )
    default_hide_overlays: BoolProperty(
        name="Hide Overlays by Default",
        description="Temporarily hide viewport overlays while each frame is captured",
        default=True,
    )
    default_pause_while_idle: BoolProperty(
        name="Pause While Idle",
        description="Skip captures when no Blender input has been seen recently",
        default=True,
    )
    default_idle_threshold_seconds: FloatProperty(
        name="Idle After",
        description="Seconds of no Blender input before capture pauses",
        default=30.0,
        min=5.0,
        soft_max=600.0,
        unit="TIME",
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
        layout.prop(self, "default_image_quality")
        layout.prop(self, "default_capture_source")
        layout.prop(self, "default_hide_overlays")
        layout.prop(self, "default_pause_while_idle")
        if self.default_pause_while_idle:
            layout.prop(self, "default_idle_threshold_seconds")
        layout.prop(self, "default_recommended_fps")
        layout.prop(self, "copy_encoder_script")


class SCT_Settings(PropertyGroup):
    project_name: StringProperty(
        name="Project",
        description="Project folder name",
        default="",
    )
    session_name: StringProperty(
        name="Session",
        description="Label added to this capture session folder",
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
    image_quality: EnumProperty(
        name="Image Quality",
        description="Quality preset for captured frames",
        items=(
            ("JPG_80", "JPG 80%", "Small files for very long sessions"),
            ("JPG_90", "JPG 90%", "Balanced default for sculpt timelapses"),
            ("PNG", "PNG", "Lossless frames with larger files"),
        ),
        default="JPG_90",
    )
    capture_source: EnumProperty(
        name="Capture Source",
        description="Source used for captured frames",
        items=(
            ("VIEW", "Active View", "Capture the current 3D View"),
            ("CAMERA", "Scene Camera", "Capture from the active scene camera"),
        ),
        default="VIEW",
    )
    hide_overlays: BoolProperty(
        name="Hide Overlays",
        description="Temporarily hide viewport overlays while each frame is captured",
        default=True,
    )
    pause_while_idle: BoolProperty(
        name="Pause While Idle",
        description="Skip captures when no Blender input has been seen recently",
        default=True,
    )
    idle_threshold_seconds: FloatProperty(
        name="Idle After",
        description="Seconds of no Blender input before capture pauses",
        default=30.0,
        min=5.0,
        soft_max=600.0,
        unit="TIME",
    )
    skipped_idle_captures: IntProperty(
        name="Idle Skips",
        default=0,
        min=0,
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

        _ensure_session_defaults(settings)
        settings.output_root = prefs.default_output_root
        settings.interval_seconds = prefs.default_interval_seconds
        settings.image_quality = prefs.default_image_quality
        settings.capture_source = prefs.default_capture_source
        settings.hide_overlays = prefs.default_hide_overlays
        settings.pause_while_idle = prefs.default_pause_while_idle
        settings.idle_threshold_seconds = prefs.default_idle_threshold_seconds
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
    _last_activity = 0.0
    _was_idle = False

    def invoke(self, context, event):
        settings = context.scene.sct_settings
        prefs = _addon_preferences(context)
        _ensure_session_defaults(settings)

        if settings.is_running:
            self.report({"WARNING"}, "Timelapse capture is already running")
            return {"CANCELLED"}

        if settings.capture_source == "VIEW" and _find_view3d_context(context.window) is None:
            self.report({"ERROR"}, "Open a 3D View before starting capture")
            return {"CANCELLED"}

        if settings.capture_source == "CAMERA" and context.scene.camera is None:
            self.report({"ERROR"}, "Scene Camera capture requires an active scene camera")
            return {"CANCELLED"}

        root_value = settings.output_root or (prefs.default_output_root if prefs else "//timelapse_sessions")
        output_root = Path(_resolved_path(root_value))
        project_name = _effective_project_name(settings)
        project_slug = _slug(project_name, "Untitled_Project")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        session_slug = _slug(_effective_session_name(settings), "sculpt_session")
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
        settings.skipped_idle_captures = 0
        settings.session_dir = str(session_dir)
        settings.active_project_name = project_name
        settings.active_session_name = _effective_session_name(settings)
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
        self._last_activity = time.monotonic()
        self._was_idle = False
        self._timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        settings = context.scene.sct_settings
        if not settings.is_running:
            self._finish(context)
            return {"CANCELLED"}

        if event.type != "TIMER":
            if _is_activity_event(event):
                self._last_activity = time.monotonic()
                if self._was_idle:
                    self._next_capture = 0.0
                    self._was_idle = False
                    settings.status = "Capturing"
            return {"PASS_THROUGH"}

        now = time.monotonic()
        if now >= self._next_capture:
            if settings.pause_while_idle and now - self._last_activity >= settings.idle_threshold_seconds:
                settings.skipped_idle_captures += 1
                settings.status = "Idle; capture paused"
                self._was_idle = True
                self._next_capture = now + settings.interval_seconds
                _write_session_metadata(context, settings)
                return {"PASS_THROUGH"}

            self._capture_frame(context)
            self._next_capture = now + settings.interval_seconds

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
        view_context = None
        if settings.capture_source == "VIEW":
            view_context = _find_view3d_context(context.window)
            if view_context is None:
                settings.status = "No 3D View found"
                return
        elif context.scene.camera is None:
            settings.status = "No scene camera found"
            return

        frame_number = settings.frame_count + 1
        image_format = _image_format_for_quality(settings.image_quality)
        jpeg_quality = _jpeg_quality_for_quality(settings.image_quality)
        extension = _extension_for_format(image_format)
        filepath = os.path.join(settings.session_dir, f"frame_{frame_number:06d}{extension}")

        render = context.scene.render
        image_settings = render.image_settings
        previous_filepath = render.filepath
        previous_format = image_settings.file_format
        previous_quality = image_settings.quality
        previous_overlays = None

        try:
            render.filepath = filepath
            image_settings.file_format = image_format
            if image_format == "JPEG" and jpeg_quality is not None:
                image_settings.quality = jpeg_quality

            if settings.capture_source == "VIEW":
                area, region, space = view_context
                previous_overlays = space.overlay.show_overlays

                if settings.hide_overlays:
                    space.overlay.show_overlays = False

                with context.temp_override(window=context.window, screen=context.screen, area=area, region=region):
                    bpy.ops.render.opengl(write_still=True, view_context=True)
            else:
                bpy.ops.render.opengl(write_still=True, view_context=False)

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
            if settings.capture_source == "VIEW" and previous_overlays is not None:
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
        layout.prop(settings, "image_quality")
        layout.prop(settings, "capture_source")
        layout.prop(settings, "hide_overlays")
        layout.prop(settings, "pause_while_idle")
        if settings.pause_while_idle:
            layout.prop(settings, "idle_threshold_seconds")
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
        if settings.skipped_idle_captures:
            layout.label(text=f"Idle skips: {settings.skipped_idle_captures}")
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
    for scene in bpy.data.scenes:
        _ensure_session_defaults(scene.sct_settings)


def unregister():
    for scene in bpy.data.scenes:
        if hasattr(scene, "sct_settings"):
            scene.sct_settings.is_running = False

    if hasattr(bpy.types.Scene, "sct_settings"):
        del bpy.types.Scene.sct_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
