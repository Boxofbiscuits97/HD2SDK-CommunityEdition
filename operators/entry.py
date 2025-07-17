import subprocess
import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from __init__ import CompositeMeshID, Global_TocManager, MaterialID, MeshID, PrettyPrint, TexID, Global_Foldouts
from displaydata import GetDisplayData
from errorchecking import PatchesNotLoaded
from stingray.archives.tocmanager import EntriesFromStrings, IDsFromString
from stingray.hashing import AddFriendlyName, Hash64, RandomHash16

# pyright: reportInvalidTypeForm=false

class ArchiveEntryOperator(Operator):
    bl_label  = "Archive Entry"
    bl_idname = "helldiver2.archive_entry"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        return{'FINISHED'}

    def invoke(self, context, event):
        Entry = Global_TocManager.GetEntry(int(self.object_id), int(self.object_typeid))
        if event.ctrl:
            if Entry.IsSelected:
                Global_TocManager.DeselectEntries([Entry])
            else:
                Global_TocManager.SelectEntries([Entry], True)
            return {'FINISHED'}
        if event.shift:
            if Global_TocManager.LastSelected != None:
                LastSelected = Global_TocManager.LastSelected
                StartIndex   = LastSelected.DEV_DrawIndex
                EndIndex     = Entry.DEV_DrawIndex
                Global_TocManager.DeselectAll()
                Global_TocManager.LastSelected = LastSelected
                if StartIndex > EndIndex:
                    Global_TocManager.SelectEntries(Global_TocManager.DrawChain[EndIndex:StartIndex+1], True)
                else:
                    Global_TocManager.SelectEntries(Global_TocManager.DrawChain[StartIndex:EndIndex+1], True)
            else:
                Global_TocManager.SelectEntries([Entry], True)
            return {'FINISHED'}

        Global_TocManager.SelectEntries([Entry])
        return {'FINISHED'}
    

class AddEntryToPatchOperator(Operator):
    bl_label = "Add To Patch"
    bl_idname = "helldiver2.archive_addtopatch"
    bl_description = "Adds Entry into Patch"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        if PatchesNotLoaded(self):
            return{'CANCELLED'}
        
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            Global_TocManager.AddEntryToPatch(Entry.FileID, Entry.TypeID)
        return{'FINISHED'}


class RemoveEntryFromPatchOperator(Operator):
    bl_label = "Remove Entry From Patch"
    bl_idname = "helldiver2.archive_removefrompatch"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            Global_TocManager.RemoveEntryFromPatch(Entry.FileID, Entry.TypeID)
        return{'FINISHED'}


class UndoArchiveEntryModOperator(Operator):
    bl_label = "Remove Modifications"
    bl_idname = "helldiver2.archive_undo_mod"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            if Entry != None:
                Entry.UndoModifiedData()
        return{'FINISHED'}


class DuplicateEntryOperator(Operator):
    bl_label = "Duplicate Entry"
    bl_idname = "helldiver2.archive_duplicate"
    bl_description = "Duplicate Selected Entry"

    NewFileID : StringProperty(name="NewFileID", default="")
    def draw(self, context):
        global Global_randomID
        PrettyPrint(f"Got ID: {Global_randomID}")
        self.NewFileID = Global_randomID
        layout = self.layout; row = layout.row()
        row.operator("helldiver2.generate_random_id", icon="FILE_REFRESH")
        row = layout.row()
        row.prop(self, "NewFileID", icon='COPY_ID')

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        global Global_randomID
        if Global_TocManager.ActivePatch == None:
            Global_randomID = ""
            self.report({'ERROR'}, "No Patches Currently Loaded")
            return {'CANCELLED'}
        if self.NewFileID == "":
            self.report({'ERROR'}, "No ID was given")
            return {'CANCELLED'}
        Global_TocManager.DuplicateEntry(int(self.object_id), int(self.object_typeid), int(self.NewFileID))
        Global_randomID = ""
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    

class GenerateEntryIDOperator(Operator):
    bl_label = "Generate Random ID"
    bl_idname = "helldiver2.generate_random_id"
    bl_description = "Generates a random ID for the entry"

    def execute(self, context):
        global Global_randomID
        Global_randomID = str(RandomHash16())
        PrettyPrint(f"Generated random ID: {Global_randomID}")
        return{'FINISHED'}


