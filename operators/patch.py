import os
import shutil
import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from __init__ import Global_TocManager, Global_backslash, Global_gamepath, BaseArchiveHexID, PrettyPrint
from errorchecking import ArchivesNotLoaded, PatchesNotLoaded
from bpy_extras.io_utils import ExportHelper

# pyright: reportInvalidTypeForm=false

class CreatePatchFromActiveOperator(Operator):
    bl_label = "Create Patch"
    bl_idname = "helldiver2.archive_createpatch"
    bl_description = "Creates Patch from Current Active Archive"

    def execute(self, context):
        
        if bpy.context.scene.Hd2ToolPanelSettings.PatchBaseArchiveOnly:
            baseArchivePath = Global_gamepath + BaseArchiveHexID
            Global_TocManager.LoadArchive(baseArchivePath)
            Global_TocManager.SetActiveByName(BaseArchiveHexID)
        else:
            self.report({'WARNING'}, f"Patch Created Was Not From Base Archive.")
        
        if ArchivesNotLoaded(self):
            return{'CANCELLED'}
        
        Global_TocManager.CreatePatchFromActive()

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}
    

class PatchArchiveOperator(Operator):
    bl_label = "Patch Archive"
    bl_idname = "helldiver2.archive_export"
    bl_description = "Writes Patch to Current Active Patch"

    def execute(self, context):
        global Global_TocManager
        if PatchesNotLoaded(self):
            return{'CANCELLED'}
        
        
        #bpy.ops.wm.save_as_mainfile(filepath=)
        
        if bpy.context.scene.Hd2ToolPanelSettings.SaveUnsavedOnWrite:
            SaveUnsavedEntries(self)
        Global_TocManager.PatchActiveArchive()
        self.report({'INFO'}, f"Patch Written")
        return{'FINISHED'}


class RenamePatchOperator(Operator):
    bl_label = "Rename Mod"
    bl_idname = "helldiver2.rename_patch"
    bl_description = "Change Name of Current Mod Within the Tool"

    patch_name: StringProperty(name="Mod Name")

    def execute(self, context):
        if PatchesNotLoaded(self):
            return{'CANCELLED'}
        
        Global_TocManager.ActivePatch.LocalName = self.patch_name

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}
    
    def invoke(self, context, event):
        if Global_TocManager.ActiveArchive == None:
            self.report({"ERROR"}, "No patch exists, please create one first")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "patch_name")


class ExportPatchAsZipOperator(Operator, ExportHelper):
    bl_label = "Export Patch"
    bl_idname = "helldiver2.export_patch"
    bl_description = "Exports the Current Active Patch as a Zip File"
    
    filename_ext = ".zip"
    use_filter_folder = True
    filter_glob: StringProperty(default='*.zip', options={'HIDDEN'})

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        
        filepath = self.properties.filepath
        outputFilename = filepath.replace(".zip", "")
        exportname = filepath.split(Global_backslash)[-1]
        
        patchName = Global_TocManager.ActivePatch.Name
        tempPatchFolder = bpy.app.tempdir + "patchExport\\"
        tempPatchFile = f"{tempPatchFolder}\{patchName}"
        PrettyPrint(f"Exporting in temp folder: {tempPatchFolder}")

        if not os.path.exists(tempPatchFolder):
            os.makedirs(tempPatchFolder)
        Global_TocManager.ActivePatch.ToFile(tempPatchFile)
        shutil.make_archive(outputFilename, 'zip', tempPatchFolder)
        for file in os.listdir(tempPatchFolder):
            path = f"{tempPatchFolder}\{file}"
            os.remove(path)
        os.removedirs(tempPatchFolder)

        if os.path.exists(filepath):
            self.report({'INFO'}, f"{patchName} Exported Successfully As {exportname}")
        else: 
            self.report({'ERROR'}, f"Failed to Export {patchName}")

        return {'FINISHED'}


class UnloadPatchesOperator(Operator):
    bl_label = "Unload Patches"
    bl_idname = "helldiver2.patches_unloadall"
    bl_description = "Unloads All Current Loaded Patches"

    def execute(self, context):
        Global_TocManager.UnloadPatches()
        return{'FINISHED'}



def SaveUnsavedEntries(self):
    for Entry in Global_TocManager.ActivePatch.TocEntries:
        if not Entry.IsModified:
            Global_TocManager.Save(int(Entry.FileID), Entry.TypeID)
            PrettyPrint(f"Saved {int(Entry.FileID)}")