import concurrent
from copy import deepcopy
import os
import bpy

from pathlib import Path
from memoryStream import MemoryStream
from stingray.archives.streamtoc import StreamToc
from stingray.archives.searchtoc import SearchToc
from stingray.hashing import GetArchiveNameFromID, RandomHash16
from __init__ import CompositeMeshID, MaterialID, MeshID, PrettyPrint, Global_TocManager, Global_gamepath, TexID
from stingray.material import Global_MaterialParentIDs

class TocManager():
    def __init__(self):
        self.SearchArchives  = []
        self.LoadedArchives  = []
        self.ActiveArchive   = None
        self.Patches         = []
        self.ActivePatch     = None

        self.CopyBuffer      = []
        self.SelectedEntries = []
        self.DrawChain       = []
        self.LastSelected = None # Last Entry Manually Selected
        self.SavedFriendlyNames   = []
        self.SavedFriendlyNameIDs = []
    #________________________________#
    # ---- Entry Selection Code ---- #
    def SelectEntries(self, Entries, Append=False):
        if not Append: self.DeselectAll()
        if len(Entries) == 1:
            Global_TocManager.LastSelected = Entries[0]

        for Entry in Entries:
            if Entry not in self.SelectedEntries:
                Entry.IsSelected = True
                self.SelectedEntries.append(Entry)
    def DeselectEntries(self, Entries):
        for Entry in Entries:
            Entry.IsSelected = False
            if Entry in self.SelectedEntries:
                self.SelectedEntries.remove(Entry)
    def DeselectAll(self):
        for Entry in self.SelectedEntries:
            Entry.IsSelected = False
        self.SelectedEntries = []
        self.LastSelected = None

    #________________________#
    # ---- Archive Code ---- #
    def LoadArchive(self, path, SetActive=True, IsPatch=False):
        # TODO: Add error if IsPatch is true but the path is not to a patch

        for Archive in self.LoadedArchives:
            if Archive.Path == path:
                return Archive
        archiveID = path.replace(Global_gamepath, '')
        archiveName = GetArchiveNameFromID(archiveID)
        PrettyPrint(f"Loading Archive: {archiveID} {archiveName}")
        toc = StreamToc()
        toc.FromFile(path)
        if SetActive and not IsPatch:
            unloadEmpty = bpy.context.scene.Hd2ToolPanelSettings.UnloadEmptyArchives and bpy.context.scene.Hd2ToolPanelSettings.EnableTools
            if unloadEmpty:
                if self.ArchiveNotEmpty(toc):
                    self.LoadedArchives.append(toc)
                    self.ActiveArchive = toc
                else:
                    PrettyPrint(f"Unloading {archiveID} as it is Empty")
            else:
                self.LoadedArchives.append(toc)
                self.ActiveArchive = toc
                bpy.context.scene.Hd2ToolPanelSettings.LoadedArchives = archiveID
        elif SetActive and IsPatch:
            self.Patches.append(toc)
            self.ActivePatch = toc

            for entry in self.ActivePatch.TocEntries:
                if entry.TypeID == MaterialID:
                    ID = GetEntryParentMaterialID(entry)
                    if ID in Global_MaterialParentIDs:
                        entry.MaterialTemplate = Global_MaterialParentIDs[ID]
                        entry.Load()
                        PrettyPrint(f"Creating Material: {entry.FileID} Template: {entry.MaterialTemplate}")
                    else:
                        PrettyPrint(f"Material: {entry.FileID} Parent ID: {ID} is not an custom material, skipping.")
        else:
            self.LoadedArchives.append(toc)

        # Get search archives
        if len(self.SearchArchives) == 0:
            futures = []
            tocs = []
            executor = concurrent.futures.ThreadPoolExecutor()
            for root, dirs, files in os.walk(Path(path).parent):
                for name in files:
                    if Path(name).suffix == "":
                        search_toc = SearchToc()
                        tocs.append(search_toc)
                        futures.append(executor.submit(search_toc.FromFile, os.path.join(root, name)))
            for index, future in enumerate(futures):
                if future.result():
                    self.SearchArchives.append(tocs[index])
            executor.shutdown()

        return toc
    
    def GetEntryByLoadArchive(self, FileID: int, TypeID: int):
        return self.GetEntry(FileID, TypeID, SearchAll=True, IgnorePatch=True)
    
    def ArchiveNotEmpty(self, toc):
        hasMaterials = False
        hasTextures = False
        hasMeshes = False
        for Entry in toc.TocEntries:
            type = Entry.TypeID
            if type == MaterialID:
                hasMaterials = True
            elif type == MeshID:
                hasMeshes = True
            elif type == TexID:
                hasTextures = True
            elif type == CompositeMeshID:
                hasMeshes = True
        return hasMaterials or hasTextures or hasMeshes

    def UnloadArchives(self):
        # TODO: Make sure all data gets unloaded...
        # some how memory can still be too high after calling this
        self.LoadedArchives = []
        self.ActiveArchive  = None
        self.SearchArchives = []
    
    def UnloadPatches(self):
        self.Patches = []
        self.ActivePatch = None

    def BulkLoad(self, list):
        if bpy.context.scene.Hd2ToolPanelSettings.UnloadPatches:
            self.UnloadArchives()
        for itemPath in list:
            Global_TocManager.LoadArchive(itemPath)

    def SetActive(self, Archive):
        if Archive != self.ActiveArchive:
            self.ActiveArchive = Archive
            self.DeselectAll()

    def SetActiveByName(self, Name):
        for Archive in self.LoadedArchives:
            if Archive.Name == Name:
                self.SetActive(Archive)

    #______________________#
    # ---- Entry Code ---- #
    def GetEntry(self, FileID, TypeID, SearchAll=False, IgnorePatch=False):
        # Check Active Patch
        if not IgnorePatch and self.ActivePatch != None:
            Entry = self.ActivePatch.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check Active Archive
        if self.ActiveArchive != None:
            Entry = self.ActiveArchive.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check All Loaded Archives
        for Archive in self.LoadedArchives:
            Entry = Archive.GetEntry(FileID, TypeID)
            if Entry != None:
                return Entry
        # Check All Search Archives
        if SearchAll:
            for Archive in self.SearchArchives:
                if Archive.HasEntry(FileID, TypeID):
                    return self.LoadArchive(Archive.Path, False).GetEntry(FileID, TypeID)
        return None

    def Load(self, FileID, TypeID, Reload=False, SearchAll=False):
        Entry = self.GetEntry(FileID, TypeID, SearchAll)
        if Entry != None: Entry.Load(Reload)

    def Save(self, FileID, TypeID):
        Entry = self.GetEntry(FileID, TypeID)
        if Entry == None:
            PrettyPrint(f"Failed to save entry {FileID}")
            return False
        if not Global_TocManager.IsInPatch(Entry):
            Entry = self.AddEntryToPatch(FileID, TypeID)
        Entry.Save()
        return True

    def CopyPaste(self, Entry, GenID = False, NewID = None):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        if self.ActivePatch:
            dup = deepcopy(Entry)
            dup.IsCreated = True
            # if self.ActivePatch.GetEntry(dup.FileID, dup.TypeID) != None and NewID == None:
            #     GenID = True
            if GenID and NewID == None: dup.FileID = RandomHash16()
            if NewID != None:
                dup.FileID = NewID

            self.ActivePatch.AddEntry(dup)
    def Copy(self, Entries):
        self.CopyBuffer = []
        for Entry in Entries:
            if Entry != None: self.CopyBuffer.append(Entry)
    def Paste(self, GenID = False, NewID = None):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        if self.ActivePatch:
            for ToCopy in self.CopyBuffer:
                self.CopyPaste(ToCopy, GenID, NewID)
            self.CopyBuffer = []

    def ClearClipboard(self):
        self.CopyBuffer = []

    #______________________#
    # ---- Patch Code ---- #
    def PatchActiveArchive(self):
        self.ActivePatch.ToFile()

    def CreatePatchFromActive(self, name="New Patch"):
        if self.ActiveArchive == None:
            raise Exception("No Archive exists to create patch from, please open one first")

        self.ActivePatch = deepcopy(self.ActiveArchive)
        self.ActivePatch.TocEntries  = []
        self.ActivePatch.TocTypes    = []
        # TODO: ask for which patch index
        path = self.ActiveArchive.Path
        if path.find(".patch_") != -1:
            num = int(path[path.find(".patch_")+len(".patch_"):]) + 1
            path = path[:path.find(".patch_")] + ".patch_" + str(num)
        else:
            path += ".patch_0"
        self.ActivePatch.UpdatePath(path)
        self.ActivePatch.LocalName = name
        PrettyPrint(f"Creating Patch: {path}")
        self.Patches.append(self.ActivePatch)

    def SetActivePatch(self, Patch):
        self.ActivePatch = Patch

    def SetActivePatchByName(self, Name):
        for Patch in self.Patches:
            if Patch.Name == Name:
                self.SetActivePatch(Patch)

    def AddNewEntryToPatch(self, Entry):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")
        self.ActivePatch.AddEntry(Entry)

    def AddEntryToPatch(self, FileID, TypeID):
        if self.ActivePatch == None:
            raise Exception("No patch exists, please create one first")

        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            PatchEntry = deepcopy(Entry)
            if PatchEntry.IsSelected:
                self.SelectEntries([PatchEntry], True)
            self.ActivePatch.AddEntry(PatchEntry)
            return PatchEntry
        return None

    def RemoveEntryFromPatch(self, FileID, TypeID):
        if self.ActivePatch != None:
            self.ActivePatch.RemoveEntry(FileID, TypeID)
        return None

    def GetPatchEntry(self, Entry):
        if self.ActivePatch != None:
            return self.ActivePatch.GetEntry(Entry.FileID, Entry.TypeID)
        return None
    def GetPatchEntry_B(self, FileID, TypeID):
        if self.ActivePatch != None:
            return self.ActivePatch.GetEntry(FileID, TypeID)
        return None

    def IsInPatch(self, Entry):
        if self.ActivePatch != None:
            PatchEntry = self.ActivePatch.GetEntry(Entry.FileID, Entry.TypeID)
            if PatchEntry != None: return True
            else: return False
        return False

    def DuplicateEntry(self, FileID, TypeID, NewID):
        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            self.CopyPaste(Entry, False, NewID)

def EntriesFromStrings(file_id_string, type_id_string):
    FileIDs = file_id_string.split(',')
    TypeIDs = type_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(Global_TocManager.GetEntry(int(FileIDs[n]), int(TypeIDs[n])))
    return Entries

def EntriesFromString(file_id_string, TypeID):
    FileIDs = file_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(Global_TocManager.GetEntry(int(FileIDs[n]), int(TypeID)))
    return Entries

def IDsFromString(file_id_string):
    FileIDs = file_id_string.split(',')
    Entries = []
    for n in range(len(FileIDs)):
        if FileIDs[n] != "":
            Entries.append(int(FileIDs[n]))
    return Entries

def GetEntryParentMaterialID(entry):
    if entry.TypeID == MaterialID:
        f = MemoryStream(entry.TocData)
        for i in range(6):
            f.uint32(0)
        parentID = f.uint64(0)
        return parentID
    else:
        raise Exception(f"Entry: {entry.FileID} is not a material")