class RenamePatchEntryOperator(Operator):
    bl_label = "Rename Entry"
    bl_idname = "helldiver2.archive_entryrename"

    NewFileID : StringProperty(name="NewFileID", default="")
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewFileID", icon='COPY_ID')

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entry = Global_TocManager.GetPatchEntry_B(int(self.object_id), int(self.object_typeid))
        if Entry == None:
            raise Exception("Entry does not exist in patch (cannot rename non patch entries)")
        if Entry != None and self.NewFileID != "":
            Entry.FileID = int(self.NewFileID)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
            
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class EntrySectionOperator(Operator):
    bl_label = "Collapse Section"
    bl_idname = "helldiver2.collapse_section"
    bl_description = "Fold Current Section"

    type: StringProperty(default = "")

    def execute(self, context):
        global Global_Foldouts
        for i in range(len(Global_Foldouts)):
            if Global_Foldouts[i][0] == str(self.type):
                Global_Foldouts[i][1] = not Global_Foldouts[i][1]
                PrettyPrint(f"Folding foldout: {Global_Foldouts[i]}")
        return {'FINISHED'}


class SelectAllOfTypeOperator(Operator):
    bl_label  = "Select All"
    bl_idname = "helldiver2.select_type"
    bl_description = "Selects All of Type in Section"

    object_typeid: StringProperty()
    def execute(self, context):
        Entries = GetDisplayData()[0]
        for EntryInfo in Entries:
            Entry = EntryInfo[0]
            if Entry.TypeID == int(self.object_typeid):
                DisplayEntry = Global_TocManager.GetEntry(Entry.FileID, Entry.TypeID)
                if DisplayEntry.IsSelected:
                    #Global_TocManager.DeselectEntries([Entry])
                    pass
                else:
                    Global_TocManager.SelectEntries([Entry], True)
        return{'FINISHED'}
    

class ImportAllOfTypeOperator(Operator):
    bl_label  = "Import All Of Type"
    bl_idname = "helldiver2.import_type"

    object_typeid: StringProperty()
    def execute(self, context):
        Entries = GetDisplayData()[0]
        for EntryInfo in Entries:
            Entry = EntryInfo[0]
            #if Entry.TypeID == int(self.object_typeid):
            DisplayEntry = Global_TocManager.GetEntry(Entry.FileID, Entry.TypeID)
            objectid = str(DisplayEntry.FileID)

            if DisplayEntry.TypeID == MeshID or DisplayEntry.TypeID == CompositeMeshID:
                EntriesIDs = IDsFromString(objectid)
                for EntryID in EntriesIDs:
                    try:
                        Global_TocManager.Load(EntryID, MeshID)
                    except Exception as error:
                        self.report({'ERROR'},[EntryID, error])

            elif DisplayEntry.TypeID == TexID:
                print("tex")
                #operator = bpy.ops.helldiver2.texture_import(object_id=objectid)
                #ImportTextureOperator.execute(operator, operator)

            elif DisplayEntry.TypeID == MaterialID:
                print("mat")
                #operator = bpy.ops.helldiver2.material_import(object_id=objectid)
                #ImportMaterialOperator.execute(operator, operator)
        return{'FINISHED'}


class SetEntryFriendlyNameOperator(Operator):
    bl_label = "Set Friendly Name"
    bl_idname = "helldiver2.archive_setfriendlyname"
    bl_description = "Change Entry Display Name"

    NewFriendlyName : StringProperty(name="NewFriendlyName", default="")
    def draw(self, context):
        layout = self.layout; row = layout.row()
        row.prop(self, "NewFriendlyName", icon='COPY_ID')
        row = layout.row()
        if Hash64(str(self.NewFriendlyName)) == int(self.object_id):
            row.label(text="Hash is correct")
        else:
            row.label(text="Hash is incorrect")
        row.label(text=str(Hash64(str(self.NewFriendlyName))))

    object_id: StringProperty()
    def execute(self, context):
        AddFriendlyName(int(self.object_id), str(self.NewFriendlyName))
        return{'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class CopyArchiveEntryOperator(Operator):
    bl_label = "Copy Entry"
    bl_idname = "helldiver2.archive_copy"
    bl_description = "Copy Selected Entries"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        Global_TocManager.Copy(Entries)
        return{'FINISHED'}


class PasteArchiveEntryOperator(Operator):
    bl_label = "Paste Entry"
    bl_idname = "helldiver2.archive_paste"
    bl_description = "Paste Selected Entries"

    def execute(self, context):
        Global_TocManager.Paste()
        return{'FINISHED'}


class ClearClipboardOperator(Operator):
    bl_label = "Clear Clipboard"
    bl_idname = "helldiver2.archive_clearclipboard"
    bl_description = "Clear Selected Entries from Clipboard"

    def execute(self, context):
        Global_TocManager.ClearClipboard()
        return{'FINISHED'}


class CopyTextOperator(Operator):
    bl_label  = "Copy ID"
    bl_idname = "helldiver2.copytest"
    bl_description = "Copies Entry Information"

    text: StringProperty()
    def execute(self, context):
        bpy.context.window_manager.clipboard = self.text
        return{'FINISHED'}