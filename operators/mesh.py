import time
import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from __init__ import MaterialID, MeshID, PrettyPrint, Global_TocManager
from blenderfunctions import GetObjectsMeshData
from errorchecking import MeshNotValidToSave
from operators.material import CreateModdedMaterial
from stingray.archives.tocmanager import IDsFromString

# pyright: reportInvalidTypeForm=false

class ImportStingrayMeshOperator(Operator):
    bl_label = "Import Archive Mesh"
    bl_idname = "helldiver2.archive_mesh_import"
    bl_description = "Loads Mesh into Blender Scene"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        Errors = []
        for EntryID in EntriesIDs:
            if len(EntriesIDs) == 1:
                Global_TocManager.Load(EntryID, MeshID)
            else:
                try:
                    Global_TocManager.Load(EntryID, MeshID)
                except Exception as error:
                    Errors.append([EntryID, error])

        if len(Errors) > 0:
            PrettyPrint("\nThese errors occurred while attempting to load meshes...", "error")
            idx = 0
            for error in Errors:
                PrettyPrint(f"  Error {idx}: for mesh {error[0]}", "error")
                PrettyPrint(f"    {error[1]}\n", "error")
                idx += 1
            raise Exception("One or more meshes failed to load")
        return{'FINISHED'}

class SaveStingrayMeshOperator(Operator):
    bl_label  = "Save Mesh"
    bl_idname = "helldiver2.archive_mesh_save"
    bl_description = "Saves Mesh"
    bl_options = {'REGISTER', 'UNDO'} 

    object_id: StringProperty()
    def execute(self, context):
        mode = context.mode
        if mode != 'OBJECT':
            self.report({'ERROR'}, f"You are Not in OBJECT Mode. Current Mode: {mode}")
            return {'CANCELLED'}
        if MeshNotValidToSave(self):
            return {'CANCELLED'}
        object = None
        object = bpy.context.active_object
        if object == None:
            self.report({"ERROR"}, "No Object selected. Please select the object to be saved.")
            return {'CANCELLED'}
        try:
            ID = object["Z_ObjectID"]
        except:
            self.report({'ERROR'}, f"{object.name} has no HD2 custom properties")
            return{'CANCELLED'}
        SwapID = ""
        try:
            SwapID = object["Z_SwapID"]
            if SwapID != "" and not SwapID.isnumeric():
                self.report({"ERROR"}, f"Object: {object.name} has an incorrect Swap ID. Assure that the ID is a proper integer entry ID.")
                return {'CANCELLED'}
        except:
            self.report({'INFO'}, f"{object.name} has no HD2 Swap ID. Skipping Swap.")
        model = GetObjectsMeshData()
        BlenderOpts = bpy.context.scene.Hd2ToolPanelSettings.get_settings_dict()
        Entry = Global_TocManager.GetEntryByLoadArchive(int(ID), MeshID)
        if Entry is None:
            self.report({'ERROR'},
                f"Archive for entry being saved is not loaded. Could not find custom property object at ID: {ID}")
            return{'CANCELLED'}
        if not Entry.IsLoaded: Entry.Load(True, False)
        m = model[ID]
        meshes = model[ID]
        for mesh_index, mesh in meshes.items():
            try:
                Entry.LoadedData.RawMeshes[mesh_index] = mesh
            except IndexError:
                self.report({'ERROR'}, f"MeshInfoIndex for {object.name} exceeds the number of meshes")
                return{'CANCELLED'}
        for mesh_index, mesh in meshes.items():
            try:
                if Entry.LoadedData.RawMeshes[mesh_index].DEV_BoneInfoIndex == -1 and object[
                    'BoneInfoIndex'] > -1:
                    self.report({'ERROR'},
                                f"Attempting to overwrite static mesh with {object[0].name}"
                                f", which has bones. Check your MeshInfoIndex is correct.")
                    return{'CANCELLED'}
                Entry.LoadedData.RawMeshes[mesh_index] = mesh
            except IndexError:
                self.report({'ERROR'},
                            f"MeshInfoIndex for {object[0].name} exceeds the number of meshes")
                return{'CANCELLED'}
        wasSaved = Entry.Save(BlenderOpts=BlenderOpts)
        if wasSaved:
            if not Global_TocManager.IsInPatch(Entry):
                Entry = Global_TocManager.AddEntryToPatch(int(ID), MeshID)
        else:
            self.report({"ERROR"}, f"Failed to save mesh {bpy.context.selected_objects[0].name}.")
            return{'CANCELLED'}
        self.report({'INFO'}, f"Saved Mesh Object ID: {self.object_id}")
        if SwapID != "" and SwapID.isnumeric():
                self.report({'INFO'}, f"Swapping Entry ID: {Entry.FileID} to: {SwapID}")
                Global_TocManager.RemoveEntryFromPatch(int(SwapID), MeshID)
                Entry.FileID = int(SwapID)
        return{'FINISHED'}

