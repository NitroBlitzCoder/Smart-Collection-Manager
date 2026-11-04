bl_info = {
    "name": "Smart Collection Manager Free",
    "author": "Codex",
    "version": (1, 1, 1),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Scene Tools",
    "description": "Sort objects by type, rename batches, view scene stats, and hide empty collections.",
    "category": "Object",
}

import bpy
from bpy.props import BoolProperty, CollectionProperty, PointerProperty, StringProperty
from .safety import (
    SceneOperator, editable, ensure_child, hide_empty,
    managed_root, move_object, private_collections, restore_hidden, write_report,
)


OWNER = "smart_collection_manager_free"


TYPE_COLLECTIONS = {
    "MESH": "Meshes",
    "LIGHT": "Lights",
    "CAMERA": "Cameras",
    "CURVE": "Curves",
    "ARMATURE": "Armatures",
    "EMPTY": "Empties",
    "FONT": "Text",
}


class SCMFREE_HiddenCollection(bpy.types.PropertyGroup):
    collection: PointerProperty(type=bpy.types.Collection)


def scene_stats(scene):
    counts = {}
    for obj in scene.objects:
        counts[obj.type] = counts.get(obj.type, 0) + 1
    return counts


def apply_rename(obj, scene, index):
    name = obj.name
    if scene.scm_search:
        name = name.replace(scene.scm_search, scene.scm_replace)
    if scene.scm_prefix:
        name = scene.scm_prefix + name
    if scene.scm_suffix:
        name = name + scene.scm_suffix
    if scene.scm_zero_pad:
        name = name + "_" + str(index).zfill(3)
    obj.name = name


class SCMFREE_OT_sort_by_type(SceneOperator, bpy.types.Operator):
    bl_idname = "smart_collection_free.sort_by_type"
    bl_label = "Sort By Type"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Sort scene objects into Meshes, Lights, Cameras, Curves, Armatures, Empties, and Other"

    def execute(self, context):
        scene = context.scene
        targets = tuple(scene.objects)
        private = private_collections(scene)
        root = None
        moved = skipped = retained = 0
        for obj in targets:
            if not editable(obj):
                skipped += 1
                continue
            try:
                if root is None:
                    root = managed_root(scene, OWNER, private)
                target = ensure_child(root, TYPE_COLLECTIONS.get(obj.type, "Other"), OWNER, private)
                success, protected = move_object(obj, target, scene.scm_exclusive_sort, private)
                moved += int(success)
                retained += protected
            except RuntimeError:
                skipped += 1
        self.report(
            {"WARNING"} if skipped or retained else {"INFO"},
            f"Sorted {moved}; skipped {skipped}; retained {retained} protected memberships.",
        )
        return {"FINISHED"}


class SCMFREE_OT_rename_objects(SceneOperator, bpy.types.Operator):
    bl_idname = "smart_collection_free.rename_objects"
    bl_label = "Rename Objects"
    bl_options = {"REGISTER", "UNDO"}
    bl_description = "Apply prefix, suffix, find/replace, and optional numbering"

    def execute(self, context):
        scene = context.scene
        scene_objects = tuple(scene.objects)
        members = set(scene_objects)
        targets = tuple(context.selected_objects) if scene.scm_rename_selected_only else scene_objects
        renamed = skipped = 0
        for obj in targets:
            if obj not in members or not editable(obj):
                skipped += 1
                continue
            try:
                apply_rename(obj, scene, renamed + 1)
                renamed += 1
            except RuntimeError:
                skipped += 1
        self.report(
            {"WARNING"} if skipped else {"INFO"},
            f"Renamed {renamed}; skipped {skipped} non-editable or out-of-scene objects.",
        )
        return {"FINISHED"}


class SCMFREE_OT_hide_empty_collections(SceneOperator, bpy.types.Operator):
    bl_idname = "smart_collection_free.hide_empty"
    bl_label = "Hide Empty Collections"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        hidden = hide_empty(context.scene, context.scene.scm_hidden_collections)
        self.report({"INFO"}, "Hidden " + str(hidden) + " empty collections.")
        return {"FINISHED"}


