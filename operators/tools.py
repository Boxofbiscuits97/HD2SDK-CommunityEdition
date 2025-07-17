import datetime
import bpy

from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import BoolProperty, StringProperty
from __init__ import PrettyPrint, Global_gamepath, Global_TocManager, BaseArchiveHexID, Global_ArchiveHashes
from operators.filepath import Global_searchpath
from stingray.hashing import hex_to_decimal

# pyright: reportInvalidTypeForm=false

class BulkLoadOperator(Operator, ImportHelper):
    bl_label = "Bulk Loader"
    bl_idname = "helldiver2.bulk_load"
    bl_description = "Loads archives from a list of patch names in a text file"

    open_file_browser: BoolProperty(default=True, options={'HIDDEN'})
    file: StringProperty(options={'HIDDEN'})
    
    filter_glob: StringProperty(options={'HIDDEN'}, default='*.txt')

    def execute(self, context):
        self.file = self.filepath
        f = open(self.file, "r")
        entries = f.read().splitlines()
        numEntries = len(entries)
        PrettyPrint(f"Loading {numEntries} Archives")
        numArchives = len(Global_TocManager.LoadedArchives)
        entryList = (Global_gamepath + entry.split(" ")[0] for entry in entries)
        Global_TocManager.BulkLoad(entryList)
        numArchives = len(Global_TocManager.LoadedArchives) - numArchives
        numSkipped = numEntries - numArchives
        PrettyPrint(f"Loaded {numArchives} Archives. Skipped {numSkipped} Archives")
        PrettyPrint(f"{len(entries)} {entries}")
        archivesList = (archive.Name for archive in Global_TocManager.LoadedArchives)
        for item in archivesList:
            if item in entries:
                PrettyPrint(f"Switching To First Loaded Archive: {item}")
                bpy.context.scene.Hd2ToolPanelSettings.LoadedArchives = item
                break
        return{'FINISHED'}

class SearchByEntryIDOperator(Operator, ImportHelper):
    bl_label = "Search By Entry ID"
    bl_idname = "helldiver2.search_by_entry"
    bl_description = "Search for Archives by their contained Entry IDs"

    filter_glob: StringProperty(options={'HIDDEN'}, default='*.txt')

    def execute(self, context):
        baseArchivePath = Global_gamepath + BaseArchiveHexID
        Global_TocManager.LoadArchive(baseArchivePath)
        
        findme = open(self.filepath, "r")
        fileIDs = findme.read().splitlines()
        findme.close()

        archives = []
        PrettyPrint(f"Searching for {len(fileIDs)} IDs")
        for fileID in fileIDs:
            ID = fileID.split()[0]
            try:
                name = fileID.split(" ", 1)[1]
            except:
                name = None
            if ID.upper() != ID.lower():
                ID = hex_to_decimal(ID)
            ID = int(ID)
            PrettyPrint(f"Searching for ID: {ID}")
            for Archive in Global_TocManager.SearchArchives:
                PrettyPrint(f"Searching Archive: {Archive.Name}")
                if ID in Archive.fileIDs:
                    PrettyPrint(f"Found ID: {ID} in Archive: {Archive.Name}")
                    item = f"{Archive.Name} {ID} {name}"
                    archives.append(item)

                    if bpy.context.scene.Hd2ToolPanelSettings.LoadFoundArchives:
                        Global_TocManager.LoadArchive(Archive.Path)
        curenttime = str(datetime.datetime.now()).replace(":", "-").replace(".", "_")
        outputfile = f"{Global_searchpath}output_{curenttime}.txt"
        PrettyPrint(f"Found {len(archives)} archives")
        output = open(outputfile, "w")
        for item in archives:
            PrettyPrint(item)
            output.write(item + "\n")
        output.close()
        self.report({'INFO'}, f"Found {len(archives)} archives with matching IDs.")
        PrettyPrint(f"Output file created at: {outputfile}")
        return {'FINISHED'}

class NextArchiveOperator(Operator):
    bl_label = "Next Archive"
    bl_idname = "helldiver2.next_archive"
    bl_description = "Select the next archive in the list of loaded archives"

    def execute(self, context):
        for index in range(len(Global_TocManager.LoadedArchives)):
            if Global_TocManager.LoadedArchives[index] == Global_TocManager.ActiveArchive:
                nextIndex = min(len(Global_TocManager.LoadedArchives) - 1, index + 1)
                bpy.context.scene.Hd2ToolPanelSettings.LoadedArchives = Global_TocManager.LoadedArchives[nextIndex].Name
                return {'FINISHED'}
        return {'CANCELLED'}
    