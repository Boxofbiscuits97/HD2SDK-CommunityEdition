import bpy

from __init__ import Global_TocManager, PrettyPrint


def MeshNotValidToSave(self):
    objects = bpy.context.selected_objects
    return (PatchesNotLoaded(self) or 
            CheckDuplicateIDsInScene(self, objects) or 
            CheckVertexGroups(self, objects) or 
            ObjectHasModifiers(self, objects) or 
            MaterialsNumberNames(self, objects) or 
            HasZeroVerticies(self, objects) or 
            ObjectHasShapeKeys(self, objects) or 
            CheckHaveHD2Properties(self, objects)
            )

def ArchivesNotLoaded(self):
    if len(Global_TocManager.LoadedArchives) <= 0:
        self.report({'ERROR'}, "No Archives Currently Loaded")
        return True
    else: 
        return False
    
def PatchesNotLoaded(self):
    if len(Global_TocManager.Patches) <= 0:
        self.report({'ERROR'}, "No Patches Currently Loaded")
        return True
    else:
        return False

def ObjectHasModifiers(self, objects):
    for obj in objects:
        if obj.modifiers:
            self.report({'ERROR'}, f"Object: {obj.name} has {len(obj.modifiers)} unapplied modifiers")
            return True
    return False

def ObjectHasShapeKeys(self, objects):
    for obj in objects:
        if hasattr(obj.data.shape_keys, 'key_blocks'):
            self.report({'ERROR'}, f"Object: {obj.name} has {len(obj.data.shape_keys.key_blocks)} unapplied shape keys")
            return True
    return False

def MaterialsNumberNames(self, objects):
    mesh_objs = [ob for ob in objects if ob.type == 'MESH']
    for mesh in mesh_objs:
        invalidMaterials = 0
        if len(mesh.material_slots) == 0:
            self.report({'ERROR'}, f"Object: {mesh.name} has no material slots")
            return True
        for slot in mesh.material_slots:
            if slot.material:
                materialName = slot.material.name
                if not materialName.isnumeric() and materialName != "StingrayDefaultMaterial":
                    invalidMaterials += 1
            else:
                invalidMaterials += 1
        if invalidMaterials > 0:
            self.report({'ERROR'}, f"Object: {mesh.name} has {invalidMaterials} non Helldivers 2 Materials")
            return True
    return False

def HasZeroVerticies(self, objects):
    mesh_objs = [ob for ob in objects if ob.type == 'MESH']
    for mesh in mesh_objs:
        verts = len(mesh.data.vertices)
        PrettyPrint(f"Object: {mesh.name} Verticies: {verts}")
        if verts <= 0:
            self.report({'ERROR'}, f"Object: {mesh.name} has no zero verticies")
            return True
    return False

def CheckHaveHD2Properties(self, objects):
    list_copy = list(objects)
    for obj in list_copy:
        try:
            _ = obj["Z_ObjectID"]
            _ = obj["MeshInfoIndex"]
            _ = obj["BoneInfoIndex"]
        except KeyError:
            self.report({'ERROR'}, f"Object {obj.name} is missing HD2 properties")
            return True
    return False


def CheckDuplicateIDsInScene(self, objects):
    custom_objects = {}
    for obj in objects:
        obj_id = obj.get("Z_ObjectID")
        swap_id = obj.get("Z_SwapID")
        mesh_index = obj.get("MeshInfoIndex")
        bone_index = obj.get("BoneInfoIndex")
        if obj_id is not None:
            obj_tuple = (obj_id, mesh_index, bone_index, swap_id)
            try:
                custom_objects[obj_tuple].append(obj)
            except:
                custom_objects[obj_tuple] = [obj]
    for item in custom_objects.values():
        if len(item) > 1:
            self.report({'ERROR'}, f"Multiple objects with the same HD2 properties are in the scene! Please delete one and try again.\nObjects: {', '.join([obj.name for obj in item])}")
            return True
    return False


def CheckVertexGroups(self, objects):
    list_copy = list(objects)
    for obj in list_copy:
        incorrectGroups = 0
        try:
            BoneIndex = obj["BoneInfoIndex"]
        except KeyError:
            self.report({'ERROR'}, f"Couldn't find HD2 Properties in {obj.name}")
            return True
        if len(obj.vertex_groups) <= 0 and BoneIndex != -1:
            self.report({'ERROR'}, f"No Vertex Groups Found for non-static mesh: {obj.name}")
            return True
        if len(obj.vertex_groups) > 0 and BoneIndex == -1:
            self.report({'ERROR'}, f"Vertex Groups Found for static mesh: {obj.name}. Please remove vertex groups.")
            return True
        for group in obj.vertex_groups:
            if "_" not in group.name:
                incorrectGroups += 1
        if incorrectGroups > 0:
            self.report({'ERROR'}, f"Found {incorrectGroups} Incorrect Vertex Group Name Scheming for Object: {obj.name}")
            return True
    return False