# Smart Collection Manager Free

## Download and Install

Download **Smart_Collection_Manager_Free.zip** from [Releases](https://github.com/NitroBlitzCoder/Smart-Collection-Manager/releases/latest), not the automatic source-code archives. Blender 5.0 or newer is required; Blender 4.2 is not supported by this release.

1. In Blender, open Preferences > Add-ons > menu > Install from Disk.
2. Select the release ZIP, enable the extension, and open its panel described below.
3. For an update, disable the previous edition, install the new ZIP, and restart Blender to clear cached Python modules. Enable only one edition per product.

## Quick Start

Open the Scene Tools sidebar. Sort active-scene objects by type, rename selected objects, inspect statistics, or hide empty private collections. Start with Exclusive Sort disabled when preserving existing collection memberships.

See [usage and troubleshooting](docs/USAGE.md) and [release notes](CHANGELOG.md). Report reproducible problems through [Issues](https://github.com/NitroBlitzCoder/Smart-Collection-Manager/issues), including Blender version, operating system, exact steps, and the complete traceback. Do not upload private project assets.

Version 1.1.1. Declared minimum: Blender 5.0. Tested in Blender 5.2.3 LTS
(build e13b728c6880), not every supported release.

## Install

Install `Smart_Collection_Manager_Free.zip`, enable it, and open **Scene Tools**
in the 3D View sidebar. ZIP packaging is separate. Both `__init__.py` and
`safety.py` must be included.

## Organization

- Sorts active-scene objects by type, including Text and Other destinations.
- Creates edition-owned collections under a scene-private **Smart Collections**
  root. Reuses only tagged private destinations under that root, never arbitrary
  global names. Blender may append numeric suffixes.
- Untagged collections from users or older versions are not automatically
  adopted. Free and Paid maintain separate roots.
- Snapshots objects before changing memberships and links before unlinking.
- **Exclusive Sort** unlinks only editable active-scene-private memberships,
  including direct scene-root links. Other-scene memberships, shared ancestry,
  instances, external references, linked IDs and overrides are protected.
  Exclusive can therefore retain several memberships; reports count those links.
- Linked/override objects are skipped by sort and rename. Operators require an
  editable local scene. Repeated sorting reuses eligible destinations.
- Rename supports selected/all scene objects, find/replace, prefix, suffix and
  numbering. A local object shared between scenes has one global datablock name,
  so renaming it changes its name wherever it is used.
- Stats count active-scene objects; collection/material totals are explicitly
  file-wide. Reports do not overwrite unrelated/linked texts by matching names.

## Visibility And Undo

Hide Empty Collections changes viewport visibility only for editable private
collections without objects anywhere in their subtree. Shared, instanced,
externally referenced and linked collections are skipped. This collection flag
affects all view layers of the scene, not render visibility or layer exclusion.

Restore Hidden Collections (operator ID `show_all`) restores only collections
this edition actually changed from visible to hidden. Pre-hidden collections
and manually hidden unrecorded collections stay hidden. Scene records use
collection pointers, survive renaming and save/reload with the add-on enabled,
and participate in undo. Deleted pointers are discarded; records that become
shared, non-editable or out-of-scene are retained until safe to restore.
This is not a history of later manual visibility edits.

Every mutating operator, including report writes, declares Blender undo support.

## Verification

Actual Blender 5.2.3 LTS: **10/10 workflow tests passed**, with real bpy.
Coverage: 67-object sorting, collisions/idempotence, cross-scene preservation,
shared ancestry, instances/external parents, actual linked IDs and overrides,
rename/stats/report protection, Free/Paid coexistence, visibility tracking,
save/reload, and undo/redo.

Background undo tests use explicit pushes around workflows and verify restored
data/redo; automatic interactive undo boundaries were not tested.
No UI screenshot or ZIP-install test is claimed.

Run only in a disposable Blender process, from the workspace root:

```sh
/private/tmp/codex-blender-523/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python work/addons/smart_collection_manager_free/tests/blender_workflows.py
```

This environment requires execution outside the sandbox. Tests create temporary
.blend fixtures; never run against an open production file.
