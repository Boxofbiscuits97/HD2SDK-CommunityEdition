import os
import bpy

from pathlib import Path
from __init__ import Global_TocManager, PrettyPrint, MeshID


def RepatchMeshes(self, path):
    if len(bpy.context.scene.objects) > 0:
        self.report({'ERROR'}, f"Scene is not empty! Please remove all objects in the scene before starting the repatching process!")
        return{'CANCELLED'}
    
    Global_TocManager.UnloadPatches()
    
    settings = bpy.context.scene.Hd2ToolPanelSettings
    settings.ImportLods = False
    settings.AutoLods = True
    settings.ImportStatic = False
    
    PrettyPrint(f"Searching for patch files in: {path}")
    patchPaths = []
    LoopPatchPaths(patchPaths, path)
    PrettyPrint(f"Found Patch Paths: {patchPaths}")
    if len(patchPaths) == 0:
        self.report({'ERROR'}, f"No patch files were found in selected path")
        return{'ERROR'}

    errors = []
    for path in patchPaths:
        PrettyPrint(f"Patching: {path}")
        Global_TocManager.LoadArchive(path, True, True)
        numMeshesRepatched = 0
        failed = False
        for entry in Global_TocManager.ActivePatch.TocEntries:
            if entry.TypeID != MeshID:
                PrettyPrint(f"Skipping {entry.FileID} as it is not a mesh entry")
                continue
            PrettyPrint(f"Repatching {entry.FileID}")
            Global_TocManager.GetEntryByLoadArchive(entry.FileID, entry.TypeID)
            settings.AutoLods = True
            settings.ImportStatic = False
            numMeshesRepatched += 1
            entry.Load(False, True)
            patchObjects = bpy.context.scene.objects
            if len(patchObjects) == 0: # Handle static meshes
                settings.AutoLods = False
                settings.ImportStatic = True
                entry.Load(False, True)
                patchObjects = bpy.context.scene.objects
            OldMeshInfoIndex = patchObjects[0]['MeshInfoIndex']
            fileID = entry.FileID
            typeID = entry.TypeID
            Global_TocManager.RemoveEntryFromPatch(fileID, typeID)
            Global_TocManager.AddEntryToPatch(fileID, typeID)
            newEntry = Global_TocManager.GetEntry(fileID, typeID)
            if newEntry:
                PrettyPrint(f"Entry successfully created")
            else:
                failed = True
                errors.append([path, fileID, "Could not create newEntry", "error"])
                continue
            newEntry.Load(False, False)
            NewMeshes = newEntry.LoadedData.RawMeshes
            NewMeshInfoIndex = ""
            for mesh in NewMeshes:
                if mesh.LodIndex == 0:
                    NewMeshInfoIndex = mesh.MeshInfoIndex
            if NewMeshInfoIndex == "": # if the index is still a string, we couldn't find it
                PrettyPrint(f"Could not find LOD 0 for mesh: {fileID}. Skipping mesh index checks", "warn")
                errors.append([path, fileID, "Could not find LOD 0 for mesh so LOD index updates did not occur. This may be intended", "warn"])
            else:
                PrettyPrint(f"Old MeshIndex: {OldMeshInfoIndex} New MeshIndex: {NewMeshInfoIndex}")
                if OldMeshInfoIndex != NewMeshInfoIndex:
                    PrettyPrint(f"Swapping mesh index to new index", "warn")
                    patchObjects[0]['MeshInfoIndex'] = NewMeshInfoIndex
            for object in patchObjects:
                object.select_set(True)
            newEntry.Save()
            for object in bpy.context.scene.objects:
                bpy.data.objects.remove(object)

        if not failed:
            Global_TocManager.PatchActiveArchive()
            PrettyPrint(f"Repatched {numMeshesRepatched} meshes in patch: {path}")
        else:
            PrettyPrint(f"Faield to repatch meshes in patch: {path}", "error")
        Global_TocManager.UnloadPatches()
    
    if len(errors) == 0:
        PrettyPrint(f"Finished repatching {len(patchPaths)} modsets")
        self.report({'INFO'}, f"Finished Repatching meshes with no errors")
    else:
        for error in errors:
            PrettyPrint(f"Failed to patch mesh: {error[1]} in patch: {error[0]} Error: {error[2]}", error[3])
        self.report({'ERROR'}, f"Failed to patch {len(errors)} meshes. Please check logs to see the errors")

def LoopPatchPaths(list, filepath):
    for path in os.listdir(filepath):
        path = f"{filepath}\{path}"
        if Path(path).is_dir():
            PrettyPrint(f"Looking in folder: {path}")
            LoopPatchPaths(list, path)
            continue
        if "patch_" in path:
            PrettyPrint(f"Adding Path: {path}")
            strippedpath = path.replace(".gpu_resources", "").replace(".stream", "")
            if strippedpath not in list:
                list.append(strippedpath)
        else:
            PrettyPrint(f"Path: {path} is not a patch file. Ignoring file.", "warn")