class BatchSaveStingrayMeshOperator(Operator):
    bl_label  = "Save Meshes"
    bl_idname = "helldiver2.archive_mesh_batchsave"
    bl_description = "Saves Meshes"
    bl_options = {'REGISTER', 'UNDO'} 

    def execute(self, context):
        start = time.time()
        errors = False
        if MeshNotValidToSave(self):
            return {'CANCELLED'}

        objects = bpy.context.selected_objects
        num_initially_selected = len(objects)

        if len(objects) == 0:
            self.report({'WARNING'}, "No Objects Selected")
            return {'CANCELLED'}

        IDs = []
        IDswaps = {}
        for object in objects:
            SwapID = ""
            try:
                ID = object["Z_ObjectID"]
                try:
                    SwapID = object["Z_SwapID"]
                    IDswaps[SwapID] = ID
                    PrettyPrint(f"Found Swap of ID: {ID} Swap: {SwapID}")
                    if SwapID != "" and not SwapID.isnumeric():
                        self.report({"ERROR"}, f"Object: {object.name} has an incorrect Swap ID. Assure that the ID is a proper integer entry ID.")
                        return {'CANCELLED'}
                except:
                    self.report({'INFO'}, f"{object.name} has no HD2 Swap ID. Skipping Swap.")
                IDitem = [ID, SwapID]
                if IDitem not in IDs:
                    IDs.append(IDitem)
            except KeyError:
                self.report({'ERROR'}, f"{object.name} has no HD2 custom properties")
                return {'CANCELLED'}
        swapCheck = {}
        for IDitem in IDs:
            ID = IDitem[0]
            SwapID = IDitem[1]
            if swapCheck.get(ID) == None:
                swapCheck[ID] = SwapID
            else:
                if (swapCheck[ID] == "" and SwapID != "") or (swapCheck[ID] != "" and SwapID == ""):
                    self.report({'ERROR'}, f"All Lods of object: {object.name} must have a swap ID! If you want to have an entry save to itself whilst swapping, set the SwapID to its own ObjectID.")
                    return {'CANCELLED'}
        objects_by_id = {}
        for obj in objects:
            try:
                objects_by_id[obj["Z_ObjectID"]][obj["MeshInfoIndex"]] = obj
            except KeyError:
                objects_by_id[obj["Z_ObjectID"]] = {obj["MeshInfoIndex"]: obj}
        MeshData = GetObjectsMeshData()
        BlenderOpts = bpy.context.scene.Hd2ToolPanelSettings.get_settings_dict()
        num_meshes = len(objects)
        for IDitem in IDs:
            ID = IDitem[0]
            SwapID = IDitem[1]
            Entry = Global_TocManager.GetEntryByLoadArchive(int(ID), MeshID)
            if Entry is None:
                self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Could not find custom property object at ID: {ID}")
                errors = True
                num_meshes -= len(MeshData[ID])
                continue
            if not Entry.IsLoaded: Entry.Load(True, False)
            MeshList = MeshData[ID]
            for mesh_index, mesh in MeshList.items():
                try:
                    Entry.LoadedData.RawMeshes[mesh_index] = mesh
                except IndexError:
                    self.report({'ERROR'},f"MeshInfoIndex of {mesh_index} for {object.name} exceeds the number of meshes")
                    errors = True
                    num_meshes -= 1
            if Global_TocManager.IsInPatch(Entry):
                Global_TocManager.RemoveEntryFromPatch(int(ID), MeshID)
            Entry = Global_TocManager.AddEntryToPatch(int(ID), MeshID)
            wasSaved = Entry.Save(BlenderOpts=BlenderOpts)
            if wasSaved:
                if SwapID != "" and SwapID.isnumeric():
                    self.report({'INFO'}, f"Swapping Entry ID: {Entry.FileID} to: {SwapID}")
                    Global_TocManager.RemoveEntryFromPatch(int(SwapID), MeshID)
                    Entry.FileID = int(SwapID)
            else:
                self.report({"ERROR"}, f"Failed to save mesh with ID {ID}.")
                num_meshes -= len(MeshData[ID])
                continue
        print("Saving mesh materials")
        SaveMeshMaterials(objects)
        self.report({'INFO'}, f"Saved {num_meshes}/{num_initially_selected} selected Meshes")
        if errors:
            self.report({'ERROR'}, f"Errors occurred while saving meshes. Click here to view.")
        PrettyPrint(f"Time to save meshes: {time.time()-start}")
        return{'FINISHED'}

def SaveMeshMaterials(objects):
    if not bpy.context.scene.Hd2ToolPanelSettings.AutoSaveMeshMaterials:
        PrettyPrint(f"Skipping saving of materials as setting is disabled")
        return
    PrettyPrint(f"Saving materials for {len(objects)} objects")
    materials = []
    for object in objects:
        for slot in object.material_slots:
            if slot.material:
                materialName = slot.material.name
                PrettyPrint(f"Found material: {materialName} in {object.name}")
                try: 
                    material = bpy.data.materials[materialName]
                except:
                    raise Exception(f"Could not find material: {materialName}")
                if material not in materials:
                    materials.append(material)

    PrettyPrint(f"Found {len(materials)} unique materials {materials}")
    for material in materials:
        try:
            ID = int(material.name)
        except:
            PrettyPrint(f"Failed to convert material: {material.name} to ID")
            continue

        nodeName = ""
        for node in material.node_tree.nodes:
            if node.type == 'GROUP':
                nodeName = node.node_tree.name
                PrettyPrint(f"ID: {ID} Group: {nodeName}")
                break

        if nodeName == "" and not bpy.context.scene.Hd2ToolPanelSettings.SaveNonSDKMaterials:
            PrettyPrint(f"Cancelling Saving Material: {ID}")
            continue

        entry = Global_TocManager.GetEntry(ID, MaterialID)
        if entry:
            if not entry.IsModified:
                PrettyPrint(f"Saving material: {ID}")
                Global_TocManager.Save(ID, MaterialID)
            else:
                PrettyPrint(f"Skipping Saving Material: {ID} as it already has been modified")
        elif "-" in nodeName:
            if str(ID) in nodeName.split("-")[1]:
                template = nodeName.split("-")[0]
                PrettyPrint(f"Creating material: {ID} with template: {template}")
                CreateModdedMaterial(template, ID)
                Global_TocManager.Save(ID, MaterialID)
            else:
                PrettyPrint(f"Failed to find template from group: {nodeName}", "error")
        else:
            PrettyPrint(f"Failed to save material: {ID}", "error")
