"""Conservative collection mutation helpers, bundled independently in each edition."""

import bpy


OWNER_KEY = "_scm_owner"
ROOT_KEY = "_scm_root"
DESTINATION_KEY = "_scm_destination"


def editable(datablock):
    return (
        datablock is not None
        and datablock.library is None
        and datablock.override_library is None
        and datablock.is_editable
    )


def collection_tree(root):
    """Snapshot a DAG without recursion or duplicate visits."""
    found = set()
    pending = [root]
    while pending:
        collection = pending.pop()
        if collection in found:
            continue
        found.add(collection)
        pending.extend(tuple(collection.children))
    return found


def private_collections(scene):
    """Exclude shared/instanced/referenced collections and their descendants."""
    members = collection_tree(scene.collection)
    blocked = {item for item in members if not editable(item)}
    for other_scene in bpy.data.scenes:
        if other_scene != scene:
            blocked.update(members & collection_tree(other_scene.collection))
    users = bpy.data.user_map(subset=tuple(members - {scene.collection}))
    allowed_users = members | {scene}
    for collection, references in users.items():
        if references - allowed_users:
            blocked.add(collection)
    protected = set()
    for collection in blocked:
        protected.update(collection_tree(collection))
    return members - protected


def managed_root(scene, owner, private):
    if scene.collection not in private:
        raise RuntimeError("The active scene collection is not editable")
    for child in tuple(scene.collection.children):
        if child in private and child.get(OWNER_KEY) == owner and child.get(ROOT_KEY):
            return child
    root = bpy.data.collections.new("Smart Collections")
    root[OWNER_KEY] = owner
    root[ROOT_KEY] = True
    scene.collection.children.link(root)
    private.add(root)
    return root


def ensure_child(parent, name, owner, private):
    if parent not in private or not editable(parent):
        raise RuntimeError("The destination collection is not scene-private")
    for child in tuple(parent.children):
        if (
            child in private
            and child.get(OWNER_KEY) == owner
            and child.get(DESTINATION_KEY) == name
            and not child.get(ROOT_KEY)
        ):
            return child
    collection = bpy.data.collections.new(name)
    collection[OWNER_KEY] = owner
    collection[DESTINATION_KEY] = name
    parent.children.link(collection)
    private.add(collection)
    return collection


def collection_has_content(collection):
    return any(item.objects for item in collection_tree(collection))


def move_object(obj, target, exclusive, private):
    """Link before unlinking, retaining memberships whose owners are protected."""
    if not editable(obj):
        return False, 0
    if obj not in tuple(target.objects):
        target.objects.link(obj)
    retained = 0
    if exclusive:
        for source in tuple(obj.users_collection):
            if source == target:
                continue
            if source not in private or not editable(source):
                retained += 1
                continue
            try:
                source.objects.unlink(obj)
            except RuntimeError:
                retained += 1
    return True, retained


def hide_empty(scene, records):
    hidden = 0
    for collection in private_collections(scene) - {scene.collection}:
        if not collection.hide_viewport and not collection_has_content(collection):
            record = records.add()
            record.collection = collection
            collection.hide_viewport = True
            hidden += 1
    return hidden


def restore_hidden(scene, records):
    private = private_collections(scene)
    restored = 0
    retained = 0
    for index in range(len(records) - 1, -1, -1):
        collection = records[index].collection
        if collection is None:
            records.remove(index)
        elif collection not in private:
            retained += 1
        else:
            collection.hide_viewport = False
            restored += 1
            records.remove(index)
    return restored, retained


def write_report(name, body, owner):
    # Never overwrite an unrelated or linked text with a coinciding display name.
    text = next(
        (
            item for item in bpy.data.texts
            if editable(item) and item.get(OWNER_KEY) == owner
            and item.get(DESTINATION_KEY) == name
        ),
        None,
    )
    if text is None:
        text = bpy.data.texts.new(name)
        text[OWNER_KEY] = owner
        text[DESTINATION_KEY] = name
    text.clear()
    text.write(body)
    return text


class SceneOperator:
    @classmethod
    def poll(cls, context):
        scene = getattr(context, "scene", None)
        return editable(scene) and editable(scene.collection)

