import os
import bpy

from pathlib import Path
from bpy.types import Operator
from bpy.props import CollectionProperty, BoolProperty, StringProperty
from __init__ import PrettyPrint, Global_gamepath, Global_TocManager, BaseArchiveHexID
from bpy_extras.io_utils import ImportHelper

from stingray.hashing import GetArchiveNameFromID

# pyright: reportInvalidTypeForm=false

class DefaultLoadArchiveOperator(Operator):
    bl_label = "Default Archive"
    bl_description = "Loads the Default Archive that Patches should be built upon"
    bl_idname = "helldiver2.archive_import_default"

    def execute(self, context):
        path = Global_gamepath + BaseArchiveHexID
        if not os.path.exists(path):
            self.report({'ERROR'}, "Current Filepath is Invalid. Change this in the Settings")
            context.scene.Hd2ToolPanelSettings.MenuExpanded = True
            return{'CANCELLED'}
        Global_TocManager.LoadArchive(path, True, False)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}
      
class LoadArchiveOperator(Operator, ImportHelper):
    bl_label = "Manually Load Archive"
    bl_idname = "helldiver2.archive_import"
    bl_description = "Loads a Selected Archive from Helldivers Data Folder"

    files: CollectionProperty(type=bpy.types.OperatorFileListElement,options={"HIDDEN", "SKIP_SAVE"})
    is_patch: BoolProperty(name="is_patch", default=False, options={'HIDDEN'})
    #files = CollectionProperty(name='File paths', type=bpy.types.PropertyGroup)

    def __init__(self):
        self.filepath = bpy.path.abspath(Global_gamepath)

    def execute(self, context):
        # Sanitize path by removing any provided extension, so the correct TOC file is loaded
        if not self.is_patch:
            filepaths = [Global_gamepath + f.name for f in self.files]
        else:
            filepaths = [self.filepath, ]
        oldLoadedLength = len(Global_TocManager.LoadedArchives)
        for filepath in filepaths:
            if not os.path.exists(filepath) or filepath.endswith(".ini") or filepath.endswith(".data"):
                continue
            path = Path(filepath)
            if not path.suffix.startswith(".patch_"): path = path.with_suffix("")

            archiveToc = Global_TocManager.LoadArchive(str(path), True, self.is_patch)
        PrettyPrint(f"Loaded {len(Global_TocManager.LoadedArchives) - oldLoadedLength} Archive(s)")

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

class LoadArchivesOperator(Operator):
    bl_label = "Load Archives"
    bl_idname = "helldiver2.archives_import"
    bl_description = "Loads Selected Archive"

    paths_str: StringProperty(name="paths_str")
    def execute(self, context):
        global Global_TocManager
        if self.paths_str != "" and os.path.exists(self.paths_str):
            Global_TocManager.LoadArchive(self.paths_str)
            id = self.paths_str.replace(Global_gamepath, "")
            name = f"{GetArchiveNameFromID(id)} {id}"
            self.report({'INFO'}, f"Loaded {name}")
            return{'FINISHED'}
        else:
            message = "Archive Failed to Load"
            if not os.path.exists(self.paths_str):
                message = "Current Filepath is Invalid. Change This in Settings"
            self.report({'ERROR'}, message )
            return{'CANCELLED'}

class UnloadArchivesOperator(Operator):
    bl_label = "Unload Archives"
    bl_idname = "helldiver2.archive_unloadall"
    bl_description = "Unloads All Current Loaded Archives"

    def execute(self, context):
        Global_TocManager.UnloadArchives()
        return{'FINISHED'}
