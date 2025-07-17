import os
import bpy

from bpy.types import Operator, OperatorFileListElement
from bpy.props import CollectionProperty, BoolProperty, StringProperty
from __init__ import PrettyPrint, Global_TocManager
from errorchecking import PatchesNotLoaded
from stingray.archives.tocentry import TocEntry
from stingray.archives.tocmanager import EntriesFromStrings
from stingray.hashing import GetIDFromTypeName, GetTypeNameFromID
from bpy_extras.io_utils import ImportHelper

# pyright: reportInvalidTypeForm=false

class DumpArchiveObjectOperator(Operator):
    bl_label = "Dump Archive Object"
    bl_idname = "helldiver2.archive_object_dump_export"
    bl_description = "Dumps Entry's Contents"

    directory: StringProperty(name="Outdir Path",description="dump output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    object_typeid: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            if Entry != None:
                data = Entry.GetData()
                FileName = str(Entry.FileID)+"."+GetTypeNameFromID(Entry.TypeID)
                with open(self.directory + FileName, 'w+b') as f:
                    f.write(data[0])
                if data[1] != b"":
                    with open(self.directory + FileName+".gpu", 'w+b') as f:
                        f.write(data[1])
                if data[2] != b"":
                    with open(self.directory + FileName+".stream", 'w+b') as f:
                        f.write(data[2])
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ImportDumpOperator(Operator, ImportHelper):
    bl_label = "Import Dump"
    bl_idname = "helldiver2.archive_object_dump_import"
    bl_description = "Loads Raw Dump"

    object_id: StringProperty(options={"HIDDEN"})
    object_typeid: StringProperty(options={"HIDDEN"})

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}

        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            ImportDump(self, Entry, self.filepath)

        return{'FINISHED'}

class ImportDumpByIDOperator(Operator, ImportHelper):
    bl_label = "Import Dump by Entry ID"
    bl_idname = "helldiver2.archive_object_dump_import_by_id"
    bl_description = "Loads Raw Dump over matching entry IDs"

    directory: StringProperty(subtype='FILE_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    files: CollectionProperty(type=OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}

        for file in self.files:
            filepath = self.directory + file.name
            fileID = file.name.split('.')[0]
            typeString = file.name.split('.')[1]
            typeID = GetIDFromTypeName(typeString)

            if typeID == None:
                self.report({'ERROR'}, f"File: {file.name} has no proper file extension for typing")
                return {'CANCELLED'}
            
            if os.path.exists(filepath):
                PrettyPrint(f"Found file: {filepath}")
            else:
                self.report({'ERROR'}, f"Filepath for selected file: {filepath} was not found")
                return {'CANCELLED'}

            entry = Global_TocManager.GetEntryByLoadArchive(int(fileID), int(typeID))
            if entry == None:
                self.report({'ERROR'}, f"Entry for fileID: {fileID} typeID: {typeID} can not be found. Make sure the fileID of your file is correct.")
                return {'CANCELLED'}
            
            ImportDump(self, entry, filepath)
            
        return{'FINISHED'}

def ImportDump(self: Operator, Entry: TocEntry, filepath: str):
    if Entry != None:
        if not Entry.IsLoaded: Entry.Load(False, False)
        path = filepath
        GpuResourchesPath = f"{path}.gpu"
        StreamPath = f"{path}.stream"

        with open(path, 'r+b') as f:
            Entry.TocData = f.read()

        if os.path.isfile(GpuResourchesPath):
            with open(GpuResourchesPath, 'r+b') as f:
                Entry.GpuData = f.read()
        else:
            Entry.GpuData = b""

        if os.path.isfile(StreamPath):
            with open(StreamPath, 'r+b') as f:
                Entry.StreamData = f.read()
        else:
            Entry.StreamData = b""

        Entry.IsModified = True
        if not Global_TocManager.IsInPatch(Entry):
            Global_TocManager.AddEntryToPatch(Entry.FileID, Entry.TypeID)
            
        self.report({'INFO'}, f"Imported Raw Dump: {path}")