bl_info = {
    "name": "Smart Collection Manager Free",
    "author": "Codex",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Scene Tools",
    "description": "Sort objects by type, rename batches, view scene stats, and hide empty collections.",
    "category": "Object",
}

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty


TYPE_COLLECTIONS = {
    "MESH": "Meshes",
    "LIGHT": "Lights",
    "CAMERA": "Cameras",
    "CURVE": "Curves",
    "ARMATURE": "Armatures",
    "EMPTY": "Empties",
    "FONT": "Text",
}


def managed_root(scene):
    root = bpy.data.collections.get("Smart Collections")
    if root is None:
        root = bpy.data.collections.new("Smart Collections")
    if root.name not in [child.name for child in scene.collection.children]:
        scene.collection.children.link(root)
    return root


def ensure_child(parent, name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
    if collection.name not in [child.name for child in parent.children]:
        parent.children.link(collection)
    return collection


def target_collection_for(scene, obj):
    root = managed_root(scene)
    return ensure_child(root, TYPE_COLLECTIONS.get(obj.type, "Other"))


def collection_has_content(collection):
    if collection.objects:
        return True
    return any(collection_has_content(child) for child in collection.children)


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


class SCMFREE_OT_sort_by_type(bpy.types.Operator):
    bl_idname = "smart_collection_free.sort_by_type"
    bl_label = "Sort By Type"
    bl_description = "Sort scene objects into Meshes, Lights, Cameras, Curves, Armatures, Empties, and Other"

    def execute(self, context):
        scene = context.scene
        moved = 0
        managed_names = set(TYPE_COLLECTIONS.values()) | {"Other"}
        for obj in scene.objects:
            target = target_collection_for(scene, obj)
            if obj.name not in [member.name for member in target.objects]:
                target.objects.link(obj)
            if scene.scm_exclusive_sort:
                for collection in list(obj.users_collection):
                    if collection != target and (collection.name in managed_names or collection.name != scene.collection.name):
                        try:
                            collection.objects.unlink(obj)
                        except RuntimeError:
                            pass
            moved += 1
        self.report({"INFO"}, "Sorted " + str(moved) + " objects.")
        return {"FINISHED"}


class SCMFREE_OT_rename_objects(bpy.types.Operator):
    bl_idname = "smart_collection_free.rename_objects"
    bl_label = "Rename Objects"
    bl_description = "Apply prefix, suffix, find/replace, and optional numbering"

    def execute(self, context):
        scene = context.scene
        targets = context.selected_objects if scene.scm_rename_selected_only else list(scene.objects)
        for index, obj in enumerate(targets, start=1):
            apply_rename(obj, scene, index)
        self.report({"INFO"}, "Renamed " + str(len(targets)) + " objects.")
        return {"FINISHED"}


class SCMFREE_OT_hide_empty_collections(bpy.types.Operator):
    bl_idname = "smart_collection_free.hide_empty"
    bl_label = "Hide Empty Collections"

    def execute(self, context):
        hidden = 0
        for collection in bpy.data.collections:
            if not collection_has_content(collection):
                collection.hide_viewport = True
                hidden += 1
        self.report({"INFO"}, "Hidden " + str(hidden) + " empty collections.")
        return {"FINISHED"}


class SCMFREE_OT_show_all_collections(bpy.types.Operator):
    bl_idname = "smart_collection_free.show_all"
    bl_label = "Show Collections"

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.hide_viewport = False
        return {"FINISHED"}


class SCMFREE_OT_stats_report(bpy.types.Operator):
    bl_idname = "smart_collection_free.stats_report"
    bl_label = "Write Stats Report"

    def execute(self, context):
        scene = context.scene
        counts = scene_stats(scene)
        lines = [
            "Smart Collection Manager Free - Scene Stats",
            "Scene: " + scene.name,
            "Objects: " + str(len(scene.objects)),
            "Collections: " + str(len(bpy.data.collections)),
            "Materials: " + str(len(bpy.data.materials)),
            "",
        ]
        for obj_type in sorted(counts):
            lines.append(obj_type.title() + ": " + str(counts[obj_type]))
        text = bpy.data.texts.get("Smart_Collection_Stats") or bpy.data.texts.new("Smart_Collection_Stats")
        text.clear()
        text.write("\n".join(lines))
        self.report({"INFO"}, "Scene stats written to Smart_Collection_Stats.")
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
        row.label(text="Collections: " + str(len(bpy.data.collections)))
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
    bpy.types.Scene.scm_exclusive_sort = BoolProperty(name="Exclusive Sort", default=False)
    bpy.types.Scene.scm_rename_selected_only = BoolProperty(name="Selected Only", default=True)
    bpy.types.Scene.scm_prefix = StringProperty(name="Prefix", default="")
    bpy.types.Scene.scm_suffix = StringProperty(name="Suffix", default="")
    bpy.types.Scene.scm_search = StringProperty(name="Find", default="")
    bpy.types.Scene.scm_replace = StringProperty(name="Replace", default="")
    bpy.types.Scene.scm_zero_pad = BoolProperty(name="Add Numbering", default=False)


def unregister():
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