class SCMFREE_OT_show_all_collections(SceneOperator, bpy.types.Operator):
    bl_idname = "smart_collection_free.show_all"
    bl_label = "Restore Hidden Collections"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        restored, retained = restore_hidden(context.scene, context.scene.scm_hidden_collections)
        self.report(
            {"WARNING"} if retained else {"INFO"},
            f"Restored {restored}; retained {retained} protected visibility records.",
        )
        return {"FINISHED"}


class SCMFREE_OT_stats_report(SceneOperator, bpy.types.Operator):
    bl_idname = "smart_collection_free.stats_report"
    bl_label = "Write Stats Report"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        counts = scene_stats(scene)
        lines = [
            "Smart Collection Manager Free - Scene Stats",
            "Scene: " + scene.name,
            "Objects: " + str(len(scene.objects)),
            "Collections (file): " + str(len(bpy.data.collections)),
            "Materials (file): " + str(len(bpy.data.materials)),
            "",
        ]
        for obj_type in sorted(counts):
            lines.append(obj_type.title() + ": " + str(counts[obj_type]))
        text = write_report("Smart_Collection_Stats_Free", "\n".join(lines), OWNER)
        self.report({"INFO"}, "Scene stats written to " + text.name + ".")
        return {"FINISHED"}


class SCMFREE_PT_panel(bpy.types.Panel):
    bl_label = "Smart Collection Manager Free"
    bl_idname = "SCMFREE_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Scene Tools"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        stats = scene_stats(scene)

        layout.label(text="Scene Stats", icon="INFO")
        row = layout.row(align=True)
        row.label(text="Objects: " + str(len(scene.objects)))
        row.label(text="Collections (file): " + str(len(bpy.data.collections)))
        layout.label(text="Meshes: " + str(stats.get("MESH", 0)) + "  Lights: " + str(stats.get("LIGHT", 0)) + "  Cameras: " + str(stats.get("CAMERA", 0)))
        layout.operator("smart_collection_free.stats_report", icon="TEXT")

        box = layout.box()
        box.label(text="Organize", icon="OUTLINER_COLLECTION")
        box.prop(scene, "scm_exclusive_sort")
        box.operator("smart_collection_free.sort_by_type", icon="SORTALPHA")
        row = box.row(align=True)
        row.operator("smart_collection_free.hide_empty", icon="HIDE_ON")
        row.operator("smart_collection_free.show_all", icon="HIDE_OFF")

        rename = layout.box()
        rename.label(text="Rename", icon="OUTLINER_OB_FONT")
        rename.prop(scene, "scm_rename_selected_only")
        rename.prop(scene, "scm_prefix")
        rename.prop(scene, "scm_suffix")
        row = rename.row(align=True)
        row.prop(scene, "scm_search")
        row.prop(scene, "scm_replace")
        rename.prop(scene, "scm_zero_pad")
        rename.operator("smart_collection_free.rename_objects", icon="GREASEPENCIL")


classes = (
    SCMFREE_HiddenCollection,
    SCMFREE_OT_sort_by_type,
    SCMFREE_OT_rename_objects,
    SCMFREE_OT_hide_empty_collections,
    SCMFREE_OT_show_all_collections,
    SCMFREE_OT_stats_report,
    SCMFREE_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.scm_hidden_collections = CollectionProperty(type=SCMFREE_HiddenCollection)
    bpy.types.Scene.scm_exclusive_sort = BoolProperty(
        name="Exclusive Sort", default=False,
        description="Unlink only editable scene-private memberships; preserve shared and linked collections",
    )
    bpy.types.Scene.scm_rename_selected_only = BoolProperty(name="Selected Only", default=True)
    bpy.types.Scene.scm_prefix = StringProperty(name="Prefix", default="")
    bpy.types.Scene.scm_suffix = StringProperty(name="Suffix", default="")
    bpy.types.Scene.scm_search = StringProperty(name="Find", default="")
    bpy.types.Scene.scm_replace = StringProperty(name="Replace", default="")
    bpy.types.Scene.scm_zero_pad = BoolProperty(name="Add Numbering", default=False)


def unregister():
    del bpy.types.Scene.scm_hidden_collections
    del bpy.types.Scene.scm_zero_pad
    del bpy.types.Scene.scm_replace
    del bpy.types.Scene.scm_search
    del bpy.types.Scene.scm_suffix
    del bpy.types.Scene.scm_prefix
    del bpy.types.Scene.scm_rename_selected_only
    del bpy.types.Scene.scm_exclusive_sort
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
