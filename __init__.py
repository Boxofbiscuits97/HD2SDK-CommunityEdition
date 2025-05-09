bl_info = {
    "name": "Helldivers 2 SDK: Community Edition",
    "version": (2, 7, 5),
    "blender": (4, 0, 0),
    "category": "Import-Export",
}

#region Imports

# System
import ctypes, os, tempfile, subprocess, time, webbrowser, shutil, datetime
import random as r
from copy import deepcopy
import copy
from math import ceil
from pathlib import Path
import configparser
import requests
import json

#import pyautogui 

# Blender
import bpy, bmesh, mathutils
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Panel, Operator, PropertyGroup, Scene, Menu

# Local
# NOTE: Not bothering to do importlib reloading shit because these modules are unlikely to be modified frequently enough to warrant testing without Blender restarts
from .math import MakeTenBitUnsigned, TenBitUnsigned
from .memoryStream import MemoryStream

#endregion

#region Global Variables

AddonPath = os.path.dirname(__file__)

Global_dllpath           = f"{AddonPath}\\deps\\HDTool_Helper.dll"
Global_texconvpath       = f"{AddonPath}\\deps\\texconv.exe"
Global_palettepath       = f"{AddonPath}\\deps\\NormalPalette.dat"
Global_materialpath      = f"{AddonPath}\\materials"
Global_typehashpath      = f"{AddonPath}\\hashlists\\typehash.txt"
Global_filehashpath      = f"{AddonPath}\\hashlists\\filehash.txt"
Global_friendlynamespath = f"{AddonPath}\\hashlists\\friendlynames.txt"

Global_archivehashpath   = f"{AddonPath}\\hashlists\\archivehashes.json"
Global_variablespath     = f"{AddonPath}\\hashlists\\shadervariables.txt"
Global_bonehashpath      = f"{AddonPath}\\hashlists\\bonehash.txt"

Global_ShaderVariables = {}

Global_defaultgamepath   = "C:\Program Files (x86)\Steam\steamapps\common\Helldivers 2\data\ "
Global_defaultgamepath   = Global_defaultgamepath[:len(Global_defaultgamepath) - 1]
Global_gamepath          = ""
Global_searchpath        = ""
Global_configpath        = f"{AddonPath}.ini"
Global_backslash         = "\-".replace("-", "")

Global_CPPHelper = ctypes.cdll.LoadLibrary(Global_dllpath) if os.path.isfile(Global_dllpath) else None

Global_Foldouts = []

Global_SectionHeader = "---------- Helldivers 2 ----------"

Global_randomID = ""

Global_latestVersionLink = "https://api.github.com/repos/Boxofbiscuits97/HD2SDK-CommunityEdition/releases/latest"
Global_addonUpToDate = None

Global_archieHashLink = "https://raw.githubusercontent.com/Boxofbiscuits97/HD2SDK-CommunityEdition/main/hashlists/archivehashes.json"

Global_previousRandomHash = 0

Global_BoneNames = {}
#endregion

#region Common Hashes & Lookups

BaseArchiveHexID = "9ba626afa44a3aa3"

CompositeMeshID = 14191111524867688662
MeshID = 16187218042980615487
TexID  = 14790446551990181426
MaterialID  = 16915718763308572383
BoneID  = 1792059921637536489
WwiseBankID = 6006249203084351385
WwiseDepID  = 12624162998411505776
WwiseStreamID  = 5785811756662211598
WwiseMetaDataID  = 15351235653606224144
ParticleID = 12112766700566326628
AnimationID = 10600967118105529382
StateMachineID = 11855396184103720540
StringID = 979299457696010195
PhysicsID = 6877563742545042104

TextureTypeLookup = {
    "original": (
        "PBR", 
        "", 
        "", 
        "", 
        "Bump Map", 
        "Normal", 
        "", 
        "Emission", 
        "Bump Map", 
        "Base Color", 
        "", 
        "", 
        ""
    ),
    "basic": (
        "PBR", 
        "Base Color", 
        "Normal"
    ),
    "basic+": (
        "PBR",
        "Base Color",
        "Normal"
    ),
    "emissive": (
        "Normal/AO/Roughness", 
        "Emission", 
        "Base Color/Metallic"
    ),
    "alphaclip": (
        "Normal/AO/Roughness",
        "Alpha Mask",
        "Base Color/Metallic"
    ),
    "advanced": (
        "",
        "",
        "Normal/AO/Roughness",
        "Metallic",
        "",
        "Color/Emission Mask",
        "",
        "",
        "",
        "",
        ""
    ),
    "translucent": (
        "Normal",
    )
}

Global_Materials = (
        ("advanced", "Advanced", "A more comlpicated material, that is color, normal, emission and PBR capable which renders in the UI. Sourced from the Illuminate Overseer."),
        ("basic+", "Basic+", "A basic material with a color, normal, and PBR map which renders in the UI, Sourced from the super credits prop"),
        ("translucent", "Translucent", "A translucent with a solid set color and normal map. Sourced from the Terminid Larva Backpack."),
        ("alphaclip", "Alpha Clip", "A material that supports an alpha mask which does not render in the UI. Sourced from a skeleton pile"),
        ("original", "Original", "The original template used for all mods uploaded to Nexus prior to the addon's public release, which is bloated with additional unnecessary textures. Sourced from a terminid"),
        ("basic", "Basic", "A basic material with a color, normal, and PBR map. Sourced from a trash bag prop"),
        ("emissive", "Emissive", "A basic material with a color, normal, and emission map. Sourced from a vending machine"),
    )

Global_MaterialParentIDs = {
    3430705909399566334 : "basic+",
    15586118709890920288 : "alphaclip",
    6101987038150196875 : "original",
    15356477064658408677 : "basic",
    15235712479575174153 : "emissive",
    17265463703140804126 : "advanced",
    9576304397847579354  : "translucent"
}

#endregion

#region Functions: Miscellaneous

# 4.3 compatibility change
def CheckBlenderVersion():
    global OnCorrectBlenderVersion
    BlenderVersion = bpy.app.version
    OnCorrectBlenderVersion = (BlenderVersion[0] == 4 and BlenderVersion[1] <= 3)
    PrettyPrint(f"Blender Version: {BlenderVersion} Correct Version: {OnCorrectBlenderVersion}")

def CheckAddonUpToDate():
    PrettyPrint("Checking If Addon is up to date...")
    currentVersion = bl_info["version"]
    try:
        req = requests.get(Global_latestVersionLink)
        req.raise_for_status()  # Check if the request is successful.
        if req.status_code == requests.codes.ok:
            req = req.json()
            latestVersion = req['tag_name'].replace("v", "")
            latestVersion = (int(latestVersion.split(".")[0]), int(latestVersion.split(".")[1]), int(latestVersion.split(".")[2]))
            
            PrettyPrint(f"Current Version: {currentVersion}")
            PrettyPrint(f"Latest Version: {latestVersion}")

            global Global_addonUpToDate
            global Global_latestAddonVersion
            Global_addonUpToDate = latestVersion == currentVersion
            Global_latestAddonVersion = f"{latestVersion[0]}.{latestVersion[1]}.{latestVersion[2]}"

            if Global_addonUpToDate:
                PrettyPrint("Addon is up to date!")
            else:
                PrettyPrint("Addon is outdated!")
        else:
            PrettyPrint(f"Request Failed, Cannot check latest Version. Status: {req.status_code}", "warn")
    except requests.ConnectionError:
        PrettyPrint("Connection failed. Please check your network settings.", "warn")
    except requests.HTTPError as err:
        PrettyPrint(f"HTTP error occurred: {err}", "warn")
        
def UpdateArchiveHashes():
    try:
        req = requests.get(Global_archieHashLink)
        req.raise_for_status()  # Check if the request is successful.
        if req.status_code == requests.codes.ok:
            file = open(Global_archivehashpath, "w")
            file.write(req.text)
            PrettyPrint(f"Updated Archive Hashes File")
        else:
            PrettyPrint(f"Request Failed, Could not update Archive Hashes File", "warn")
    except requests.ConnectionError:
        PrettyPrint("Connection failed. Please check your network settings.", "warn")
    except requests.HTTPError as err:
        PrettyPrint(f"HTTP error occurred: {err}", "warn")

def PrettyPrint(msg, type="info"): # Inspired by FortnitePorting
    reset = u"\u001b[0m"
    color = reset
    match type.lower():
        case "info":
            color = u"\u001b[36m"
        case "warn" | "warning":
            color = u"\u001b[33m"
        case "error":
            color = u"\u001b[31m"
        case _:
            pass
    print(f"{color}[HD2SDK:CE]{reset} {msg}")

def DXGI_FORMAT(format):
    Dict = {0: "UNKNOWN", 1: "R32G32B32A32_TYPELESS", 2: "R32G32B32A32_FLOAT", 3: "R32G32B32A32_UINT", 4: "R32G32B32A32_SINT", 5: "R32G32B32_TYPELESS", 6: "R32G32B32_FLOAT", 7: "R32G32B32_UINT", 8: "R32G32B32_SINT", 9: "R16G16B16A16_TYPELESS", 10: "R16G16B16A16_FLOAT", 11: "R16G16B16A16_UNORM", 12: "R16G16B16A16_UINT", 13: "R16G16B16A16_SNORM", 14: "R16G16B16A16_SINT", 15: "R32G32_TYPELESS", 16: "R32G32_FLOAT", 17: "R32G32_UINT", 18: "R32G32_SINT", 19: "R32G8X24_TYPELESS", 20: "D32_FLOAT_S8X24_UINT", 21: "R32_FLOAT_X8X24_TYPELESS", 22: "X32_TYPELESS_G8X24_UINT", 23: "R10G10B10A2_TYPELESS", 24: "R10G10B10A2_UNORM", 25: "R10G10B10A2_UINT", 26: "R11G11B10_FLOAT", 27: "R8G8B8A8_TYPELESS", 28: "R8G8B8A8_UNORM", 29: "R8G8B8A8_UNORM_SRGB", 30: "R8G8B8A8_UINT", 31: "R8G8B8A8_SNORM", 32: "R8G8B8A8_SINT", 33: "R16G16_TYPELESS", 34: "R16G16_FLOAT", 35: "R16G16_UNORM", 36: "R16G16_UINT", 37: "R16G16_SNORM", 38: "R16G16_SINT", 39: "R32_TYPELESS", 40: "D32_FLOAT", 41: "R32_FLOAT", 42: "R32_UINT", 43: "R32_SINT", 44: "R24G8_TYPELESS", 45: "D24_UNORM_S8_UINT", 46: "R24_UNORM_X8_TYPELESS", 47: "X24_TYPELESS_G8_UINT", 48: "R8G8_TYPELESS", 49: "R8G8_UNORM", 50: "R8G8_UINT", 51: "R8G8_SNORM", 52: "R8G8_SINT", 53: "R16_TYPELESS", 54: "R16_FLOAT", 55: "D16_UNORM", 56: "R16_UNORM", 57: "R16_UINT", 58: "R16_SNORM", 59: "R16_SINT", 60: "R8_TYPELESS", 61: "R8_UNORM", 62: "R8_UINT", 63: "R8_SNORM", 64: "R8_SINT", 65: "A8_UNORM", 66: "R1_UNORM", 67: "R9G9B9E5_SHAREDEXP", 68: "R8G8_B8G8_UNORM", 69: "G8R8_G8B8_UNORM", 70: "BC1_TYPELESS", 71: "BC1_UNORM", 72: "BC1_UNORM_SRGB", 73: "BC2_TYPELESS", 74: "BC2_UNORM", 75: "BC2_UNORM_SRGB", 76: "BC3_TYPELESS", 77: "BC3_UNORM", 78: "BC3_UNORM_SRGB", 79: "BC4_TYPELESS", 80: "BC4_UNORM", 81: "BC4_SNORM", 82: "BC5_TYPELESS", 83: "BC5_UNORM", 84: "BC5_SNORM", 85: "B5G6R5_UNORM", 86: "B5G5R5A1_UNORM", 87: "B8G8R8A8_UNORM", 88: "B8G8R8X8_UNORM", 89: "R10G10B10_XR_BIAS_A2_UNORM", 90: "B8G8R8A8_TYPELESS", 91: "B8G8R8A8_UNORM_SRGB", 92: "B8G8R8X8_TYPELESS", 93: "B8G8R8X8_UNORM_SRGB", 94: "BC6H_TYPELESS", 95: "BC6H_UF16", 96: "BC6H_SF16", 97: "BC7_TYPELESS", 98: "BC7_UNORM", 99: "BC7_UNORM_SRGB", 100: "AYUV", 101: "Y410", 102: "Y416", 103: "NV12", 104: "P010", 105: "P016", 106: "420_OPAQUE", 107: "YUY2", 108: "Y210", 109: "Y216", 110: "NV11", 111: "AI44", 112: "IA44", 113: "P8", 114: "A8P8", 115: "B4G4R4A4_UNORM", 130: "P208", 131: "V208", 132: "V408"}
    return Dict[format]

def DXGI_FORMAT_SIZE(format):
    if format.find("BC1") != -1 or format.find("BC4") != -1:
        return 8
    elif format.find("BC") != -1:
        return 16
    else:
        raise Exception("Provided DDS' format is currently unsupported")

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

def GetDisplayData():
    # Set display archive TODO: Global_TocManager.LastSelected Draw Index could be wrong if we switch to patch only mode, that should be fixed
    DisplayTocEntries = []
    DisplayTocTypes   = []
    DisplayArchive = Global_TocManager.ActiveArchive
    if bpy.context.scene.Hd2ToolPanelSettings.PatchOnly:
        if Global_TocManager.ActivePatch != None:
            DisplayTocEntries = [[Entry, True] for Entry in Global_TocManager.ActivePatch.TocEntries]
            DisplayTocTypes   = Global_TocManager.ActivePatch.TocTypes
    elif Global_TocManager.ActiveArchive != None:
        DisplayTocEntries = [[Entry, False] for Entry in Global_TocManager.ActiveArchive.TocEntries]
        DisplayTocTypes   = [Type for Type in Global_TocManager.ActiveArchive.TocTypes]
        AddedTypes   = [Type.TypeID for Type in DisplayTocTypes]
        AddedEntries = [Entry[0].FileID for Entry in DisplayTocEntries]
        if Global_TocManager.ActivePatch != None:
            for Type in Global_TocManager.ActivePatch.TocTypes:
                if Type.TypeID not in AddedTypes:
                    AddedTypes.append(Type.TypeID)
                    DisplayTocTypes.append(Type)
            for Entry in Global_TocManager.ActivePatch.TocEntries:
                if Entry.FileID not in AddedEntries:
                    AddedEntries.append(Entry.FileID)
                    DisplayTocEntries.append([Entry, True])
    return [DisplayTocEntries, DisplayTocTypes]


def ApplyAllTransforms(self, FileID):
    bpy.ops.object.select_all(action='DESELECT')
    PrettyPrint(f"Applying transforms to {FileID}")
    for obj in bpy.context.scene.objects:
        try:
            id = int(obj["Z_ObjectID"])
            if FileID == id:
                obj.select_set(True)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                obj.rotation_mode = 'QUATERNION'
                obj.select_set(False)
        except:
            id = None

def SaveUnsavedEntries(self):
    for Entry in Global_TocManager.ActivePatch.TocEntries:
                if not Entry.IsModified:
                    Global_TocManager.Save(int(Entry.FileID), Entry.TypeID)
                    PrettyPrint(f"Saved {int(Entry.FileID)}")

def RandomHash16():
    global Global_previousRandomHash
    hash = Global_previousRandomHash
    while hash == Global_previousRandomHash:
        r.seed(datetime.datetime.now().timestamp())
        hash = r.randint(1, 0xffffffffffffffff)
    Global_previousRandomHash = hash
    PrettyPrint(f"Generated hash: {hash}")
    return hash
#endregion

#region Functions: Blender

def duplicate(obj, data=True, actions=True, collection=None):
    obj_copy = obj.copy()
    if data:
        obj_copy.data = obj_copy.data.copy()
    if actions and obj_copy.animation_data:
        if obj_copy.animation_data.action:
            obj_copy.animation_data.action = obj_copy.animation_data.action.copy()
    bpy.context.collection.objects.link(obj_copy)
    return obj_copy

def PrepareMesh(og_object):
    object = duplicate(og_object)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    # split UV seams
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.seams_from_islands()
    except: PrettyPrint("Failed to create seams from UV islands. This is not fatal, but will likely cause undesirable results in-game", "warn")
    bpy.ops.object.mode_set(mode='OBJECT')

    bm = bmesh.new()
    bm.from_mesh(object.data)

    # get all sharp edges and uv seams
    sharp_edges = [e for e in bm.edges if not e.smooth]
    boundary_seams = [e for e in bm.edges if e.seam]
    # split edges
    bmesh.ops.split_edges(bm, edges=sharp_edges)
    bmesh.ops.split_edges(bm, edges=boundary_seams)
    # update mesh
    bm.to_mesh(object.data)
    bm.clear()
    # transfer normals
    modifier = object.modifiers.new("EXPORT_NORMAL_TRANSFER", 'DATA_TRANSFER')
    bpy.context.object.modifiers[modifier.name].data_types_loops = {'CUSTOM_NORMAL'}
    bpy.context.object.modifiers[modifier.name].object = og_object
    bpy.context.object.modifiers[modifier.name].use_loop_data = True
    bpy.context.object.modifiers[modifier.name].loop_mapping = 'TOPOLOGY'
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # triangulate
    modifier = object.modifiers.new("EXPORT_TRIANGULATE", 'TRIANGULATE')
    bpy.context.object.modifiers[modifier.name].keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    # adjust weights
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    try:
        bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    except: pass

    return object

def GetMeshData(og_object):
    global Global_palettepath
    object = PrepareMesh(og_object)
    bpy.context.view_layer.objects.active = object
    mesh = object.data

    vertices    = [ [vert.co[0], vert.co[1], vert.co[2]] for vert in mesh.vertices]
    normals     = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    tangents    = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    bitangents  = [ [vert.normal[0], vert.normal[1], vert.normal[2]] for vert in mesh.vertices]
    colors      = [[0,0,0,0] for n in range(len(vertices))]
    uvs         = []
    weights     = [[0,0,0,0] for n in range(len(vertices))]
    boneIndices = []
    faces       = []
    materials   = [ RawMaterialClass() for idx in range(len(object.material_slots))]
    for idx in range(len(object.material_slots)): materials[idx].IDFromName(object.material_slots[idx].name)

    # get vertex color
    if mesh.vertex_colors:
        color_layer = mesh.vertex_colors.active
        for face in object.data.polygons:
            if color_layer == None: 
                PrettyPrint(f"{og_object.name} Color Layer does not exist", 'ERROR')
                break
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                col = color_layer.data[loop_idx].color
                colors[vert_idx] = [col[0], col[1], col[2], col[3]]

    # get normals, tangents, bitangents
    #mesh.calc_tangents()
    # 4.3 compatibility change
    if bpy.app.version[0] >= 4 and bpy.app.version[1] == 0:
        if not mesh.has_custom_normals:
            mesh.create_normals_split()
        mesh.calc_normals_split()
        
    for loop in mesh.loops:
        normals[loop.vertex_index]    = loop.normal.normalized()
        #tangents[loop.vertex_index]   = loop.tangent.normalized()
        #bitangents[loop.vertex_index] = loop.bitangent.normalized()
    # if fuckywuckynormalwormal do this bullshit
    LoadNormalPalette(Global_palettepath)
    normals = NormalsFromPalette(normals)
    # get uvs
    for uvlayer in object.data.uv_layers:
        if len(uvs) >= 3:
            break
        texCoord = [[0,0] for vert in mesh.vertices]
        for face in object.data.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                texCoord[vert_idx] = [uvlayer.data[loop_idx].uv[0], uvlayer.data[loop_idx].uv[1]*-1 + 1]
        uvs.append(texCoord)

    # get weights
    vert_idx = 0
    numInfluences = 4
    if len(object.vertex_groups) > 0:
        for vertex in mesh.vertices:
            group_idx = 0
            for group in vertex.groups:
                # limit influences
                if group_idx >= numInfluences:
                    break
                if group.weight > 0.001:
                    vertex_group        = object.vertex_groups[group.group]
                    vertex_group_name   = vertex_group.name
                    parts               = vertex_group_name.split("_")
                    HDGroupIndex        = int(parts[0])
                    HDBoneIndex         = int(parts[1])
                    if HDGroupIndex+1 > len(boneIndices):
                        dif = HDGroupIndex+1 - len(boneIndices)
                        boneIndices.extend([[[0,0,0,0] for n in range(len(vertices))]]*dif)
                    boneIndices[HDGroupIndex][vert_idx][group_idx] = HDBoneIndex
                    weights[vert_idx][group_idx] = group.weight
                    group_idx += 1
            vert_idx += 1
    else:
        boneIndices = []
        weights     = []

    # get faces
    temp_faces = [[] for n in range(len(object.material_slots))]
    for f in mesh.polygons:
        temp_faces[f.material_index].append([f.vertices[0], f.vertices[1], f.vertices[2]])
        materials[f.material_index].NumIndices += 3
    for tmp in temp_faces: faces.extend(tmp)

    NewMesh = RawMeshClass()
    NewMesh.VertexPositions     = vertices
    NewMesh.VertexNormals       = normals
    #NewMesh.VertexTangents      = tangents
    #NewMesh.VertexBiTangents    = bitangents
    NewMesh.VertexColors        = colors
    NewMesh.VertexUVs           = uvs
    NewMesh.VertexWeights       = weights
    NewMesh.VertexBoneIndices   = boneIndices
    NewMesh.Indices             = faces
    NewMesh.Materials           = materials
    NewMesh.MeshInfoIndex       = og_object["MeshInfoIndex"]
    NewMesh.DEV_BoneInfoIndex   = og_object["BoneInfoIndex"]
    NewMesh.LodIndex            = og_object["BoneInfoIndex"]
    if len(vertices) > 0xffff: NewMesh.DEV_Use32BitIndices = True
    matNum = 0
    for material in NewMesh.Materials:
        try:
            material.DEV_BoneInfoOverride = int(og_object[f"matslot{matNum}"])
        except: pass
        matNum += 1

    if object is not None and object.name:
        PrettyPrint(f"Removing {object.name}")
        bpy.data.objects.remove(object, do_unlink=True)
    else:
        PrettyPrint(f"Current object: {object}")
    return NewMesh

def GetObjectsMeshData():
    objects = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')
    data = {}
    for object in objects:
        ID = object["Z_ObjectID"]
        data[ID] = GetMeshData(object)
        #data.append(GetMeshData(object))
    return data

def NameFromMesh(mesh, id, customization_info, bone_names, use_sufix=True):
    # generate name
    name = str(id)
    if customization_info.BodyType != "":
        BodyType    = customization_info.BodyType.replace("HelldiverCustomizationBodyType_", "")
        Slot        = customization_info.Slot.replace("HelldiverCustomizationSlot_", "")
        Weight      = customization_info.Weight.replace("HelldiverCustomizationWeight_", "")
        PieceType   = customization_info.PieceType.replace("HelldiverCustomizationPieceType_", "")
        name = Slot+"_"+PieceType+"_"+BodyType
    name_sufix = "_lod"+str(mesh.LodIndex)
    if mesh.LodIndex == -1:
        name_sufix = "_mesh"+str(mesh.MeshInfoIndex)
    if mesh.IsCullingBody():
        name_sufix = "_culling"+str(mesh.MeshInfoIndex)
    if use_sufix: name = name + name_sufix

    if use_sufix and bone_names != None:
        for bone_name in bone_names:
            if Hash32(bone_name) == mesh.MeshID:
                name = bone_name

    return name

def CreateModel(model, id, customization_info, bone_names, transform_info, bone_info):
    if len(model) < 1: return
    # Make collection
    old_collection = bpy.context.collection
    if bpy.context.scene.Hd2ToolPanelSettings.MakeCollections:
        new_collection = bpy.data.collections.new(NameFromMesh(model[0], id, customization_info, bone_names, False))
        old_collection.children.link(new_collection)
    else:
        new_collection = old_collection
    # Make Meshes
    for mesh in model:
        # check lod
        if not bpy.context.scene.Hd2ToolPanelSettings.ImportLods and mesh.IsLod():
            continue
        # check physics
        if not bpy.context.scene.Hd2ToolPanelSettings.ImportCulling and mesh.IsCullingBody():
            continue
        # check static
        if not bpy.context.scene.Hd2ToolPanelSettings.ImportStatic and mesh.IsStaticMesh():
            continue
        # do safety check
        for face in mesh.Indices:
            for index in face:
                if index > len(mesh.VertexPositions):
                    raise Exception("Bad Mesh Parse: indices do not match vertices")
        # generate name
        name = NameFromMesh(mesh, id, customization_info, bone_names)

        # create mesh
        new_mesh = bpy.data.meshes.new(name)
        #new_mesh.from_pydata(mesh.VertexPositions, [], [])
        new_mesh.from_pydata(mesh.VertexPositions, [], mesh.Indices)
        new_mesh.update()
        # make object from mesh
        new_object = bpy.data.objects.new(name, new_mesh)
        # set transform
        PrettyPrint(f"scale: {mesh.DEV_Transform.scale}")
        PrettyPrint(f"location: {mesh.DEV_Transform.pos}")
        new_object.scale = (mesh.DEV_Transform.scale[0],mesh.DEV_Transform.scale[1],mesh.DEV_Transform.scale[2])
        new_object.location = (mesh.DEV_Transform.pos[0],mesh.DEV_Transform.pos[1],mesh.DEV_Transform.pos[2])

        # TODO: fix incorrect rotation
        rot = mesh.DEV_Transform.rot
        rotation_matrix = mathutils.Matrix([rot.x, rot.y, rot.z])
        new_object.rotation_mode = 'QUATERNION'
        new_object.rotation_quaternion = rotation_matrix.to_quaternion()

        # set object properties
        new_object["MeshInfoIndex"] = mesh.MeshInfoIndex
        new_object["BoneInfoIndex"] = mesh.LodIndex
        new_object["Z_ObjectID"]      = str(id)
        if customization_info.BodyType != "":
            new_object["Z_CustomizationBodyType"] = customization_info.BodyType
            new_object["Z_CustomizationSlot"]     = customization_info.Slot
            new_object["Z_CustomizationWeight"]   = customization_info.Weight
            new_object["Z_CustomizationPieceType"]= customization_info.PieceType
        if mesh.IsCullingBody():
            new_object.display_type = 'WIRE'

        # add object to scene collection
        new_collection.objects.link(new_object)
        # -- || ASSIGN NORMALS || -- #
        if len(mesh.VertexNormals) == len(mesh.VertexPositions):
            # 4.3 compatibility change
            if bpy.app.version[0] >= 4 and bpy.app.version[1] >= 1:
                new_mesh.shade_smooth()
            else:
                new_mesh.use_auto_smooth = True
            
            new_mesh.polygons.foreach_set('use_smooth',  [True] * len(new_mesh.polygons))
            if not isinstance(mesh.VertexNormals[0], int):
                new_mesh.normals_split_custom_set_from_vertices(mesh.VertexNormals)

        # -- || ASSIGN VERTEX COLORS || -- #
        if len(mesh.VertexColors) == len(mesh.VertexPositions):
            color_layer = new_mesh.vertex_colors.new()
            for face in new_mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    color_layer.data[loop_idx].color = (mesh.VertexColors[vert_idx][0], mesh.VertexColors[vert_idx][1], mesh.VertexColors[vert_idx][2], mesh.VertexColors[vert_idx][3])
        # -- || ASSIGN UVS || -- #
        for uvs in mesh.VertexUVs:
            uvlayer = new_mesh.uv_layers.new()
            new_mesh.uv_layers.active = uvlayer
            for face in new_mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    uvlayer.data[loop_idx].uv = (uvs[vert_idx][0], uvs[vert_idx][1]*-1 + 1)
        # -- || ASSIGN WEIGHTS || -- #
        created_groups = []
        for vertex_idx in range(len(mesh.VertexWeights)):
            weights      = mesh.VertexWeights[vertex_idx]
            index_groups = [Indices[vertex_idx] for Indices in mesh.VertexBoneIndices]
            group_index  = 0
            for indices in index_groups:
                if bpy.context.scene.Hd2ToolPanelSettings.ImportGroup0 and group_index != 0:
                    continue
                if type(weights) != list:
                    weights = [weights]
                for weight_idx in range(len(weights)):
                    weight_value = weights[weight_idx]
                    bone_index   = indices[weight_idx]
                    #bone_index   = mesh.DEV_BoneInfo.GetRealIndex(bone_index)
                    group_name = str(group_index) + "_" + str(bone_index)
                    if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
                        hashIndex = bone_info[mesh.LodIndex].RealIndices[bone_index] - 1
                        boneHash = transform_info.NameHashes[hashIndex]
                        global Global_BoneNames
                        if boneHash in Global_BoneNames:
                            group_name = Global_BoneNames[boneHash]
                        else:
                            group_name = str(boneHash)
                    if group_name not in created_groups:
                        created_groups.append(group_name)
                        new_vertex_group = new_object.vertex_groups.new(name=str(group_name))
                    vertex_group_data = [vertex_idx]
                    new_object.vertex_groups[str(group_name)].add(vertex_group_data, weight_value, 'ADD')
                group_index += 1
        # -- || ASSIGN MATERIALS || -- #
        # convert mesh to bmesh
        bm = bmesh.new()
        bm.from_mesh(new_object.data)
        # assign materials
        matNum = 0
        goreIndex = None
        for material in mesh.Materials:
            if str(material.MatID) == "12070197922454493211":
                goreIndex = matNum
                PrettyPrint(f"Found gore material at index: {matNum}")
            # append material to slot
            try: new_object.data.materials.append(bpy.data.materials[material.MatID])
            except: raise Exception(f"Tool was unable to find material that this mesh uses, ID: {material.MatID}")
            # assign material to faces
            numTris    = int(material.NumIndices/3)
            StartIndex = int(material.StartIndex/3)
            for f in bm.faces[StartIndex:(numTris+(StartIndex))]:
                f.material_index = matNum
            matNum += 1
        # remove gore mesh
        if bpy.context.scene.Hd2ToolPanelSettings.RemoveGoreMeshes and goreIndex:
            PrettyPrint(f"Removing Gore Mesh")
            verticies = []
            for vert in bm.verts:
                if len(vert.link_faces) == 0:
                    continue
                if vert.link_faces[0].material_index == goreIndex:
                    verticies.append(vert)
            for vert in verticies:
                bm.verts.remove(vert)
        # convert bmesh to mesh
        bm.to_mesh(new_object.data)


        # Create skeleton
        if False:
            if mesh.DEV_BoneInfo != None:
                for Bone in mesh.DEV_BoneInfo.Bones:
                    current_pos = [Bone.v[12], Bone.v[13], Bone.v[14]]
                    bpy.ops.object.empty_add(type='SPHERE', radius=0.08, align='WORLD', location=(current_pos[0], current_pos[1], current_pos[2]), scale=(1, 1, 1))

#endregion

#region Functions: Stingray Hashing

def GetTypeNameFromID(ID):
    for hash_info in Global_TypeHashes:
        if int(ID) == hash_info[0]:
            return hash_info[1]
    return "unknown"

def GetIDFromTypeName(Name):
    for hash_info in Global_TypeHashes:
        if hash_info[1] == Name:
            return int(hash_info[0])
    return None

def GetFriendlyNameFromID(ID):
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            if hash_info[1] != "":
                return hash_info[1]
    return str(ID)

def GetArchiveNameFromID(EntryID):
    for hash in Global_ArchiveHashes:
        if hash[0] == EntryID:
            return hash[1]
    return ""

def GetVertexGroupsFromID(EntryID, InfoIndex):
    for archive in Global_TocManager.LoadedArchives:
        for entry in archive.TocEntries:
            for vertexObjects in entry.VertexGroups:
                if vertexObjects[0] == EntryID and vertexObjects[1] == InfoIndex:
                    PrettyPrint(f"Found Vertex Groups {vertexObjects[2]}")
                    return vertexObjects[2]
    return None

def GetTransformsFromID(EntryID, InfoIndex):
    for archive in Global_TocManager.LoadedArchives:
        for entry in archive.TocEntries:
            for transformObjects in entry.Transforms:
                if transformObjects[0] == EntryID and transformObjects[1] == InfoIndex:
                    PrettyPrint(f"Found Transforms {transformObjects[2]}")
                    return transformObjects[2]
    return None

def GetArchiveIDFromName(Name):
    for hash in Global_ArchiveHashes:
        if hash[1] == Name:
            return hash[0]
    return ""

def HasFriendlyName(ID):
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            return True
    return False

def AddFriendlyName(ID, Name):
    Global_TocManager.SavedFriendlyNames = []
    Global_TocManager.SavedFriendlyNameIDs = []
    for hash_info in Global_NameHashes:
        if int(ID) == hash_info[0]:
            hash_info[1] = str(Name)
            return
    Global_NameHashes.append([int(ID), str(Name)])
    SaveFriendlyNames()

def SaveFriendlyNames():
    with open(Global_filehashpath, 'w') as f:
        for hash_info in Global_NameHashes:
            if hash_info[1] != "" and int(hash_info[0]) == Hash64(hash_info[1]):
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")
    with open(Global_friendlynamespath, 'w') as f:
        for hash_info in Global_NameHashes:
            if hash_info[1] != "":
                string = str(hash_info[0]) + " " + str(hash_info[1])
                f.writelines(string+"\n")

def Hash32(string):
    output    = bytearray(4)
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_Hash32(c_output, string.encode())
    F = MemoryStream(output, IOMode = "read")
    return F.uint32(0)

def Hash64(string):
    output    = bytearray(8)
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_Hash64(c_output, string.encode())
    F = MemoryStream(output, IOMode = "read")
    return F.uint64(0)

#endregion

#region Functions: Initialization

def LoadNormalPalette(path):
    Global_CPPHelper.dll_LoadPalette(path.encode())

def NormalsFromPalette(normals):
    f = MemoryStream(IOMode = "write")
    normals = [f.vec3_float(normal) for normal in normals]
    output    = bytearray(len(normals)*4)
    c_normals = ctypes.c_char_p(bytes(f.Data))
    c_output  = (ctypes.c_char * len(output)).from_buffer(output)
    Global_CPPHelper.dll_NormalsFromPalette(c_output, c_normals, ctypes.c_uint32(len(normals)))
    F = MemoryStream(output, IOMode = "read")
    return [F.uint32(0) for normal in normals]

Global_TypeHashes = []
def LoadTypeHashes():
    with open(Global_typehashpath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ")
            Global_TypeHashes.append([int(parts[0], 16), parts[1].replace("\n", "")])

Global_NameHashes = []
def LoadNameHashes():
    Loaded = []
    with open(Global_filehashpath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ")
            Global_NameHashes.append([int(parts[0]), parts[1].replace("\n", "")])
            Loaded.append(int(parts[0]))
    with open(Global_friendlynamespath, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ", 1)
            if int(parts[0]) not in Loaded:
                Global_NameHashes.append([int(parts[0]), parts[1].replace("\n", "")])
                Loaded.append(int(parts[0]))

Global_ArchiveHashes = []
def LoadHash(path, title):
    with open(path, 'r') as f:
        for line in f.readlines():
            parts = line.split(" ", 1)
            Global_ArchiveHashes.append([parts[0], title + parts[1].replace("\n", "")])
                
def LoadArchiveHashes():
    file = open(Global_archivehashpath, "r")
    data = json.load(file)

    for title in data:
        for innerKey in data[title]:
            Global_ArchiveHashes.append([innerKey, title + ": " + data[title][innerKey]])

    Global_ArchiveHashes.append([BaseArchiveHexID, "SDK: Base Patch Archive"])

def LoadShaderVariables():
    global Global_ShaderVariables
    file = open(Global_variablespath, "r")
    text = file.read()
    for line in text.splitlines():
        Global_ShaderVariables[int(line.split()[1], 16)] = line.split()[0]

def LoadBoneHashes():
    global Global_BoneNames
    file = open(Global_bonehashpath, "r")
    text = file.read()
    for line in text.splitlines():
        Global_BoneNames[int(line.split()[0])] = line.split()[1]

def GetEntryParentMaterialID(entry):
    if entry.TypeID == MaterialID:
        f = MemoryStream(entry.TocData)
        for i in range(6):
            f.uint32(0)
        parentID = f.uint64(0)
        return parentID
    else:
        raise Exception(f"Entry: {entry.FileID} is not a material")

#endregion

#region Configuration

def InitializeConfig():
    global Global_gamepath, Global_searchpath, Global_configpath
    if os.path.exists(Global_configpath):
        config = configparser.ConfigParser()
        config.read(Global_configpath, encoding='utf-8')
        try:
            Global_gamepath = config['DEFAULT']['filepath']
            Global_searchpath = config['DEFAULT']['searchpath']
        except:
            UpdateConfig()
        PrettyPrint(f"Loaded Data Folder: {Global_gamepath}")

    else:
        UpdateConfig()

def UpdateConfig():
    global Global_gamepath, Global_searchpath, Global_defaultgamepath
    if Global_gamepath == "":
        Global_gamepath = Global_defaultgamepath
    config = configparser.ConfigParser()
    config['DEFAULT'] = {'filepath' : Global_gamepath, 'searchpath' : Global_searchpath}
    with open(Global_configpath, 'w') as configfile:
        config.write(configfile)
    
#endregion

#region Classes and Functions: Stingray Archives

class TocEntry:

    def __init__(self):
        self.FileID = self.TypeID = self.TocDataOffset = self.Unknown1 = self.GpuResourceOffset = self.Unknown2 = self.TocDataSize = self.GpuResourceSize = self.EntryIndex = self.StreamSize = self.StreamOffset = 0
        self.Unknown3 = 16
        self.Unknown4 = 64

        self.TocData =  self.TocData_OLD = b""
        self.GpuData =  self.GpuData_OLD = b""
        self.StreamData =  self.StreamData_OLD = b""

        # Custom Dev stuff
        self.LoadedData = None
        self.IsLoaded   = False
        self.IsModified = False
        self.IsCreated  = False # custom created, can be removed from archive
        self.IsSelected = False
        self.MaterialTemplate = None # for determining tuple to use for labeling textures in the material editor
        self.DEV_DrawIndex = -1
        self.VertexGroups = []
        self.Transforms = []
    # -- Serialize TocEntry -- #
    def Serialize(self, TocFile: MemoryStream, Index=0):
        self.FileID             = TocFile.uint64(self.FileID)
        self.TypeID             = TocFile.uint64(self.TypeID)
        self.TocDataOffset      = TocFile.uint64(self.TocDataOffset)
        self.StreamOffset       = TocFile.uint64(self.StreamOffset)
        self.GpuResourceOffset  = TocFile.uint64(self.GpuResourceOffset)
        self.Unknown1           = TocFile.uint64(self.Unknown1)
        self.Unknown2           = TocFile.uint64(self.Unknown2)
        self.TocDataSize        = TocFile.uint32(len(self.TocData))
        self.StreamSize         = TocFile.uint32(len(self.StreamData))
        self.GpuResourceSize    = TocFile.uint32(len(self.GpuData))
        self.Unknown3           = TocFile.uint32(self.Unknown3)
        self.Unknown4           = TocFile.uint32(self.Unknown4)
        self.EntryIndex         = TocFile.uint32(Index)
        return self

    # -- Write TocEntry Data -- #
    def SerializeData(self, TocFile: MemoryStream, GpuFile, StreamFile):
        if TocFile.IsReading():
            TocFile.seek(self.TocDataOffset)
            self.TocData = bytearray(self.TocDataSize)
        elif TocFile.IsWriting():
            self.TocDataOffset = TocFile.tell()
        self.TocData = TocFile.bytes(self.TocData)

        if GpuFile.IsWriting(): self.GpuResourceOffset = ceil(float(GpuFile.tell())/64)*64
        if self.GpuResourceSize > 0:
            GpuFile.seek(self.GpuResourceOffset)
            if GpuFile.IsReading(): self.GpuData = bytearray(self.GpuResourceSize)
            self.GpuData = GpuFile.bytes(self.GpuData)

        if StreamFile.IsWriting(): self.StreamOffset = ceil(float(StreamFile.tell())/64)*64
        if self.StreamSize > 0:
            StreamFile.seek(self.StreamOffset)
            if StreamFile.IsReading(): self.StreamData = bytearray(self.StreamSize)
            self.StreamData = StreamFile.bytes(self.StreamData)
        if GpuFile.IsReading():
            self.TocData_OLD    = bytearray(self.TocData)
            self.GpuData_OLD    = bytearray(self.GpuData)
            self.StreamData_OLD = bytearray(self.StreamData)

    # -- Get Data -- #
    def GetData(self):
        return [self.TocData, self.GpuData, self.StreamData]
    # -- Set Data -- #
    def SetData(self, TocData, GpuData, StreamData, IsModified=True):
        self.TocData = TocData
        self.GpuData = GpuData
        self.StreamData = StreamData
        self.TocDataSize     = len(self.TocData)
        self.GpuResourceSize = len(self.GpuData)
        self.StreamSize      = len(self.StreamData)
        self.IsModified = IsModified
    # -- Undo Modified Data -- #
    def UndoModifiedData(self):
        self.TocData = bytearray(self.TocData_OLD)
        self.GpuData = bytearray(self.GpuData_OLD)
        self.StreamData = bytearray(self.StreamData_OLD)
        self.TocDataSize     = len(self.TocData)
        self.GpuResourceSize = len(self.GpuData)
        self.StreamSize      = len(self.StreamData)
        self.IsModified = False
        if self.IsLoaded:
            self.Load(True, False)
    # -- Load Data -- #
    def Load(self, Reload=False, MakeBlendObject=True):
        callback = None
        if self.TypeID == MeshID: callback = LoadStingrayMesh
        if self.TypeID == TexID: callback = LoadStingrayTexture
        if self.TypeID == MaterialID: callback = LoadStingrayMaterial
        if self.TypeID == ParticleID: callback = LoadStingrayParticle
        if self.TypeID == CompositeMeshID: callback = LoadStingrayCompositeMesh
        if self.TypeID == Hash64("bones"): callback = LoadStingrayBones
        if callback == None: callback = LoadStingrayDump

        if callback != None:
            self.LoadedData = callback(self.FileID, self.TocData, self.GpuData, self.StreamData, Reload, MakeBlendObject)
            if self.LoadedData == None: raise Exception("Archive Entry Load Failed")
            self.IsLoaded   = True
            if self.TypeID == MeshID and not self.IsModified:
                for object in bpy.data.objects:
                    try:
                        objectID = object["Z_ObjectID"]
                        infoIndex = object["MeshInfoIndex"]
                        if objectID == str(self.FileID):
                            PrettyPrint(f"Writing Vertex Groups for {object.name}")
                            vertexNames = []
                            for group in object.vertex_groups:
                                vertexNames.append(group.name)
                            newGroups = [objectID, infoIndex, vertexNames]
                            if newGroups not in self.VertexGroups:
                                self.VertexGroups.append(newGroups)
                            PrettyPrint(self.VertexGroups)
                            PrettyPrint(f"Writing Transforms for {object.name}")
                            transforms = []
                            transforms.append(object.location)
                            transforms.append(object.rotation_euler)
                            transforms.append(object.scale)
                            objectTransforms = [objectID, infoIndex, transforms]
                            if objectTransforms not in self.Transforms:
                                self.Transforms.append(objectTransforms)
                            PrettyPrint(self.Transforms)
                    except:
                        PrettyPrint(f"Object: {object.name} has No HD2 Properties")

    # -- Write Data -- #
    def Save(self, **kwargs):
        if not self.IsLoaded: self.Load(True, False)
        if self.TypeID == MeshID: callback = SaveStingrayMesh
        if self.TypeID == TexID: callback = SaveStingrayTexture
        if self.TypeID == MaterialID: callback = SaveStingrayMaterial
        if self.TypeID == ParticleID: callback = SaveStingrayParticle
        if callback == None: callback = SaveStingrayDump

        if self.IsLoaded:
            if self.TypeID == MeshID:
                BlenderOpts = kwargs.get("BlenderOpts")
                data = callback(self, self.FileID, self.TocData, self.GpuData, self.StreamData, self.LoadedData, BlenderOpts)
            else:
                data = callback(self, self.FileID, self.TocData, self.GpuData, self.StreamData, self.LoadedData)
            self.SetData(data[0], data[1], data[2])
        return True

class TocFileType:
    def __init__(self, ID=0, NumFiles=0):
        self.unk1     = 0
        self.TypeID   = ID
        self.NumFiles = NumFiles
        self.unk2     = 16
        self.unk3     = 64
    def Serialize(self, TocFile: MemoryStream):
        self.unk1     = TocFile.uint64(self.unk1)
        self.TypeID   = TocFile.uint64(self.TypeID)
        self.NumFiles = TocFile.uint64(self.NumFiles)
        self.unk2     = TocFile.uint32(self.unk2)
        self.unk3     = TocFile.uint32(self.unk3)
        return self

class StreamToc:
    def __init__(self):
        self.magic      = self.numTypes = self.numFiles = self.unknown = 0
        self.unk4Data   = bytearray(56)
        self.TocTypes   = []
        self.TocEntries = []
        self.Path = ""
        self.Name = ""
        self.LocalName = ""

    def Serialize(self, SerializeData=True):
        # Create Toc Types Structs
        if self.TocFile.IsWriting():
            self.UpdateTypes()
        # Begin Serializing file
        self.magic      = self.TocFile.uint32(self.magic)
        if self.magic != 4026531857: return False

        self.numTypes   = self.TocFile.uint32(len(self.TocTypes))
        self.numFiles   = self.TocFile.uint32(len(self.TocEntries))
        self.unknown    = self.TocFile.uint32(self.unknown)
        self.unk4Data   = self.TocFile.bytes(self.unk4Data, 56)

        if self.TocFile.IsReading():
            self.TocTypes   = [TocFileType() for n in range(self.numTypes)]
            self.TocEntries = [TocEntry() for n in range(self.numFiles)]
        # serialize Entries in correct order
        self.TocTypes   = [Entry.Serialize(self.TocFile) for Entry in self.TocTypes]
        TocEntryStart   = self.TocFile.tell()
        if self.TocFile.IsReading(): self.TocEntries = [Entry.Serialize(self.TocFile) for Entry in self.TocEntries]
        else:
            Index = 1
            for Type in self.TocTypes:
                for Entry in self.TocEntries:
                    if Entry.TypeID == Type.TypeID:
                        Entry.Serialize(self.TocFile, Index)
                        Index += 1

        # Serialize Data
        if SerializeData:
            for FileEntry in self.TocEntries:
                FileEntry.SerializeData(self.TocFile, self.GpuFile, self.StreamFile)

        # re-write toc entry info with updated offsets
        if self.TocFile.IsWriting():
            self.TocFile.seek(TocEntryStart)
            Index = 1
            for Type in self.TocTypes:
                for Entry in self.TocEntries:
                    if Entry.TypeID == Type.TypeID:
                        Entry.Serialize(self.TocFile, Index)
                        Index += 1
        return True

    def UpdateTypes(self):
        self.TocTypes = []
        for Entry in self.TocEntries:
            exists = False
            for Type in self.TocTypes:
                if Type.TypeID == Entry.TypeID:
                    Type.NumFiles += 1; exists = True
                    break
            if not exists:
                self.TocTypes.append(TocFileType(Entry.TypeID, 1))

    def UpdatePath(self, path):
        self.Path = path
        self.Name = Path(path).name

    def FromFile(self, path, SerializeData=True):
        self.UpdatePath(path)
        with open(path, 'r+b') as f:
            self.TocFile = MemoryStream(f.read())

        self.GpuFile    = MemoryStream()
        self.StreamFile = MemoryStream()
        if SerializeData:
            if os.path.isfile(path+".gpu_resources"):
                with open(path+".gpu_resources", 'r+b') as f:
                    self.GpuFile = MemoryStream(f.read())
            if os.path.isfile(path+".stream"):
                with open(path+".stream", 'r+b') as f:
                    self.StreamFile = MemoryStream(f.read())
        return self.Serialize(SerializeData)

    def ToFile(self, path=None):
        self.TocFile = MemoryStream(IOMode = "write")
        self.GpuFile = MemoryStream(IOMode = "write")
        self.StreamFile = MemoryStream(IOMode = "write")
        self.Serialize()
        if path == None: path = self.Path

        with open(path, 'w+b') as f:
            f.write(bytes(self.TocFile.Data))
        with open(path+".gpu_resources", 'w+b') as f:
            f.write(bytes(self.GpuFile.Data))
        with open(path+".stream", 'w+b') as f:
            f.write(bytes(self.StreamFile.Data))

    def GetFileData(self, FileID, TypeID):
        for FileEntry in self.TocEntries:
            if FileEntry.FileID == FileID and FileEntry.TypeID == TypeID:
                return FileEntry.GetData()
        return None
    def GetEntry(self, FileID, TypeID):
        for Entry in self.TocEntries:
            if Entry.FileID == int(FileID) and Entry.TypeID == TypeID:
                return Entry
        return None
    def AddEntry(self, NewEntry):
        if self.GetEntry(NewEntry.FileID, NewEntry.TypeID) != None:
            raise Exception("Entry with same ID already exists")
        self.TocEntries.append(NewEntry)
        self.UpdateTypes()
    def RemoveEntry(self, FileID, TypeID):
        Entry = self.GetEntry(FileID, TypeID)
        if Entry != None:
            self.TocEntries.remove(Entry)
            self.UpdateTypes()

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
            for root, dirs, files in os.walk(Path(path).parent):
                for name in files:
                    if Path(name).suffix == "":
                        search_toc = StreamToc()
                        success = search_toc.FromFile(os.path.join(root, name), False)
                        if success:
                            self.SearchArchives.append(search_toc)

        return toc
    
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
                Entry = Archive.GetEntry(FileID, TypeID)
                if Entry != None:
                    return self.LoadArchive(Archive.Path, False).GetEntry(FileID, TypeID)
        return None

    def Load(self, FileID, TypeID, Reload=False, SearchAll=False):
        Entry = self.GetEntry(FileID, TypeID, SearchAll)
        if Entry != None: Entry.Load(Reload)

    def Save(self, FileID, TypeID):
        #ApplyAllTransforms(self, FileID)
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

#endregion

#region Classes and Functions: Stingray Materials
class ShaderVariable:
    klasses = {
        0: "Scalar",
        1: "Vector2",
        2: "Vector3",
        3: "Vector4",
        12: "Other"
    }
    
    def __init__(self):
        self.klass = self.klassName = self.elements = self.ID = self.offset = self.elementStride = 0
        self.values = []
        self.name = ""

class StingrayMaterial:
    def __init__(self):
        self.undat1 = self.undat3 = self.undat4 = self.undat5 = self.undat6 = self.RemainingData = bytearray()
        self.EndOffset = self.undat2 = self.ParentMaterialID = self.NumTextures = self.NumVariables = self.VariableDataSize = 0
        self.TexUnks = []
        self.TexIDs  = []
        self.ShaderVariables = []

        self.DEV_ShowEditor = False
        self.DEV_DDSPaths = []
    def Serialize(self, f: MemoryStream):
        self.undat1      = f.bytes(self.undat1, 12)
        self.EndOffset   = f.uint32(self.EndOffset)
        self.undat2      = f.uint64(self.undat2)
        self.ParentMaterialID= f.uint64(self.ParentMaterialID)
        self.undat3      = f.bytes(self.undat3, 32)
        self.NumTextures = f.uint32(self.NumTextures)
        self.undat4      = f.bytes(self.undat4, 36)
        self.NumVariables= f.uint32(self.NumVariables)
        self.undat5      = f.bytes(self.undat5, 12)
        self.VariableDataSize = f.uint32(self.VariableDataSize)
        self.undat6      = f.bytes(self.undat6, 12)
        if f.IsReading():
            self.TexUnks = [0 for n in range(self.NumTextures)]
            self.TexIDs = [0 for n in range(self.NumTextures)]
            self.ShaderVariables = [ShaderVariable() for n in range(self.NumVariables)]
        self.TexUnks = [f.uint32(TexUnk) for TexUnk in self.TexUnks]
        self.TexIDs  = [f.uint64(TexID) for TexID in self.TexIDs]
        for variable in self.ShaderVariables:
            variable.klass = f.uint32(variable.klass)
            variable.klassName = ShaderVariable.klasses[variable.klass]
            variable.elements = f.uint32(variable.elements)
            variable.ID = f.uint32(variable.ID)
            if variable.ID in Global_ShaderVariables:
                variable.name = Global_ShaderVariables[variable.ID]
            variable.offset = f.uint32(variable.offset)
            variable.elementStride = f.uint32(variable.elementStride)
            if f.IsReading():
                variable.values = [0 for n in range(variable.klass + 1)]  # Create an array with the length of the data which is one greater than the klass value
        
        variableValueLocation = f.Location # Record and add all of the extra data that is skipped around during the variable offsets
        if f.IsReading():self.RemainingData = f.bytes(self.RemainingData, len(f.Data) - f.tell())
        if f.IsWriting():self.RemainingData = f.bytes(self.RemainingData)
        f.Location = variableValueLocation

        for variable in self.ShaderVariables:
            oldLocation = f.Location
            f.Location = f.Location + variable.offset
            for idx in range(len(variable.values)):
                variable.values[idx] = f.float32(variable.values[idx])
            f.Location = oldLocation

        self.EditorUpdate()

    def EditorUpdate(self):
        self.DEV_DDSPaths = [None for n in range(len(self.TexIDs))]

def LoadStingrayMaterial(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    exists = True
    force_reload = False
    try:
        mat = bpy.data.materials[str(ID)]
        force_reload = True
    except: exists = False


    f = MemoryStream(TocData)
    Material = StingrayMaterial()
    Material.Serialize(f)
    if MakeBlendObject and not (exists and not Reload): AddMaterialToBlend(ID, Material, Reload)
    elif force_reload: AddMaterialToBlend(ID, Material, True)
    return Material

def SaveStingrayMaterial(self, ID, TocData, GpuData, StreamData, LoadedData):
    if self.MaterialTemplate != None:
        texturesFilepaths = GenerateMaterialTextures(self)
    mat = LoadedData
    index = 0
    for TexIdx in range(len(mat.TexIDs)):
        oldTexID = mat.TexIDs[TexIdx]
        if mat.DEV_DDSPaths[TexIdx] != None:
            # get texture data
            StingrayTex = StingrayTexture()
            with open(mat.DEV_DDSPaths[TexIdx], 'r+b') as f:
                StingrayTex.FromDDS(f.read())
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture entry to archive
            Entry = TocEntry()
            Entry.FileID = RandomHash16()
            Entry.TypeID = TexID
            Entry.IsCreated = True
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)
            Global_TocManager.AddNewEntryToPatch(Entry)
            mat.TexIDs[TexIdx] = Entry.FileID
        else:
            Global_TocManager.Load(int(mat.TexIDs[TexIdx]), TexID, False, True)
            Entry = Global_TocManager.GetEntry(int(mat.TexIDs[TexIdx]), TexID, True)
            if Entry != None:
                Entry = deepcopy(Entry)
                Entry.FileID = RandomHash16()
                Entry.IsCreated = True
                Global_TocManager.AddNewEntryToPatch(Entry)
                mat.TexIDs[TexIdx] = Entry.FileID
        if self.MaterialTemplate != None:
            path = texturesFilepaths[index]
            if not os.path.exists(path):
                raise Exception(f"Could not find file at path: {path}")
            if not Entry:
                raise Exception(f"Could not find or generate texture entry ID: {int(mat.TexIDs[TexIdx])}")
            
            if path.endswith(".dds"):
                SaveImageDDS(path, Entry.FileID)
            else:
                SaveImagePNG(path, Entry.FileID)
        Global_TocManager.RemoveEntryFromPatch(oldTexID, TexID)
        index += 1
    f = MemoryStream(IOMode="write")
    LoadedData.Serialize(f)
    return [f.Data, b"", b""]

def AddMaterialToBlend(ID, StingrayMat, EmptyMatExists=False):
    try:
        mat = bpy.data.materials[str(ID)]
        PrettyPrint(f"Found material for ID: {ID} Skipping creation of new material")
        return
    except:
        PrettyPrint(f"Unable to find material in blender scene for ID: {ID} creating new material")
        mat = bpy.data.materials.new(str(ID)); mat.name = str(ID)

    r.seed(ID)
    mat.diffuse_color = (r.random(), r.random(), r.random(), 1)
    mat.use_nodes = True
    #bsdf = mat.node_tree.nodes["Principled BSDF"] # It's not even used?

    Entry = Global_TocManager.GetEntry(int(ID), MaterialID)
    if Entry == None:
        PrettyPrint(f"No Entry Found when getting Material ID: {ID}", "ERROR")
        return
    if Entry.MaterialTemplate != None: CreateAddonMaterial(ID, StingrayMat, mat, Entry)
    else: CreateGameMaterial(StingrayMat, mat)
    
def CreateGameMaterial(StingrayMat, mat):
    for node in mat.node_tree.nodes:
        if node.bl_idname == 'ShaderNodeTexImage':
            mat.node_tree.nodes.remove(node)
    idx = 0
    height = round(len(StingrayMat.TexIDs) * 300 / 2)
    for TextureID in StingrayMat.TexIDs:
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.location = (-450, height - 300*idx)

        try:    bpy.data.images[str(TextureID)]
        except: Global_TocManager.Load(TextureID, TexID, False, True)
        try: texImage.image = bpy.data.images[str(TextureID)]
        except:
            PrettyPrint(f"Failed to load texture {TextureID}. This is not fatal, but does mean that the materials in Blender will have empty image texture nodes", "warn")
            pass
        idx +=1

def CreateAddonMaterial(ID, StingrayMat, mat, Entry):
    mat.node_tree.nodes.clear()
    output = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (200, 300)
    group = mat.node_tree.nodes.new('ShaderNodeGroup')
    treeName = f"{Entry.MaterialTemplate}-{str(ID)}"
    nodeTree = bpy.data.node_groups.new(treeName, 'ShaderNodeTree')
    group.node_tree = nodeTree
    group.location = (0, 300)

    group_input = nodeTree.nodes.new('NodeGroupInput')
    group_input.location = (-400,0)
    group_output = nodeTree.nodes.new('NodeGroupOutput')
    group_output.location = (400,0)

    idx = 0
    height = round(len(StingrayMat.TexIDs) * 300 / 2)
    TextureNodes = []
    for TextureID in StingrayMat.TexIDs:
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.location = (-450, height - 300*idx)

        TextureNodes.append(texImage)

        name = TextureTypeLookup[Entry.MaterialTemplate][idx]
        socket_type = "NodeSocketColor"
        nodeTree.interface.new_socket(name=name, in_out ="INPUT", socket_type=socket_type).hide_value = True

        try:    bpy.data.images[str(TextureID)]
        except: Global_TocManager.Load(TextureID, TexID, False, True)
        try: texImage.image = bpy.data.images[str(TextureID)]
        except:
            PrettyPrint(f"Failed to load texture {TextureID}. This is not fatal, but does mean that the materials in Blender will have empty image texture nodes", "warn")
            pass
        
        if "Normal" in name:
            texImage.image.colorspace_settings.name = 'Non-Color'

        mat.node_tree.links.new(texImage.outputs['Color'], group.inputs[idx])
        idx +=1

    nodeTree.interface.new_socket(name="Surface",in_out ="OUTPUT", socket_type="NodeSocketShader")

    nodes = mat.node_tree.nodes
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            nodes.remove(node)
        elif node.type == 'OUTPUT_MATERIAL':
             mat.node_tree.links.new(group.outputs['Surface'], node.inputs['Surface'])
    
    inputNode = nodeTree.nodes.get('Group Input')
    outputNode = nodeTree.nodes.get('Group Output')
    bsdf = nodeTree.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (50, 0)
    separateColor = nodeTree.nodes.new('ShaderNodeSeparateColor')
    separateColor.location = (-150, 0)
    normalMap = nodeTree.nodes.new('ShaderNodeNormalMap')
    normalMap.location = (-150, -150)

    bsdf.inputs['IOR'].default_value = 1
    bsdf.inputs['Emission Strength'].default_value = 1

    bpy.ops.file.unpack_all(method='REMOVE')
    
    PrettyPrint(f"Setting up any custom templates. Current Template: {Entry.MaterialTemplate}")

    if Entry.MaterialTemplate == "basic": SetupBasicBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap)
    elif Entry.MaterialTemplate == "basic+": SetupBasicBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap)
    elif Entry.MaterialTemplate == "original": SetupOriginalBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap)
    elif Entry.MaterialTemplate == "emissive": SetupEmissiveBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap)
    elif Entry.MaterialTemplate == "alphaclip": SetupAlphaClipBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, mat)
    elif Entry.MaterialTemplate == "advanced": SetupAdvancedBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, TextureNodes, group, mat)
    elif Entry.MaterialTemplate == "translucent": SetupTranslucentBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, mat)
    
def SetupBasicBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap):
    bsdf.inputs['Emission Strength'].default_value = 0
    inputNode.location = (-750, 0)
    SetupNormalMapTemplate(nodeTree, inputNode, normalMap, bsdf)
    nodeTree.links.new(inputNode.outputs['Base Color'], bsdf.inputs['Base Color'])
    nodeTree.links.new(inputNode.outputs['PBR'], separateColor.inputs['Color'])
    nodeTree.links.new(separateColor.outputs['Red'], bsdf.inputs['Metallic'])
    nodeTree.links.new(separateColor.outputs['Green'], bsdf.inputs['Roughness'])
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])

def SetupOriginalBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap):
    inputNode.location = (-800, -0)
    SetupNormalMapTemplate(nodeTree, inputNode, normalMap, bsdf)
    nodeTree.links.new(inputNode.outputs['Base Color'], bsdf.inputs['Base Color'])
    nodeTree.links.new(inputNode.outputs['Emission'], bsdf.inputs['Emission Color'])
    nodeTree.links.new(inputNode.outputs['PBR'], separateColor.inputs['Color'])
    nodeTree.links.new(separateColor.outputs['Red'], bsdf.inputs['Metallic'])
    nodeTree.links.new(separateColor.outputs['Green'], bsdf.inputs['Roughness'])
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])

def SetupEmissiveBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap):
    nodeTree.links.new(inputNode.outputs['Base Color/Metallic'], bsdf.inputs['Base Color'])
    nodeTree.links.new(inputNode.outputs['Emission'], bsdf.inputs['Emission Color'])
    nodeTree.links.new(inputNode.outputs['Normal/AO/Roughness'], separateColor.inputs['Color'])
    nodeTree.links.new(separateColor.outputs['Red'], normalMap.inputs['Color'])
    nodeTree.links.new(normalMap.outputs['Normal'], bsdf.inputs['Normal'])
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])

def SetupAlphaClipBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, mat):
    bsdf.inputs['Emission Strength'].default_value = 0
    combineColor = nodeTree.nodes.new('ShaderNodeCombineColor')
    combineColor.inputs['Blue'].default_value = 1
    combineColor.location = (-350, -150)
    separateColor.location = (-550, -150)
    inputNode.location = (-750, 0)
    mat.blend_method = 'CLIP'
    nodeTree.links.new(inputNode.outputs['Base Color/Metallic'], bsdf.inputs['Base Color'])
    nodeTree.links.new(inputNode.outputs['Alpha Mask'], bsdf.inputs['Alpha'])
    nodeTree.links.new(inputNode.outputs['Normal/AO/Roughness'], separateColor.inputs['Color'])
    nodeTree.links.new(separateColor.outputs['Red'], combineColor.inputs['Red'])
    nodeTree.links.new(separateColor.outputs['Green'], combineColor.inputs['Green'])
    nodeTree.links.new(combineColor.outputs['Color'], normalMap.inputs['Color'])
    nodeTree.links.new(normalMap.outputs['Normal'], bsdf.inputs['Normal'])
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])

def SetupNormalMapTemplate(nodeTree, inputNode, normalMap, bsdf):
    separateColorNormal = nodeTree.nodes.new('ShaderNodeSeparateColor')
    separateColorNormal.location = (-550, -150)
    combineColorNormal = nodeTree.nodes.new('ShaderNodeCombineColor')
    combineColorNormal.location = (-350, -150)
    combineColorNormal.inputs['Blue'].default_value = 1
    nodeTree.links.new(inputNode.outputs['Normal'], separateColorNormal.inputs['Color'])
    nodeTree.links.new(separateColorNormal.outputs['Red'], combineColorNormal.inputs['Red'])
    nodeTree.links.new(separateColorNormal.outputs['Green'], combineColorNormal.inputs['Green'])
    nodeTree.links.new(combineColorNormal.outputs['Color'], normalMap.inputs['Color'])
    nodeTree.links.new(normalMap.outputs['Normal'], bsdf.inputs['Normal'])

def SetupAdvancedBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, TextureNodes, group, mat):
    bsdf.inputs['Emission Strength'].default_value = 0
    TextureNodes[5].image.colorspace_settings.name = 'Non-Color'
    nodeTree.nodes.remove(separateColor)
    inputNode.location = (-750, 0)
    separateColorNormal = nodeTree.nodes.new('ShaderNodeSeparateColor')
    separateColorNormal.location = (-550, -150)
    combineColorNormal = nodeTree.nodes.new('ShaderNodeCombineColor')
    combineColorNormal.location = (-350, -150)
    combineColorNormal.inputs['Blue'].default_value = 1
    nodeTree.links.new(inputNode.outputs['Normal/AO/Roughness'], separateColorNormal.inputs['Color'])
    nodeTree.links.new(separateColorNormal.outputs['Red'], combineColorNormal.inputs['Red'])
    nodeTree.links.new(separateColorNormal.outputs['Green'], combineColorNormal.inputs['Green'])
    nodeTree.links.new(normalMap.outputs['Normal'], bsdf.inputs['Normal'])
    nodeTree.links.new(combineColorNormal.outputs['Color'], normalMap.inputs['Color'])
    nodeTree.links.new(inputNode.outputs['Color/Emission Mask'], bsdf.inputs['Base Color'])
    nodeTree.links.new(inputNode.outputs['Metallic'], bsdf.inputs['Metallic'])

    RoughnessSocket = nodeTree.interface.new_socket(name="Normal/AO/Roughness (Alpha)", in_out ="INPUT", socket_type="NodeSocketFloat").hide_value = True
    mat.node_tree.links.new(TextureNodes[2].outputs['Alpha'], group.inputs['Normal/AO/Roughness (Alpha)'])
    nodeTree.links.new(inputNode.outputs['Normal/AO/Roughness (Alpha)'], bsdf.inputs['Roughness'])

    multiplyEmission = nodeTree.nodes.new('ShaderNodeMath')
    multiplyEmission.location = (-350, -350)
    multiplyEmission.operation = 'MULTIPLY'
    multiplyEmission.inputs[1].default_value = 0
    nodeTree.interface.new_socket(name="Color/Emission Mask (Alpha)", in_out ="INPUT", socket_type="NodeSocketFloat").hide_value = True
    mat.node_tree.links.new(TextureNodes[5].outputs['Alpha'], group.inputs['Color/Emission Mask (Alpha)'])
    nodeTree.links.new(inputNode.outputs['Color/Emission Mask (Alpha)'], multiplyEmission.inputs[0])
    nodeTree.links.new(multiplyEmission.outputs['Value'], bsdf.inputs['Emission Strength'])
    
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])

def SetupTranslucentBlenderMaterial(nodeTree, inputNode, outputNode, bsdf, separateColor, normalMap, mat):
    bsdf.inputs['Emission Strength'].default_value = 0
    nodeTree.nodes.remove(separateColor)
    inputNode.location = (-750, 0)
    SetupNormalMapTemplate(nodeTree, inputNode, normalMap, bsdf)
    nodeTree.links.new(bsdf.outputs['BSDF'], outputNode.inputs['Surface'])
    mat.blend_method = 'BLEND'
    bsdf.inputs['Alpha'].default_value = 0.02
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)

def CreateGenericMaterial(ID, StingrayMat, mat):
    idx = 0
    for TextureID in StingrayMat.TexIDs:
        # Create Node
        texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
        texImage.location = (-450, 850 - 300*idx)

        # Load Texture
        Global_TocManager.Load(TextureID, TexID, False, True)
        # Apply Texture
        try: texImage.image = bpy.data.images[str(TextureID)]
        except:
            PrettyPrint(f"Failed to load texture {TextureID}. This is not fatal, but does mean that the materials in Blender will have empty image texture nodes", "warn")
            pass
        idx +=1

def AddMaterialToBlend_EMPTY(ID):
    try:
        bpy.data.materials[str(ID)]
    except:
        mat = bpy.data.materials.new(str(ID)); mat.name = str(ID)
        r.seed(ID)
        mat.diffuse_color = (r.random(), r.random(), r.random(), 1)

def GenerateMaterialTextures(Entry):
    material = group = None
    for mat in bpy.data.materials:
        if mat.name == str(Entry.FileID):
            material = mat
            break
    if material == None:
        raise Exception(f"Material Could not be Found ID: {Entry.FileID} {bpy.data.materials}")
    PrettyPrint(f"Found Material {material.name} {material}")
    for node in material.node_tree.nodes:
        if node.type == 'GROUP':
            group = node
            break
    if group == None:
        raise Exception("Could not find node group within material")
    filepaths = []
    for input_socket in group.inputs:
        PrettyPrint(input_socket.name)
        if input_socket.is_linked:
            for link in input_socket.links:
                image = link.from_node.image
                tempdir = tempfile.gettempdir()
                extension = str(image.file_format).lower()
                if (extension == "dds" or extension == "") and not os.path.exists(image.filepath):
                    raise Exception(f"Selected texture: {image.name} is a DDS image and its filepath cannot be found. Please manually apply any DDS textures to the patch after saving the material by right clicking on the texture entry and Importing the DDS file.")
                path = f"{tempdir}\\{image.name.split('.')[0]}.{extension}"
                oldPath = image.filepath
                if not os.path.exists(image.filepath):
                    PrettyPrint(f"Saving image at path: {path} This might destroy color data.", "warn")
                    try:
                        image.save(filepath=path)
                        filepaths.append(path)
                    except Exception as e:
                        PrettyPrint(f"Failed to save image at path. {e}", "error")
                        PrettyPrint(f"Setting image path to old path: {oldPath}")
                        filepaths.append(oldPath)
                else:
                    filepaths.append(oldPath)

                # enforce proper colorspace for abnormal stingray textures
                if "Normal" in input_socket.name or "Color/Emission Mask" in input_socket.name:
                     image.colorspace_settings.name = 'Non-Color'
    
    # display proper emissives on advanced material
    if "advanced" in group.node_tree.name:
        colorVariable = Entry.LoadedData.ShaderVariables[32].values
        emissionColor = (colorVariable[0], colorVariable[1], colorVariable[2], 1)
        emissionStrength = Entry.LoadedData.ShaderVariables[40].values[0]
        emissionStrength = max(0, emissionStrength)
        PrettyPrint(f"Emission color: {emissionColor} Strength: {emissionStrength}")
        for node in group.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Emission Color'].default_value = emissionColor
            if node.type == 'MATH' and node.operation == 'MULTIPLY':
                node.inputs[1].default_value = emissionStrength

    # update color and alpha of translucent
    if "translucent" in group.node_tree.name:
        colorVariable = Entry.LoadedData.ShaderVariables[7].values
        baseColor = (colorVariable[0], colorVariable[1], colorVariable[2], 1)
        alphaVariable = Entry.LoadedData.ShaderVariables[1].values[0]
        PrettyPrint(f"Base color: {baseColor} Alpha: {alphaVariable}")
        for node in group.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = baseColor
                node.inputs['Alpha'].default_value = alphaVariable

    PrettyPrint(f"Found {len(filepaths)} Images: {filepaths}")
    return filepaths

#endregion

#region Classes and Functions: Stingray Textures

class StingrayMipmapInfo:
    def __init__(self):
        self.Start     = self.BytesLeft = self.Height = self.Width  = 0
    def Serialize(self, Toc):
        self.Start      = Toc.uint32(self.Start)
        self.BytesLeft  = Toc.uint32(self.BytesLeft)
        self.Height     = Toc.uint16(self.Height)
        self.Width      = Toc.uint16(self.Width)
        return self

class StingrayTexture:
    def __init__(self):
        self.UnkID = self.Unk1  = self.Unk2  = 0
        self.MipMapInfo = []

        self.ddsHeader = bytearray(148)
        self.rawTex    = b""

        self.Format     = ""
        self.Width      = 0
        self.Height     = 0
        self.NumMipMaps = 0
        self.ArraySize  = 0
    def Serialize(self, Toc: MemoryStream, Gpu, Stream):
        # clear header, so we dont have to deal with the .stream file
        if Toc.IsWriting():
            self.Unk1 = 0; self.Unk2  = 0xFFFFFFFF
            self.MipMapInfo = [StingrayMipmapInfo() for n in range(15)]

        self.UnkID = Toc.uint32(self.UnkID)
        self.Unk1  = Toc.uint32(self.Unk1)
        self.Unk2  = Toc.uint32(self.Unk2)
        if Toc.IsReading(): self.MipMapInfo = [StingrayMipmapInfo() for n in range(15)]
        self.MipMapInfo = [mipmapInfo.Serialize(Toc) for mipmapInfo in self.MipMapInfo]
        self.ddsHeader  = Toc.bytes(self.ddsHeader, 148)
        self.ParseDDSHeader()

        if Toc.IsWriting():
            Gpu.bytes(self.rawTex)
        else:# IsReading
            if len(Stream.Data) > 0:
                self.rawTex = Stream.Data
            else:
                self.rawTex = Gpu.Data

    def ToDDSArray(self):
        modifiedHeader = self.ddsHeader[:140] + bytes([1]) + self.ddsHeader[141:]
        TextureArray = []
        dataLength = len(self.rawTex) / self.ArraySize
        for idx in range(self.ArraySize):
            startIndex = int(dataLength * idx)
            endIndex = int(startIndex + dataLength)
            dds = modifiedHeader + self.rawTex[startIndex:endIndex:]
            TextureArray.append(dds)
        return TextureArray
        
    def ToDDS(self):
        return self.ddsHeader + self.rawTex
    
    def FromDDS(self, dds):
        self.ddsHeader = dds[:148]
        self.rawTex    = dds[148::]
    
    def ParseDDSHeader(self):
        dds = MemoryStream(self.ddsHeader, IOMode="read")
        dds.seek(84)
        Header = dds.read(4)
        DX10Header = b"DX10"
        if Header != DX10Header:
            raise Exception(f"DDS must use dx10 extended header. Got: {Header}")
        dds.seek(12)
        self.Height = dds.uint32(0)
        self.Width  = dds.uint32(0)
        dds.seek(28)
        self.NumMipMaps = dds.uint32(0)
        dds.seek(128)
        self.Format = DXGI_FORMAT(dds.uint32(0))
        dds.seek(140)
        self.ArraySize = dds.uint32(0)
    
    def CalculateGpuMipmaps(self):
        Stride = DXGI_FORMAT_SIZE(self.Format) / 16
        start_mip = max(1, self.NumMipMaps-6)

        CurrentWidth = self.Width
        CurrentSize = int((self.Width*self.Width)*Stride)
        for mip in range(self.NumMipMaps-1):
            if mip+1 == start_mip:
                return CurrentSize

            if CurrentWidth > 4: CurrentWidth /= 2
            CurrentSize += int((CurrentWidth*CurrentWidth)*Stride)

def LoadStingrayTexture(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    exists = True
    try: bpy.data.images[str(ID)]
    except: exists = False

    StingrayTex = StingrayTexture()
    StingrayTex.Serialize(MemoryStream(TocData), MemoryStream(GpuData), MemoryStream(StreamData))
    dds = StingrayTex.ToDDS()

    if MakeBlendObject and not (exists and not Reload):
        tempdir = tempfile.gettempdir()
        dds_path = f"{tempdir}\\{ID}.dds"
        png_path = f"{tempdir}\\{ID}.png"

        with open(dds_path, 'w+b') as f:
            f.write(dds)
        
        subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "png", "-f", "R8G8B8A8_UNORM", "-sepalpha", "-alpha", dds_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        if os.path.isfile(png_path):
            image = bpy.data.images.load(png_path)
            image.name = str(ID)
            image.pack()
        else:
            raise Exception(f"Failed to convert texture {ID} to PNG, or DDS failed to export")
    
    return StingrayTex

def BlendImageToStingrayTexture(image, StingrayTex):
    tempdir  = tempfile.gettempdir()
    dds_path = f"{tempdir}\\blender_img.dds"
    tga_path = f"{tempdir}\\blender_img.tga"

    image.file_format = 'TARGA_RAW'
    image.filepath_raw = tga_path
    image.save()

    subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-f", StingrayTex.Format, "-sepalpha", "-alpha", dds_path], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    
    if os.path.isfile(dds_path):
        with open(dds_path, 'r+b') as f:
            StingrayTex.FromDDS(f.read())
    else:
        raise Exception("Failed to convert TGA to DDS")

def SaveStingrayTexture(self, ID, TocData, GpuData, StreamData, LoadedData):
    exists = True
    try: bpy.data.images[str(ID)]
    except: exists = False

    Toc = MemoryStream(IOMode="write")
    Gpu = MemoryStream(IOMode="write")
    Stream = MemoryStream(IOMode="write")

    LoadedData.Serialize(Toc, Gpu, Stream)

    return [Toc.Data, Gpu.Data, Stream.Data]

#endregion

#region Classes and Functions: Stingray Bones

class StingrayBones:
    def __init__(self):
        self.NumNames = self.NumLODLevels = self.Unk1 = 0
        self.UnkArray1 = []; self.BoneHashes = []; self.LODLevels = []; self.Names = []
    def Serialize(self, f: MemoryStream):
        self.NumNames = f.uint32(self.NumNames)
        self.NumLODLevels   = f.uint32(self.NumLODLevels)
        if f.IsReading():
            self.UnkArray1 = [0 for n in range(self.NumLODLevels)]
            self.BoneHashes = [0 for n in range(self.NumNames)]
            self.LODLevels = [0 for n in range(self.NumLODLevels)]
        self.UnkArray1 = [f.float32(value) for value in self.UnkArray1]
        self.BoneHashes = [f.uint32(value) for value in self.BoneHashes]
        self.LODLevels = [f.uint32(value) for value in self.LODLevels]
        if f.IsReading():
            Data = f.read().split(b"\x00")
            self.Names = [dat.decode() for dat in Data]
            if self.Names[-1] == '':
                self.Names.pop() # remove extra empty string element
        else:
            Data = b""
            for string in self.Names:
                Data += string.encode() + b"\x00"
            f.write(Data)

        # add to global bone hashes
        if f.IsReading():
            PrettyPrint("Adding Bone Hashes to global list")
            global Global_BoneNames
            if len(self.BoneHashes) == len(self.Names):
                for idx in range(len(self.BoneHashes)):
                    Global_BoneNames[self.BoneHashes[idx]] = self.Names[idx]
            else:
                PrettyPrint(f"Failed to add bone hashes as list length is misaligned. Hashes Length: {len(self.BoneHashes)} Names Length: {len(self.Names)} Hashes: {self.BoneHashes} Names: {self.Names}", "error")
        return self

def LoadStingrayBones(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayBonesData = StingrayBones()
    StingrayBonesData.Serialize(MemoryStream(TocData))
    return StingrayBonesData

#endregion

#region Classes and Functions: Stingray Composite Meshes

class StingrayCompositeMesh:
    def __init__(self):
        self.unk1 = self.NumExternalMeshes = self.StreamInfoOffset = 0
        self.Unreversed = bytearray()
        self.NumStreams = 0
        self.StreamInfoArray = []
        self.StreamInfoOffsets = []
        self.StreamInfoUnk = []
        self.StreamInfoUnk2 = 0
        self.GpuData = None
    def Serialize(self, f: MemoryStream, gpu):
        self.unk1               = f.uint64(self.unk1)
        self.NumExternalMeshes  = f.uint32(self.NumExternalMeshes)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        if f.IsReading():
            self.Unreversed = bytearray(self.StreamInfoOffset-f.tell())
        self.Unreversed     = f.bytes(self.Unreversed)

        if f.IsReading(): f.seek(self.StreamInfoOffset)
        else:
            f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
        self.NumStreams = f.uint32(len(self.StreamInfoArray))
        if f.IsWriting():
            if not redo_offsets: self.StreamInfoOffsets = [0 for n in range(self.NumStreams)]
            self.StreamInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
        if f.IsReading():
            self.StreamInfoOffsets = [0 for n in range(self.NumStreams)]
            self.StreamInfoUnk     = [0 for n in range(self.NumStreams)]
            self.StreamInfoArray   = [StreamInfo() for n in range(self.NumStreams)]

        self.StreamInfoOffsets  = [f.uint32(Offset) for Offset in self.StreamInfoOffsets]
        self.StreamInfoUnk      = [f.uint32(Unk) for Unk in self.StreamInfoUnk]
        self.StreamInfoUnk2     = f.uint32(self.StreamInfoUnk2)
        for stream_idx in range(self.NumStreams):
            if f.IsReading(): f.seek(self.StreamInfoOffset + self.StreamInfoOffsets[stream_idx])
            else            : self.StreamInfoOffsets[stream_idx] = f.tell() - self.StreamInfoOffset
            self.StreamInfoArray[stream_idx] = self.StreamInfoArray[stream_idx].Serialize(f)

        self.GpuData = gpu
        return self

def LoadStingrayCompositeMesh(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    raise Exception("Composite Meshes Are Not Yet Supported")
    StingrayCompositeMeshData = StingrayCompositeMesh()
    StingrayCompositeMeshData.Serialize(MemoryStream(TocData), MemoryStream(GpuData))
    return StingrayCompositeMeshData

#endregion

#region StingrayParticles

class StingrayParticles:
    def __init__(self):
        self.magic = 0
        self.minLifetime = 0
        self.maxLifetime = 0
        self.unk1 = 0
        self.unk2 = 0
        self.numVariables = 0
        self.numParticleSystems = 0
        self.ParticleVariableHashes = []
        self.ParticleVariablePositions = []
        self.ParticleSystems = []

    def Serialize(self, f: MemoryStream):
        PrettyPrint("Serializing Particle")
        self.magic = f.uint32(self.magic)
        self.minLifetime = f.float32(self.minLifetime)
        self.maxLifetime = f.float32(self.maxLifetime)
        self.unk1 = f.uint32(self.unk1)
        self.unk2 = f.uint32(self.unk2)
        self.numVariables = f.uint32(self.numVariables)
        self.numParticleSystems = f.uint32(self.numParticleSystems)
        f.seek(f.tell() + 44)
        if f.IsReading():
            self.ParticleVariableHashes = [0 for n in range(self.numVariables)]
            self.ParticleVariablePositions = [[0, 0, 0] for n in range(self.numVariables)]
            self.ParticleSystems = [ParticleSystem() for n in range(self.numParticleSystems)]
        
        self.ParticleVariableHashes = [f.uint32(hash) for hash in self.ParticleVariableHashes]
        self.ParticleVariablePositions = [f.vec3_float(position) for position in self.ParticleVariablePositions]

        for system in self.ParticleSystems:
            system.Serialize(f)
        
        #Debug Print
        PrettyPrint(f"Particle System: {vars(self)}")
        PrettyPrint(f"Systems:")
        for system in self.ParticleSystems: 
            PrettyPrint(vars(system))
            PrettyPrint(f"Rotation: {vars(system.Rotation)}")
            PrettyPrint(f"Components: {vars(system.ComponentList)}")

class ParticleSystem:
    def __init__(self):
        self.maxNumParticles = 0
        self.numComponents = 0
        self.unk2 = 0
        self.componentBitFlags = []
        self.unk3 = 0
        self.unk4 = 0
        self.unk5 = 0
        self.unk6 = 0
        self.type1 = 0
        self.type2 = 0
        self.Rotation = ParticleRotation()
        self.unknown = []
        self.unk7 = 0
        self.componentListOffset = 0
        self.unk8 = 0
        self.componentListSize = 0
        self.unk9 = 0
        self.unk10 = 0
        self.offset3 = 0
        self.particleSystemSize = 0
        self.ComponentList = ComponentList()

    def Serialize(self, f: MemoryStream):
        PrettyPrint("Serializing Particle System")
        startOffset = f.tell()
        self.maxNumParticles = f.uint32(self.maxNumParticles)
        self.numComponents = f.uint32(self.numComponents)
        self.unk2 = f.uint32(self.unk2)
        if f.IsReading():
            self.componentBitFlags = [0 for n in range(self.numComponents)]
        self.componentBitFlags = [f.uint32(flag) for flag in self.componentBitFlags]
        f.seek(f.tell() + (64 - 4 * self.numComponents))
        self.unk3 = f.uint32(self.unk3)
        self.unk4 = f.uint32(self.unk4)
        f.seek(f.tell() + 8)
        self.unk5 = f.uint32(self.unk5)
        f.seek(f.tell() + 4)
        self.unk6 = f.uint32(self.unk6)
        f.seek(f.tell() + 4)
        self.type1 = f.uint32(self.type1)
        self.type2 = f.uint32(self.type2)
        f.seek(f.tell() + 4)
        self.Rotation.Serialize(f)
        if f.IsReading():
            self.unknown = [0 for n in range(11)]
        self.unknown = [f.float32(n) for n in self.unknown]
        self.unk7 = f.uint32(self.unk7)
        self.componentListOffset = f.uint32(self.componentListOffset)
        self.unk8 = f.uint32(self.unk8)
        self.componentListSize = f.uint32(self.componentListSize)
        self.unk9 = f.uint32(self.unk9)
        self.unk10 = f.uint32(self.unk10)
        self.offset3 = f.uint32(self.offset3)
        self.particleSystemSize = f.uint32(self.particleSystemSize)
        f.seek(startOffset + self.componentListOffset)
        if (self.unk3 == 0xFFFFFFFF): #non-rendering particle system
            f.seek(startOffset + self.particleSystemSize)
            return
        self.ComponentList.Serialize(self, f)
        f.seek(startOffset + self.particleSystemSize)

class ParticleRotation:
    def __init__(self):
        self.xRow = [0 for n in range(3)]
        self.yRow = [0 for n in range(3)]
        self.zRow = [0 for n in range(3)]
        self.unk = [0 for n in range(16)]

    def Serialize(self, f: MemoryStream):
        self.xRow = [f.float32(x) for x in self.xRow]
        f.seek(f.tell() + 4)
        self.yRow = [f.float32(y) for y in self.yRow]
        f.seek(f.tell() + 4)
        self.zRow = [f.float32(z) for z in self.zRow]
        f.seek(f.tell() + 4)
        self.unk = [f.uint8(n) for n in self.unk]

class ComponentList:
    def __init__(self):
        self.componentList = []
    
    def Serialize(self, particleSystem: ParticleSystem, f: MemoryStream):
        size = particleSystem.componentListSize - particleSystem.componentListOffset
        if f.IsReading():
            self.componentList = [0 for n in range(size)]
        self.componentList = [f.uint8(component) for component in self.componentList]

def LoadStingrayParticle(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    f = MemoryStream(TocData)
    Particle = StingrayParticles()
    Particle.Serialize(f)
    return Particle

def SaveStingrayParticle(self, ID, TocData, GpuData, StreamData, LoadedData):
    f = MemoryStream(TocData, IOMode="write") # Load in original TocData before overwriting it
    LoadedData.Serialize(f)
    return [f.Data, b"", b""]

#endregion

#region StingrayRawDump

class StingrayRawDump:
    def __init__(self):
        return None

    def Serialize(self, f: MemoryStream):
        return self

def LoadStingrayDump(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    StingrayDumpData = StingrayRawDump()
    StingrayDumpData.Serialize(MemoryStream(TocData))
    return StingrayDumpData

def SaveStingrayDump(self, ID, TocData, GpuData, StreamData, LoadedData):
    Toc = MemoryStream(IOMode="write")
    Gpu = MemoryStream(IOMode="write")
    Stream = MemoryStream(IOMode="write")

    LoadedData.Serialize(Toc, Gpu, Stream)

    return [Toc.Data, Gpu.Data, Stream.Data]

#endregion

#region Classes and Functions: Stingray Meshes

class StingrayMatrix4x4: # Matrix4x4: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_89
    def __init__(self):
        self.v = [float(0)]*16
    def Serialize(self, f: MemoryStream):
        self.v = [f.float32(value) for value in self.v]
        return self

class StingrayMatrix3x3: # Matrix3x3: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_84
    def __init__(self):
        self.x = [0,0,0]
        self.y = [0,0,0]
        self.z = [0,0,0]
    def Serialize(self, f: MemoryStream):
        self.x = f.vec3_float(self.x)
        self.y = f.vec3_float(self.x)
        self.z = f.vec3_float(self.x)
        return self

class StingrayLocalTransform: # Stingray Local Transform: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_100
    def __init__(self):
        self.rot   = StingrayMatrix3x3()
        self.pos   = [0,0,0]
        self.scale = [1,1,1]
        self.dummy = 0 # Force 16 byte alignment
        self.Incriment = self.ParentBone = 0

    def Serialize(self, f: MemoryStream):
        self.rot    = self.rot.Serialize(f)
        self.pos    = f.vec3_float(self.pos)
        self.scale  = f.vec3_float(self.scale)
        self.dummy  = f.float32(self.dummy)
        return self
    def SerializeV2(self, f: MemoryStream): # Quick and dirty solution, unknown exactly what this is for
        f.seek(f.tell()+48)
        self.pos    = f.vec3_float(self.pos)
        self.dummy  = f.float32(self.dummy)
        return self
    def SerializeTransformEntry(self, f: MemoryStream):
        self.Incriment = f.uint16(self.Incriment)
        self.ParentBone = f.uint16(self.ParentBone)
        return self

class TransformInfo: # READ ONLY
    def __init__(self):
        self.NumTransforms = 0
        self.Transforms = []
        self.PositionTransforms = []
        self.TransfromEntries = []
        self.NameHashes = []
    def Serialize(self, f: MemoryStream):
        if f.IsWriting():
            raise Exception("This struct is read only (write not implemented)")
        self.NumTransforms = f.uint32(self.NumTransforms)
        f.seek(f.tell()+12)
        self.Transforms = [StingrayLocalTransform().Serialize(f) for n in range(self.NumTransforms)]
        self.PositionTransforms = [StingrayLocalTransform().SerializeV2(f) for n in range(self.NumTransforms)]
        self.TransfromEntries = [StingrayLocalTransform().SerializeTransformEntry(f) for n in range(self.NumTransforms)]
        self.NameHashes = [f.uint32(n) for n in range(self.NumTransforms)]
        PrettyPrint(f"hashes: {self.NameHashes}")
        for n in range(self.NumTransforms):
            self.Transforms[n].pos = self.PositionTransforms[n].pos

class CustomizationInfo: # READ ONLY
    def __init__(self):
        self.BodyType  = ""
        self.Slot      = ""
        self.Weight    = ""
        self.PieceType = ""
    def Serialize(self, f: MemoryStream):
        if f.IsWriting():
            raise Exception("This struct is read only (write not implemented)")
        try: # TODO: fix this, this is basically completely wrong, this is generic user data, but for now this works
            f.seek(f.tell()+24)
            length = f.uint32(0)
            self.BodyType = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.Slot = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.Weight = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
            f.seek(f.tell()+12)
            length = f.uint32(0)
            self.PieceType = bytes(f.bytes(b"", length)).replace(b"\x00", b"").decode()
        except:
            self.BodyType  = ""
            self.Slot      = ""
            self.Weight    = ""
            self.PieceType = ""
            pass # tehee


class StreamComponentType:
    POSITION = 0
    NORMAL = 1
    TANGENT = 2 # not confirmed
    BITANGENT = 3 # not confirmed
    UV = 4
    COLOR = 5
    BONE_INDEX = 6
    BONE_WEIGHT = 7
    UNKNOWN_TYPE = -1
    
class StreamComponentFormat:
    FLOAT = 0
    VEC2_FLOAT = 1
    VEC3_FLOAT = 2
    RGBA_R8G8B8A8 = 4
    VEC4_UINT32 = 20 # unconfirmed
    VEC4_UINT8 = 24
    VEC4_1010102 = 25
    UNK_NORMAL = 26
    VEC2_HALF = 29
    VEC4_HALF = 31
    UNKNOWN_TYPE = -1

class StreamComponentInfo:
    
    def __init__(self, type="position", format="float"):
        self.Type   = self.TypeFromName(type)
        self.Format = self.FormatFromName(format)
        self.Index   = 0
        self.Unknown = 0
    def Serialize(self, f: MemoryStream):
        self.Type      = f.uint32(self.Type)
        self.Format    = f.uint32(self.Format)
        self.Index     = f.uint32(self.Index)
        self.Unknown   = f.uint64(self.Unknown)
        return self
    def TypeName(self):
        if   self.Type == 0: return "position"
        elif self.Type == 1: return "normal"
        elif self.Type == 2: return "tangent" # not confirmed
        elif self.Type == 3: return "bitangent" # not confirmed
        elif self.Type == 4: return "uv"
        elif self.Type == 5: return "color"
        elif self.Type == 6: return "bone_index"
        elif self.Type == 7: return "bone_weight"
        return "unknown"
    def TypeFromName(self, name):
        if   name == "position": return 0
        elif name == "normal":   return 1
        elif name == "tangent":  return 2
        elif name == "bitangent":return 3
        elif name == "uv":       return 4
        elif name == "color":    return 5
        elif name == "bone_index":  return 6
        elif name == "bone_weight": return 7
        return -1
    def FormatName(self):
        # check archive 9102938b4b2aef9d
        if   self.Format == 0:  return "float"
        elif self.Format == 1:  return "vec2_float"
        elif self.Format == 2:  return "vec3_float"
        elif self.Format == 4:  return "rgba_r8g8b8a8"
        elif self.Format == 20: return "vec4_uint32" # vec4_uint32 ??
        elif self.Format == 24: return "vec4_uint8"
        elif self.Format == 25: return "vec4_1010102"
        elif self.Format == 26: return "unk_normal"
        elif self.Format == 29: return "vec2_half"
        elif self.Format == 31: return "vec4_half" # found in archive 738130362c354ceb->8166218779455159235.mesh
        return "unknown"
    def FormatFromName(self, name):
        if   name == "float":         return 0
        elif name == "vec3_float":    return 2
        elif name == "rgba_r8g8b8a8": return 4
        elif name == "vec4_uint32": return 20 # unconfirmed
        elif name == "vec4_uint8":  return 24
        elif name == "vec4_1010102":  return 25
        elif name == "unk_normal":  return 26
        elif name == "vec2_half":   return 29
        elif name == "vec4_half":   return 31
        return -1
    def GetSize(self):
        if   self.Format == 0:  return 4
        elif self.Format == 2:  return 12
        elif self.Format == 4:  return 4
        elif self.Format == 20: return 16
        elif self.Format == 24: return 4
        elif self.Format == 25: return 4
        elif self.Format == 26: return 4
        elif self.Format == 29: return 4
        elif self.Format == 31: return 8
        raise Exception("Cannot get size of unknown vertex format: "+str(self.Format))
    def SerializeComponent(self, f: MemoryStream, value):
        try:
            serialize_func = FUNCTION_LUTS.SERIALIZE_COMPONENT_LUT[self.Format]
            return serialize_func(f, value)
        except:
            raise Exception("Cannot serialize unknown vertex format: "+str(self.Format))
                

class BoneInfo:
    def __init__(self):
        self.NumBones = self.unk1 = self.RealIndicesOffset = self.FakeIndicesOffset = self.NumFakeIndices = self.FakeIndicesUnk = 0
        self.Bones = self.RealIndices = self.FakeIndices = []
        self.DEV_RawData = bytearray()
    def Serialize(self, f: MemoryStream, end=None):
        if f.IsReading():
            self.DEV_RawData = bytearray(end-f.tell())
            start = f.tell()
            self.Serialize_REAL(f)
            f.seek(start)
        self.DEV_RawData = f.bytes(self.DEV_RawData)
        return self

    def Serialize_REAL(self, f: MemoryStream): # still need to figure out whats up with the unknown bit
        RelPosition = f.tell()

        self.NumBones       = f.uint32(self.NumBones)
        self.unk1           = f.uint32(self.unk1)
        self.RealIndicesOffset = f.uint32(self.RealIndicesOffset)
        self.FakeIndicesOffset = f.uint32(self.FakeIndicesOffset)
        # get bone data
        if f.IsReading():
            self.Bones = [StingrayMatrix4x4() for n in range(self.NumBones)]
            self.RealIndices = [0 for n in range(self.NumBones)]
            self.FakeIndices = [0 for n in range(self.NumBones)]
        self.Bones = [bone.Serialize(f) for bone in self.Bones]
        # get real indices
        if f.IsReading(): f.seek(RelPosition+self.RealIndicesOffset)
        else            : self.RealIndicesOffset = f.tell()-RelPosition
        self.RealIndices = [f.uint32(index) for index in self.RealIndices]
        PrettyPrint("indicies")
        PrettyPrint(self.RealIndices)
        # get unknown
        return self

        # get fake indices
        if f.IsReading(): f.seek(RelPosition+self.FakeIndicesOffset)
        else            : self.FakeIndicesOffset = f.tell()-RelPosition
        self.NumFakeIndices = f.uint32(self.NumFakeIndices)
        self.FakeIndicesUnk = f.uint64(self.FakeIndices[0])
        self.FakeIndices = [f.uint32(index) for index in self.FakeIndices]
        return self
    def GetRealIndex(self, bone_index):
        FakeIndex = self.FakeIndices.index(bone_index)
        return self.RealIndices[FakeIndex]

class StreamInfo:
    def __init__(self):
        self.Components = []
        self.ComponentInfoID = self.NumComponents = self.VertexBufferID = self.VertexBuffer_unk1 = self.NumVertices = self.VertexStride = self.VertexBuffer_unk2 = self.VertexBuffer_unk3 = 0
        self.IndexBufferID = self.IndexBuffer_unk1 = self.NumIndices = self.IndexBuffer_unk2 = self.IndexBuffer_unk3 = self.IndexBuffer_Type = self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.VertexBufferOffset = self.VertexBufferSize = self.IndexBufferOffset = self.IndexBufferSize = 0
        self.UnkEndingBytes = bytearray(16)
        self.DEV_StreamInfoOffset    = self.DEV_ComponentInfoOffset = 0 # helper vars, not in file

    def Serialize(self, f: MemoryStream):
        self.DEV_StreamInfoOffset = f.tell()
        self.ComponentInfoID = f.uint64(self.ComponentInfoID)
        self.DEV_ComponentInfoOffset = f.tell()
        f.seek(self.DEV_ComponentInfoOffset + 320)
        # vertex buffer info
        self.NumComponents      = f.uint64(len(self.Components))
        self.VertexBufferID     = f.uint64(self.VertexBufferID)
        self.VertexBuffer_unk1  = f.uint64(self.VertexBuffer_unk1)
        self.NumVertices        = f.uint32(self.NumVertices)
        self.VertexStride       = f.uint32(self.VertexStride)
        self.VertexBuffer_unk2  = f.uint64(self.VertexBuffer_unk2)
        self.VertexBuffer_unk3  = f.uint64(self.VertexBuffer_unk3)
        # index buffer info
        self.IndexBufferID      = f.uint64(self.IndexBufferID)
        self.IndexBuffer_unk1   = f.uint64(self.IndexBuffer_unk1)
        self.NumIndices         = f.uint32(self.NumIndices)
        self.IndexBuffer_Type   = f.uint32(self.IndexBuffer_Type)
        self.IndexBuffer_unk2   = f.uint64(self.IndexBuffer_unk2)
        self.IndexBuffer_unk3   = f.uint64(self.IndexBuffer_unk3)
        # offset info
        self.VertexBufferOffset = f.uint32(self.VertexBufferOffset)
        self.VertexBufferSize   = f.uint32(self.VertexBufferSize)
        self.IndexBufferOffset  = f.uint32(self.IndexBufferOffset)
        self.IndexBufferSize    = f.uint32(self.IndexBufferSize)
        # allign to 16
        self.UnkEndingBytes     = f.bytes(self.UnkEndingBytes, 16) # exact length is unknown
        EndOffset = ceil(float(f.tell())/16) * 16
        # component info
        f.seek(self.DEV_ComponentInfoOffset)
        if f.IsReading():
            self.Components = [StreamComponentInfo() for n in range(self.NumComponents)]
        self.Components = [Comp.Serialize(f) for Comp in self.Components]

        # return
        f.seek(EndOffset)
        return self

class MeshSectionInfo:
    def __init__(self, ID=0):
        self.unk1 = self.VertexOffset=self.NumVertices=self.IndexOffset=self.NumIndices=self.unk2 = 0
        self.DEV_MeshInfoOffset=0 # helper var, not in file
        self.ID = ID
    def Serialize(self, f: MemoryStream):
        self.DEV_MeshInfoOffset = f.tell()
        self.unk1           = f.uint32(self.unk1)
        self.VertexOffset   = f.uint32(self.VertexOffset)
        self.NumVertices    = f.uint32(self.NumVertices)
        self.IndexOffset    = f.uint32(self.IndexOffset)
        self.NumIndices     = f.uint32(self.NumIndices)
        self.unk2           = f.uint32(self.unk1)
        return self

class MeshInfo:
    def __init__(self):
        self.unk1 = self.unk3 = self.unk4 = self.TransformIndex = self.LodIndex = self.StreamIndex = self.NumSections = self.unk7 = self.unk8 = self.unk9 = self.NumSections_unk = self.MeshID = 0
        self.unk2 = bytearray(32); self.unk6 = bytearray(40)
        self.SectionIDs = self.Sections = []
    def Serialize(self, f: MemoryStream):
        self.unk1 = f.uint64(self.unk1)
        self.unk2 = f.bytes(self.unk2, 32)
        self.MeshID= f.uint32(self.MeshID)
        self.unk3 = f.uint32(self.unk3)
        self.TransformIndex = f.uint32(self.TransformIndex)
        self.unk4 = f.uint32(self.unk4)
        self.LodIndex       = f.int32(self.LodIndex)
        self.StreamIndex    = f.uint32(self.StreamIndex)
        self.unk6           = f.bytes(self.unk6, 40)
        self.NumSections_unk= f.uint32(len(self.Sections))
        self.unk7           = f.uint32(0x80)
        self.unk8           = f.uint64(self.unk8)
        self.NumSections    = f.uint32(len(self.Sections))
        self.unk9           = f.uint32(0x80+(len(self.Sections)*4))
        if f.IsReading(): self.SectionIDs  = [0 for n in range(self.NumSections)]
        else:             self.SectionIDs  = [section.ID for section in self.Sections]
        self.SectionIDs  = [f.uint32(ID) for ID in self.SectionIDs]
        if f.IsReading(): self.Sections    = [MeshSectionInfo(self.SectionIDs[n]) for n in range(self.NumSections)]
        self.Sections   = [Section.Serialize(f) for Section in self.Sections]
        return self
    def GetNumIndices(self):
        total = 0
        for section in self.Sections:
            total += section.NumIndices
        return total
    def GetNumVertices(self):
        return self.Sections[0].NumVertices

class RawMaterialClass:
    DefaultMaterialName    = "StingrayDefaultMaterial"
    DefaultMaterialShortID = 155175220
    def __init__(self):
        self.MatID      = self.DefaultMaterialName
        self.ShortID    = self.DefaultMaterialShortID
        self.StartIndex = 0
        self.NumIndices = 0
        self.DEV_BoneInfoOverride = None
    def IDFromName(self, name):
        if name.find(self.DefaultMaterialName) != -1:
            self.MatID   = self.DefaultMaterialName
            self.ShortID = self.DefaultMaterialShortID
        else:
            try:
                self.MatID   = int(name)
                self.ShortID = r.randint(1, 0xffffffff)
            except:
                raise Exception("Material name must be a number")

class RawMeshClass:
    def __init__(self):
        self.MeshInfoIndex = 0
        self.VertexPositions  = []
        self.VertexNormals    = []
        self.VertexTangents   = []
        self.VertexBiTangents = []
        self.VertexUVs        = []
        self.VertexColors     = []
        self.VertexBoneIndices= []
        self.VertexWeights    = []
        self.Indices          = []
        self.Materials        = []
        self.LodIndex         = -1
        self.MeshID           = 0
        self.DEV_Use32BitIndices = False
        self.DEV_BoneInfo      = None
        self.DEV_BoneInfoIndex = 0
        self.DEV_Transform     = None
    def IsCullingBody(self):
        IsPhysics = True
        for material in self.Materials:
            if material.MatID != material.DefaultMaterialName:
                IsPhysics = False
        return IsPhysics
    def IsLod(self):
        IsLod = True
        if self.LodIndex == 0 or self.LodIndex == -1:
            IsLod = False
        if self.IsCullingBody():
            IsLod = False
        return IsLod
    def IsStaticMesh(self):
        for vertex in self.VertexWeights:
            if vertex != [0, 0, 0, 0]:
                return False
        return True

    def InitBlank(self, numVertices, numIndices, numUVs, numBoneIndices):
        self.VertexPositions    = [[0,0,0] for n in range(numVertices)]
        self.VertexNormals      = [[0,0,0] for n in range(numVertices)]
        self.VertexTangents     = [[0,0,0] for n in range(numVertices)]
        self.VertexBiTangents   = [[0,0,0] for n in range(numVertices)]
        self.VertexColors       = [[0,0,0,0] for n in range(numVertices)]
        self.VertexWeights      = [[0,0,0,0] for n in range(numVertices)]
        self.Indices            = [[0,0,0] for n in range(int(numIndices/3))]
        for idx in range(numUVs):
            self.VertexUVs.append([[0,0] for n in range(numVertices)])
        for idx in range(numBoneIndices):
            self.VertexBoneIndices.append([[0,0,0,0] for n in range(numVertices)])
    
    def ReInitVerts(self, numVertices):
        self.VertexPositions    = [[0,0,0] for n in range(numVertices)]
        self.VertexNormals      = [[0,0,0] for n in range(numVertices)]
        self.VertexTangents     = [[0,0,0] for n in range(numVertices)]
        self.VertexBiTangents   = [[0,0,0] for n in range(numVertices)]
        self.VertexColors       = [[0,0,0,0] for n in range(numVertices)]
        self.VertexWeights      = [[0,0,0,0] for n in range(numVertices)]
        numVerts        = len(self.VertexUVs)
        numBoneIndices  = len(self.VertexBoneIndices)
        self.VertexUVs = []
        self.VertexBoneIndices = []
        for idx in range(numVerts):
            self.VertexUVs.append([[0,0] for n in range(numVertices)])
        for idx in range(numBoneIndices):
            self.VertexBoneIndices.append([[0,0,0,0] for n in range(numVertices)])
            
class SerializeFunctions:
    
    def SerializePositionComponent(gpu, mesh, component, vidx):
        mesh.VertexPositions[vidx] = component.SerializeComponent(gpu, mesh.VertexPositions[vidx])
    
    def SerializeNormalComponent(gpu, mesh, component, vidx):
        norm = component.SerializeComponent(gpu, mesh.VertexNormals[vidx])
        if gpu.IsReading():
            if not isinstance(norm, int):
                norm = list(mathutils.Vector((norm[0],norm[1],norm[2])).normalized())
                mesh.VertexNormals[vidx] = norm[:3]
            else:
                mesh.VertexNormals[vidx] = norm
    
    def SerializeTangentComponent(gpu, mesh, component, vidx):
        mesh.VertexTangents[vidx] = component.SerializeComponent(gpu, mesh.VertexTangents[vidx])
    
    def SerializeBiTangentComponent(gpu, mesh, component, vidx):
        mesh.VertexBiTangents[vidx] = component.SerializeComponent(gpu, mesh.VertexBiTangents[vidx])
    
    def SerializeUVComponent(gpu, mesh, component, vidx):
        mesh.VertexUVs[component.Index][vidx] = component.SerializeComponent(gpu, mesh.VertexUVs[component.Index][vidx])
    
    def SerializeColorComponent(gpu, mesh, component, vidx):
        mesh.VertexColors[vidx] = component.SerializeComponent(gpu, mesh.VertexColors[vidx])
    
    def SerializeBoneIndexComponent(gpu, mesh, component, vidx):
        try:
             mesh.VertexBoneIndices[component.Index][vidx] = component.SerializeComponent(gpu, mesh.VertexBoneIndices[component.Index][vidx])
        except:
            raise Exception(f"Vertex bone index out of range. Component index: {component.Index} vidx: {vidx}")
    
    def SerializeBoneWeightComponent(gpu, mesh, component, vidx):
        if component.Index > 0: # TODO: add support for this (check archive 9102938b4b2aef9d)
            PrettyPrint("Multiple weight indices are unsupported!", "warn")
            gpu.seek(gpu.tell()+component.GetSize())
        else:
            mesh.VertexWeights[vidx] = component.SerializeComponent(gpu, mesh.VertexWeights[vidx])
            
            
    def SerializeFloatComponent(f: MemoryStream, value):
        return f.float32(value)
        
    def SerializeVec2FloatComponent(f: MemoryStream, value):
        return f.vec2_float(value)
        
    def SerializeVec3FloatComponent(f: MemoryStream, value):
        return f.vec3_float(value)
        
    def SerializeRGBA8888Component(f: MemoryStream, value):
        if f.IsReading():
            r = min(255, int(value[0]*255))
            g = min(255, int(value[1]*255))
            b = min(255, int(value[2]*255))
            a = min(255, int(value[3]*255))
            value = f.vec4_uint8([r,g,b,a])
        else:
            value = f.vec4_uint8([r,g,b,a])
            value[0] = min(1, float(value[0]/255))
            value[1] = min(1, float(value[1]/255))
            value[2] = min(1, float(value[2]/255))
            value[3] = min(1, float(value[3]/255))
        return value
        
    def SerializeVec4Uint32Component(f: MemoryStream, value):
        return f.vec4_uint32(value)
        
    def SerializeVec4Uint8Component(f: MemoryStream, value):
        return f.vec4_uint8(value)
        
    def SerializeVec41010102Component(f: MemoryStream, value):
        if f.IsReading():
            value = TenBitUnsigned(f.uint32(0))
            value[3] = 0 # seems to be needed for weights
        else:
            f.uint32(MakeTenBitUnsigned(value))
        return value
        
    def SerializeUnkNormalComponent(f: MemoryStream, value):
        if isinstance(value, int):
            return f.uint32(value)
        else:
            return f.uint32(0)
            
    def SerializeVec2HalfComponent(f: MemoryStream, value):
        return f.vec2_half(value)
        
    def SerializeVec4HalfComponent(f: MemoryStream, value):
        if isinstance(value, float):
            return f.vec4_half([value,value,value,value])
        else:
            return f.vec4_half(value)
            
    def SerializeUnknownComponent(f: MemoryStream, value):
        raise Exception("Cannot serialize unknown vertex format!")
              
            
class FUNCTION_LUTS:
    
    SERIALIZE_MESH_LUT = {
        StreamComponentType.POSITION: SerializeFunctions.SerializePositionComponent,
        StreamComponentType.NORMAL: SerializeFunctions.SerializeNormalComponent,
        StreamComponentType.TANGENT: SerializeFunctions.SerializeTangentComponent,
        StreamComponentType.BITANGENT: SerializeFunctions.SerializeBiTangentComponent,
        StreamComponentType.UV: SerializeFunctions.SerializeUVComponent,
        StreamComponentType.COLOR: SerializeFunctions.SerializeColorComponent,
        StreamComponentType.BONE_INDEX: SerializeFunctions.SerializeBoneIndexComponent,
        StreamComponentType.BONE_WEIGHT: SerializeFunctions.SerializeBoneWeightComponent
    }
    
    SERIALIZE_COMPONENT_LUT = {
        StreamComponentFormat.FLOAT: SerializeFunctions.SerializeFloatComponent,
        StreamComponentFormat.VEC2_FLOAT: SerializeFunctions.SerializeVec2FloatComponent,
        StreamComponentFormat.VEC3_FLOAT: SerializeFunctions.SerializeVec3FloatComponent,
        StreamComponentFormat.RGBA_R8G8B8A8: SerializeFunctions.SerializeRGBA8888Component,
        StreamComponentFormat.VEC4_UINT32: SerializeFunctions.SerializeVec4Uint32Component,
        StreamComponentFormat.VEC4_UINT8: SerializeFunctions.SerializeVec4Uint8Component,
        StreamComponentFormat.VEC4_1010102: SerializeFunctions.SerializeVec41010102Component,
        StreamComponentFormat.UNK_NORMAL: SerializeFunctions.SerializeUnkNormalComponent,
        StreamComponentFormat.VEC2_HALF: SerializeFunctions.SerializeVec2HalfComponent,
        StreamComponentFormat.VEC4_HALF: SerializeFunctions.SerializeVec4HalfComponent
    }

class StingrayMeshFile:
    def __init__(self):
        self.HeaderData1        = bytearray(28);  self.HeaderData2        = bytearray(20); self.UnReversedData1  = bytearray(); self.UnReversedData2    = bytearray()
        self.StreamInfoOffset   = self.EndingOffset = self.MeshInfoOffset = self.NumStreams = self.NumMeshes = self.EndingBytes = self.StreamInfoUnk2 = self.HeaderUnk = self.MaterialsOffset = self.NumMaterials = self.NumBoneInfo = self.BoneInfoOffset = 0
        self.StreamInfoOffsets  = self.StreamInfoUnk = self.StreamInfoArray = self.MeshInfoOffsets = self.MeshInfoUnk = self.MeshInfoArray = []
        self.CustomizationInfoOffset = self.UnkHeaderOffset1 = self.UnkHeaderOffset2 = self.TransformInfoOffset = self.UnkRef1 = self.BonesRef = self.CompositeRef = 0
        self.BoneInfoOffsets = self.BoneInfoArray = []
        self.RawMeshes = []
        self.SectionsIDs = []
        self.MaterialIDs = []
        self.DEV_MeshInfoMap = [] # Allows removing of meshes while mapping them to the original meshes
        self.CustomizationInfo = CustomizationInfo()
        self.TransformInfo     = TransformInfo()
        self.BoneNames = None
    # -- Serialize Mesh -- #
    def Serialize(self, f: MemoryStream, gpu, redo_offsets = False, BlenderOpts=None):
        PrettyPrint("Serialize")
        if f.IsWriting() and not redo_offsets:
            # duplicate bone info sections if needed
            temp_boneinfos = [None for n in range(len(self.BoneInfoArray))]
            for Raw_Mesh in self.RawMeshes:
                idx         = Raw_Mesh.MeshInfoIndex
                Mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[idx]]
                if Mesh_info.LodIndex == -1:
                    continue
                RealBoneInfoIdx = Mesh_info.LodIndex
                BoneInfoIdx     = Raw_Mesh.DEV_BoneInfoIndex
                temp_boneinfos[RealBoneInfoIdx] = self.BoneInfoArray[BoneInfoIdx]
            self.BoneInfoArray = temp_boneinfos
            PrettyPrint("Building materials")
            self.SectionsIDs = []
            self.MaterialIDs = []
            Order = 0xffffffff
            for Raw_Mesh in self.RawMeshes:
                if len(Raw_Mesh.Materials) == 0:
                    raise Exception("Mesh has no materials, but at least one is required")
                idx         = Raw_Mesh.MeshInfoIndex
                Mesh_info   = self.MeshInfoArray[self.DEV_MeshInfoMap[idx]]
                Mesh_info.Sections = []
                for Material in Raw_Mesh.Materials:
                    Section = MeshSectionInfo()
                    Section.ID          = int(Material.ShortID)
                    Section.NumIndices  = Material.NumIndices
                    Section.VertexOffset  = Order # | Used for ordering function
                    Section.IndexOffset   = Order # /

                    # This doesnt do what it was intended to do
                    if Material.DEV_BoneInfoOverride != None:
                        PrettyPrint("Overriding unknown material values")
                        Section.unk1 = Material.DEV_BoneInfoOverride
                        Section.unk2 = Material.DEV_BoneInfoOverride
                    else:
                        Section.unk1 = len(Mesh_info.Sections) # | dont know what these actually are, but this is usually correct it seems
                        Section.unk2 = len(Mesh_info.Sections) # /

                    Mesh_info.Sections.append(Section)
                    Order -= 1
                    try: # if material ID uses the defualt material string it will throw an error, but thats fine as we dont want to include those ones anyway
                        #if int(Material.MatID) not in self.MaterialIDs:
                        self.MaterialIDs.append(int(Material.MatID))
                        self.SectionsIDs.append(int(Material.ShortID))
                    except:
                        pass

        # serialize file
        self.UnkRef1            = f.uint64(self.UnkRef1)
        self.BonesRef           = f.uint64(self.BonesRef)
        self.CompositeRef       = f.uint64(self.CompositeRef)
        self.HeaderData1        = f.bytes(self.HeaderData1, 28)
        self.TransformInfoOffset= f.uint32(self.TransformInfoOffset)
        self.HeaderData2        = f.bytes(self.HeaderData2, 20)
        self.CustomizationInfoOffset  = f.uint32(self.CustomizationInfoOffset)
        self.UnkHeaderOffset1   = f.uint32(self.UnkHeaderOffset1)
        self.UnkHeaderOffset2   = f.uint32(self.UnkHeaderOffset1)
        self.BoneInfoOffset     = f.uint32(self.BoneInfoOffset)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        self.EndingOffset       = f.uint32(self.EndingOffset)
        self.MeshInfoOffset     = f.uint32(self.MeshInfoOffset)
        self.HeaderUnk          = f.uint64(self.HeaderUnk)
        self.MaterialsOffset    = f.uint32(self.MaterialsOffset)

        if f.IsReading() and self.MeshInfoOffset == 0:
            raise Exception("Unsuported Mesh Format (No geometry)")

        if f.IsReading() and (self.StreamInfoOffset == 0 and self.CompositeRef == 0):
            raise Exception("Unsuported Mesh Format (No buffer stream)")

        # Get composite file
        if f.IsReading() and self.CompositeRef != 0:
            Entry = Global_TocManager.GetEntry(self.CompositeRef, CompositeMeshID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.StreamInfoArray = Entry.LoadedData.StreamInfoArray
                gpu = Entry.LoadedData.GpuData
            else:
                raise Exception(f"Composite mesh file {self.CompositeRef} could not be found")

        # Get bones file
        if f.IsReading() and self.BonesRef != 0:
            Entry = Global_TocManager.GetEntry(self.BonesRef, Hash64("bones"))
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.BoneNames = Entry.LoadedData.Names
                self.BoneHashes = Entry.LoadedData.BoneHashes

        # Get Customization data: READ ONLY
        if f.IsReading() and self.CustomizationInfoOffset > 0:
            loc = f.tell(); f.seek(self.CustomizationInfoOffset)
            self.CustomizationInfo.Serialize(f)
            f.seek(loc)
        # Get Transform data: READ ONLY
        if f.IsReading() and self.TransformInfoOffset > 0:
            loc = f.tell(); f.seek(self.TransformInfoOffset)
            self.TransformInfo.Serialize(f)
            f.seek(loc)

        # Unreversed data
        if f.IsReading():
            if self.BoneInfoOffset > 0:
                UnreversedData1Size = self.BoneInfoOffset-f.tell()
            elif self.StreamInfoOffset > 0:
                UnreversedData1Size = self.StreamInfoOffset-f.tell()
        else: UnreversedData1Size = len(self.UnReversedData1)
        try:
            self.UnReversedData1    = f.bytes(self.UnReversedData1, UnreversedData1Size)
        except:
            PrettyPrint(f"Could not set UnReversedData1", "ERROR")

        # Bone Info
        if f.IsReading(): f.seek(self.BoneInfoOffset)
        else            : self.BoneInfoOffset = f.tell()
        self.NumBoneInfo = f.uint32(len(self.BoneInfoArray))
        if f.IsWriting() and not redo_offsets:
            self.BoneInfoOffsets = [0]*self.NumBoneInfo
        if f.IsReading():
            self.BoneInfoOffsets = [0]*self.NumBoneInfo
            self.BoneInfoArray   = [BoneInfo() for n in range(self.NumBoneInfo)]
        self.BoneInfoOffsets    = [f.uint32(Offset) for Offset in self.BoneInfoOffsets]
        for boneinfo_idx in range(self.NumBoneInfo):
            end_offset = None
            if f.IsReading():
                f.seek(self.BoneInfoOffset + self.BoneInfoOffsets[boneinfo_idx])
                if boneinfo_idx+1 != self.NumBoneInfo:
                    end_offset = self.BoneInfoOffset + self.BoneInfoOffsets[boneinfo_idx+1]
                else:
                    end_offset = self.StreamInfoOffset
                    if self.StreamInfoOffset == 0:
                        end_offset = self.MeshInfoOffset
            else:
                self.BoneInfoOffsets[boneinfo_idx] = f.tell() - self.BoneInfoOffset
            self.BoneInfoArray[boneinfo_idx] = self.BoneInfoArray[boneinfo_idx].Serialize(f, end_offset)
            # Bone Hash linking
            # if f.IsReading(): 
            #     PrettyPrint("Hashes")
            #     PrettyPrint(f"Length of bone names: {len(self.BoneNames)}")
            #     HashOffset = self.CustomizationInfoOffset - ((len(self.BoneNames) - 1) * 4) # this is a bad work around as we can't always get the bone names since some meshes don't have a bone file listed
            #     PrettyPrint(f"Hash Offset: {HashOffset}")
            #     f.seek(HashOffset)
            #     self.MeshBoneHashes = [0 for n in range(len(self.BoneNames))]
            #     self.MeshBoneHashes = [f.uint32(Hash) for Hash in self.MeshBoneHashes]
            #     PrettyPrint(self.MeshBoneHashes)
            #     for index in self.BoneInfoArray[boneinfo_idx].RealIndices:
            #         BoneInfoHash = self.MeshBoneHashes[index]
            #         for index in range(len(self.BoneHashes)):
            #             if self.BoneHashes[index] == BoneInfoHash:
            #                 BoneName = self.BoneNames[index]
            #                 PrettyPrint(f"Index: {index}")
            #                 PrettyPrint(f"Bone: {BoneName}")
            #                 continue


        # Stream Info
        if self.StreamInfoOffset != 0:
            if f.IsReading(): f.seek(self.StreamInfoOffset)
            else:
                f.seek(ceil(float(f.tell())/16)*16); self.StreamInfoOffset = f.tell()
            self.NumStreams = f.uint32(len(self.StreamInfoArray))
            if f.IsWriting():
                if not redo_offsets: self.StreamInfoOffsets = [0]*self.NumStreams
                self.StreamInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray[:self.NumStreams]]
            if f.IsReading():
                self.StreamInfoOffsets = [0]*self.NumStreams
                self.StreamInfoUnk     = [0]*self.NumStreams
                self.StreamInfoArray   = [StreamInfo() for n in range(self.NumStreams)]

            self.StreamInfoOffsets  = [f.uint32(Offset) for Offset in self.StreamInfoOffsets]
            self.StreamInfoUnk      = [f.uint32(Unk) for Unk in self.StreamInfoUnk]
            self.StreamInfoUnk2     = f.uint32(self.StreamInfoUnk2)
            for stream_idx in range(self.NumStreams):
                if f.IsReading(): f.seek(self.StreamInfoOffset + self.StreamInfoOffsets[stream_idx])
                else            : self.StreamInfoOffsets[stream_idx] = f.tell() - self.StreamInfoOffset
                self.StreamInfoArray[stream_idx] = self.StreamInfoArray[stream_idx].Serialize(f)

        # Mesh Info
        if f.IsReading(): f.seek(self.MeshInfoOffset)
        else            : self.MeshInfoOffset = f.tell()
        self.NumMeshes = f.uint32(len(self.MeshInfoArray))

        if f.IsWriting():
            if not redo_offsets: self.MeshInfoOffsets = [0]*self.NumMeshes
            self.MeshInfoUnk = [mesh_info.MeshID for mesh_info in self.MeshInfoArray]
        if f.IsReading():
            self.MeshInfoOffsets = [0]*self.NumMeshes
            self.MeshInfoUnk     = [0]*self.NumMeshes
            self.MeshInfoArray   = [MeshInfo() for n in range(self.NumMeshes)]
            self.DEV_MeshInfoMap = [n for n in range(len(self.MeshInfoArray))]

        self.MeshInfoOffsets  = [f.uint32(Offset) for Offset in self.MeshInfoOffsets]
        self.MeshInfoUnk      = [f.uint32(Unk) for Unk in self.MeshInfoUnk]
        for mesh_idx in range(self.NumMeshes):
            if f.IsReading(): f.seek(self.MeshInfoOffset+self.MeshInfoOffsets[mesh_idx])
            else            : self.MeshInfoOffsets[mesh_idx] = f.tell() - self.MeshInfoOffset
            self.MeshInfoArray[mesh_idx] = self.MeshInfoArray[mesh_idx].Serialize(f)

        # Materials
        if f.IsReading(): f.seek(self.MaterialsOffset)
        else            : self.MaterialsOffset = f.tell()
        self.NumMaterials = f.uint32(len(self.MaterialIDs))
        if f.IsReading():
            self.SectionsIDs = [0]*self.NumMaterials
            self.MaterialIDs = [0]*self.NumMaterials
        self.SectionsIDs = [f.uint32(ID) for ID in self.SectionsIDs]
        self.MaterialIDs = [f.uint64(ID) for ID in self.MaterialIDs]

        # Unreversed Data
        if f.IsReading(): UnreversedData2Size = self.EndingOffset-f.tell()
        else: UnreversedData2Size = len(self.UnReversedData2)
        self.UnReversedData2    = f.bytes(self.UnReversedData2, UnreversedData2Size)
        if f.IsWriting(): self.EndingOffset = f.tell()
        self.EndingBytes        = f.uint64(self.NumMeshes)
        if redo_offsets:
            return self

        # Serialize Data
        self.SerializeGpuData(gpu, BlenderOpts);

        # TODO: update offsets only instead of re-writing entire file
        if f.IsWriting() and not redo_offsets:
            f.seek(0)
            self.Serialize(f, gpu, True)
        return self

    def SerializeGpuData(self, gpu: MemoryStream, BlenderOpts=None):
        PrettyPrint("SerializeGpuData")
        # Init Raw Meshes If Reading
        if gpu.IsReading():
            self.InitRawMeshes()
        # re-order the meshes to match the vertex order (this is mainly for writing)
        OrderedMeshes = self.CreateOrderedMeshList()
        # Create Vertex Components If Writing
        if gpu.IsWriting():
            self.SetupRawMeshComponents(OrderedMeshes, BlenderOpts)

        # Serialize Gpu Data
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]
            if gpu.IsReading():
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
            else:
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)

    def SerializeIndexBuffer(self, gpu: MemoryStream, Stream_Info, stream_idx, OrderedMeshes):
        # get indices
        IndexOffset  = 0
        CompiledIncorrectly = False
        if gpu.IsWriting():Stream_Info.IndexBufferOffset = gpu.tell()
        for mesh in OrderedMeshes[stream_idx][1]:
            Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
            # Lod Info
            if gpu.IsReading():
                mesh.LodIndex = Mesh_Info.LodIndex
                mesh.DEV_BoneInfoIndex = Mesh_Info.LodIndex
            # handle index formats
            IndexStride = 2
            IndexInt = gpu.uint16
            if Stream_Info.IndexBuffer_Type == 1:
                IndexStride = 4
                IndexInt = gpu.uint32

            TotalIndex = 0
            for Section in Mesh_Info.Sections:
                # Create mat info
                if gpu.IsReading():
                    mat = RawMaterialClass()
                    if Section.ID in self.SectionsIDs:
                        mat_idx = self.SectionsIDs.index(Section.ID)
                        mat.IDFromName(str(self.MaterialIDs[mat_idx]))
                        mat.MatID = str(self.MaterialIDs[mat_idx])
                        #mat.ShortID = self.SectionsIDs[mat_idx]
                        if bpy.context.scene.Hd2ToolPanelSettings.ImportMaterials:
                            Global_TocManager.Load(mat.MatID, MaterialID, False, True)
                        else:
                            AddMaterialToBlend_EMPTY(mat.MatID)
                    else:
                        try   : bpy.data.materials[mat.MatID]
                        except: bpy.data.materials.new(mat.MatID)
                    mat.StartIndex = TotalIndex*3
                    mat.NumIndices = Section.NumIndices
                    mesh.Materials.append(mat)

                if gpu.IsReading(): gpu.seek(Stream_Info.IndexBufferOffset + (Section.IndexOffset*IndexStride))
                else:
                    Section.IndexOffset = IndexOffset
                    PrettyPrint(f"Updated Section Offset: {Section.IndexOffset}")
                for fidx in range(int(Section.NumIndices/3)):
                    indices = mesh.Indices[TotalIndex]
                    for i in range(3):
                        value = indices[i]
                        if not (0 <= value <= 0xffff) and IndexStride == 2:
                            PrettyPrint(f"Index: {value} TotalIndex: {TotalIndex}indecies out of bounds", "ERROR")
                            CompiledIncorrectly = True
                            value = min(max(0, value), 0xffff)
                        elif not (0 <= value <= 0xffffffff) and IndexStride == 4:
                            PrettyPrint(f"Index: {value} TotalIndex: {TotalIndex} indecies out of bounds", "ERROR")
                            CompiledIncorrectly = True
                            value = min(max(0, value), 0xffffffff)
                        indices[i] = IndexInt(value)
                    mesh.Indices[TotalIndex] = indices
                    TotalIndex += 1
                IndexOffset  += Section.NumIndices
        # update stream info
        if gpu.IsWriting():
            Stream_Info.IndexBufferSize    = gpu.tell() - Stream_Info.IndexBufferOffset
            Stream_Info.NumIndices         = IndexOffset

        # calculate correct vertex num (sometimes its wrong, no clue why, see 9102938b4b2aef9d->7040046837345593857)
        if gpu.IsReading():
            for mesh in OrderedMeshes[stream_idx][0]:
                RealNumVerts = 0
                for face in mesh.Indices:
                    for index in face:
                        if index > RealNumVerts:
                            RealNumVerts = index
                RealNumVerts += 1
                Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
                if Mesh_Info.Sections[0].NumVertices != RealNumVerts:
                    for Section in Mesh_Info.Sections:
                        Section.NumVertices = RealNumVerts
                    self.ReInitRawMeshVerts(mesh)

    def SerializeVertexBuffer(self, gpu: MemoryStream, Stream_Info, stream_idx, OrderedMeshes):
        # Vertex Buffer
        VertexOffset = 0
        if gpu.IsWriting(): Stream_Info.VertexBufferOffset = gpu.tell()
        for mesh in OrderedMeshes[stream_idx][0]:
            Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
            if gpu.IsWriting():
                for Section in Mesh_Info.Sections:
                    Section.VertexOffset = VertexOffset
                    Section.NumVertices  = len(mesh.VertexPositions)
                    PrettyPrint(f"Updated VertexOffset Offset: {Section.VertexOffset}")
            MainSection = Mesh_Info.Sections[0]
            # get vertices
            if gpu.IsReading(): gpu.seek(Stream_Info.VertexBufferOffset + (MainSection.VertexOffset*Stream_Info.VertexStride))
            
            for vidx in range(len(mesh.VertexPositions)):
                vstart = gpu.tell()

                for Component in Stream_Info.Components:
                    serialize_func = FUNCTION_LUTS.SERIALIZE_MESH_LUT[Component.Type]
                    serialize_func(gpu, mesh, Component, vidx)

                gpu.seek(vstart + Stream_Info.VertexStride)
            VertexOffset += len(mesh.VertexPositions)
        # update stream info
        if gpu.IsWriting():
            gpu.seek(ceil(float(gpu.tell())/16)*16)
            Stream_Info.VertexBufferSize    = gpu.tell() - Stream_Info.VertexBufferOffset
            Stream_Info.NumVertices         = VertexOffset
            
    def CreateOrderedMeshList(self):
        # re-order the meshes to match the vertex order (this is mainly for writing)
        meshes_ordered_by_vert = [
            sorted(
                [mesh for mesh in self.RawMeshes if self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].StreamIndex == index],
                key=lambda mesh: self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].Sections[0].VertexOffset
            ) for index in range(len(self.StreamInfoArray))
        ]
        meshes_ordered_by_index = [
            sorted(
                [mesh for mesh in self.RawMeshes if self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].StreamIndex == index],
                key=lambda mesh: self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]].Sections[0].IndexOffset
            ) for index in range(len(self.StreamInfoArray))
        ]
        OrderedMeshes = [list(a) for a in zip(meshes_ordered_by_vert, meshes_ordered_by_index)]

        # set 32 bit face indices if needed
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]
            for mesh in OrderedMeshes[stream_idx][0]:
                if mesh.DEV_Use32BitIndices:
                    Stream_Info.IndexBuffer_Type = 1
        return OrderedMeshes

    def InitRawMeshes(self):
        for n in range(len(self.MeshInfoArray)):
            NewMesh     = RawMeshClass()
            Mesh_Info   = self.MeshInfoArray[n]

            indexerror = Mesh_Info.StreamIndex >= len(self.StreamInfoArray)
            messageerror = "ERROR" if indexerror else "INFO"
            message = "Stream index out of bounds" if indexerror else ""
            PrettyPrint(f"Num: {len(self.StreamInfoArray)} Index: {Mesh_Info.StreamIndex}    {message}", messageerror)
            if indexerror: continue

            Stream_Info = self.StreamInfoArray[Mesh_Info.StreamIndex]
            NewMesh.MeshInfoIndex = n
            NewMesh.MeshID = Mesh_Info.MeshID
            NewMesh.DEV_Transform = self.TransformInfo.Transforms[Mesh_Info.TransformIndex]
            try:
                NewMesh.DEV_BoneInfo  = self.BoneInfoArray[Mesh_Info.LodIndex]
            except: pass
            numUVs          = 0
            numBoneIndices  = 0
            for component in Stream_Info.Components:
                if component.TypeName() == "uv":
                    numUVs += 1
                if component.TypeName() == "bone_index":
                    numBoneIndices += 1
            NewMesh.InitBlank(Mesh_Info.GetNumVertices(), Mesh_Info.GetNumIndices(), numUVs, numBoneIndices)
            self.RawMeshes.append(NewMesh)
    
    def ReInitRawMeshVerts(self, mesh):
        # for mesh in self.RawMeshes:
        Mesh_Info = self.MeshInfoArray[self.DEV_MeshInfoMap[mesh.MeshInfoIndex]]
        mesh.ReInitVerts(Mesh_Info.GetNumVertices())

    def SetupRawMeshComponents(self, OrderedMeshes, BlenderOpts=None):
        for stream_idx in range(len(OrderedMeshes)):
            Stream_Info = self.StreamInfoArray[stream_idx]

            HasPositions = False
            HasNormals   = False
            HasTangents  = False
            HasBiTangents= False
            IsSkinned    = False
            NumUVs       = 0
            NumBoneIndices = 0
            # get total number of components
            for mesh in OrderedMeshes[stream_idx][0]:
                if len(mesh.VertexPositions)  > 0: HasPositions  = True
                if len(mesh.VertexNormals)    > 0: HasNormals    = True
                if len(mesh.VertexTangents)   > 0: HasTangents   = True
                if len(mesh.VertexBiTangents) > 0: HasBiTangents = True
                if len(mesh.VertexBoneIndices)> 0: IsSkinned     = True
                if len(mesh.VertexUVs)   > NumUVs: NumUVs = len(mesh.VertexUVs)
                if len(mesh.VertexBoneIndices) > NumBoneIndices: NumBoneIndices = len(mesh.VertexBoneIndices)
            if BlenderOpts:    
                if BlenderOpts.get("Force2UVs"):
                    NumUVs = 2
                if IsSkinned and NumBoneIndices > 1 and BlenderOpts.get("Force1Group"):
                    NumBoneIndices = 1

            for mesh in OrderedMeshes[stream_idx][0]: # fill default values for meshes which are missing some components
                if not len(mesh.VertexPositions)  > 0:
                    raise Exception("bruh... your mesh doesn't have any vertices")
                if HasNormals and not len(mesh.VertexNormals)    > 0:
                    mesh.VertexNormals = [[0,0,0] for n in mesh.VertexPositions]
                if HasTangents and not len(mesh.VertexTangents)   > 0:
                    mesh.VertexTangents = [[0,0,0] for n in mesh.VertexPositions]
                if HasBiTangents and not len(mesh.VertexBiTangents) > 0:
                    mesh.VertexBiTangents = [[0,0,0] for n in mesh.VertexPositions]
                if IsSkinned and not len(mesh.VertexWeights) > 0:
                    mesh.VertexWeights      = [[0,0,0,0] for n in mesh.VertexPositions]
                    mesh.VertexBoneIndices  = [[[0,0,0,0] for n in mesh.VertexPositions]*NumBoneIndices]
                if IsSkinned and len(mesh.VertexBoneIndices) > NumBoneIndices:
                    mesh.VertexBoneIndices = mesh.VertexBoneIndices[::NumBoneIndices]
                if NumUVs > len(mesh.VertexUVs):
                    dif = NumUVs - len(mesh.VertexUVs)
                    for n in range(dif):
                        mesh.VertexUVs.append([[0,0] for n in mesh.VertexPositions])
            # make stream components
            Stream_Info.Components = []
            if HasPositions:  Stream_Info.Components.append(StreamComponentInfo("position", "vec3_float"))
            if HasNormals:    Stream_Info.Components.append(StreamComponentInfo("normal", "unk_normal"))
            for n in range(NumUVs):
                UVComponent = StreamComponentInfo("uv", "vec2_half")
                UVComponent.Index = n
                Stream_Info.Components.append(UVComponent)
            if IsSkinned:     Stream_Info.Components.append(StreamComponentInfo("bone_weight", "vec4_half"))
            for n in range(NumBoneIndices):
                BIComponent = StreamComponentInfo("bone_index", "vec4_uint8")
                BIComponent.Index = n
                Stream_Info.Components.append(BIComponent)
            # calculate Stride
            Stream_Info.VertexStride = 0
            for Component in Stream_Info.Components:
                Stream_Info.VertexStride += Component.GetSize()

def LoadStingrayMesh(ID, TocData, GpuData, StreamData, Reload, MakeBlendObject):
    toc  = MemoryStream(TocData)
    gpu  = MemoryStream(GpuData)
    StingrayMesh = StingrayMeshFile().Serialize(toc, gpu)
    if MakeBlendObject: CreateModel(StingrayMesh.RawMeshes, str(ID), StingrayMesh.CustomizationInfo, StingrayMesh.BoneNames, StingrayMesh.TransformInfo, StingrayMesh.BoneInfoArray)
    return StingrayMesh

def SaveStingrayMesh(self, ID, TocData, GpuData, StreamData, StingrayMesh, BlenderOpts=None):
    if BlenderOpts and BlenderOpts.get("AutoLods"):
        lod0 = None
        for mesh in StingrayMesh.RawMeshes:
            if mesh.LodIndex == 0:
                lod0 = mesh
                break
        # print(lod0)
        if lod0 != None:
            for n in range(len(StingrayMesh.RawMeshes)):
                if StingrayMesh.RawMeshes[n].IsLod():
                    newmesh = copy.copy(lod0)
                    newmesh.MeshInfoIndex = StingrayMesh.RawMeshes[n].MeshInfoIndex
                    StingrayMesh.RawMeshes[n] = newmesh
    toc  = MemoryStream(IOMode = "write")
    gpu  = MemoryStream(IOMode = "write")
    StingrayMesh.Serialize(toc, gpu)
    return [toc.Data, gpu.Data, b""]

#endregion

#region Operators: Archives & Patches

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

def DuplicateIDsInScene(self):
    CustomObjects = []
    for obj in bpy.context.selected_objects:
        if len(obj.keys()) > 1: 
            for key in obj.keys():
                if key == "Z_ObjectID":
                    indexKey = "MeshInfoIndex"
                    PrettyPrint(f"obj: {obj.name} id: {obj[key]} index: {obj[indexKey]}")
                    for otherObject in CustomObjects:
                        if obj[key] == otherObject[0] and obj[indexKey] == otherObject[1]:
                            PrettyPrint(f"found {obj}")
                            self.report({'ERROR'}, f"Multiple objects with the same HD2 properties are in the scene! Please delete one and try again.\nObjects:{otherObject[2]}, {obj.name}")
                            return True
                    CustomObjects.append([obj[key], obj[indexKey], obj.name])
    return False

def IncorrectVertexGroupNaming(self):
    for obj in bpy.context.selected_objects:
        incorrectGroups = 0
        try:
            ID = obj["Z_ObjectID"]
            InfoIndex = obj["MeshInfoIndex"]
        except:
            self.report({'ERROR'}, f"Couldn't find HD2 Properties in {obj.name}")
            return True
        groups = GetVertexGroupsFromID(ID, InfoIndex)
        if groups == None or len(groups) == 0:
            self.report({'WARNING'}, f"No Prior Loaded Vertex Groups Found, This May be Correct")
            return False
        if len(obj.vertex_groups) <= 0:
            self.report({'ERROR'}, f"No Vertex Groups Found for Object: {obj.name}")
            return True
        for group in obj.vertex_groups:
            if "_" not in group.name:
                incorrectGroups += 1
        if incorrectGroups > 0:
            self.report({'ERROR'}, f"Found {incorrectGroups} Incorrect Vertex Group Name Scheming for Object: {obj.name}")
            return True
        if len(groups) != len(obj.vertex_groups):
            self.report({'WARNING'}, f"Object: {obj.name} has a different number of vertex groups than expected")
            return False
    return False

def ObjectHasModifiers(self):
    for obj in bpy.context.selected_objects:
        if obj.modifiers:
            self.report({'ERROR'}, f"Object: {obj.name} has {len(obj.modifiers)} unapplied modifiers")
            return True
    return False

def ObjectHasShapeKeys(self):
    for obj in bpy.context.selected_objects:
        if hasattr(obj.data.shape_keys, 'key_blocks'):
            self.report({'ERROR'}, f"Object: {obj.name} has {len(obj.data.shape_keys.key_blocks)} unapplied shape keys")
            return True
    return False

def AllTransformsApplied(self):
    for obj in bpy.context.selected_objects:
        try:
            ID = obj["Z_ObjectID"]
            InfoIndex = obj["MeshInfoIndex"]
        except:
            self.report({'ERROR'}, f"Couldn't find HD2 Properties in {obj.name}")
            return True
        transforms = GetTransformsFromID(ID, InfoIndex)
        if transforms != None and obj.location == transforms[0] and obj.rotation_euler == transforms[1] and obj.scale == transforms[2]:
            PrettyPrint(f"Found Correct Transforms for Object: {obj.name}")
            return False
        else:
            if transforms == None: 
                PrettyPrint(f"Failed to find any Cashed Transforms for Object: {obj.name} ID: {ID}", "WARN")
                return False
            if obj.location != transforms[0]:
                PrettyPrint(f"Object Location: {obj.location} Expected Location: {transforms[0]}")
            if obj.rotation_euler != transforms[1]:
                PrettyPrint(f"Object Rotation: {obj.rotation_euler} Expected Rotation: {transforms[1]}")
            if obj.scale != transforms[2]:
                PrettyPrint(f"Object Scale: {obj.scale} Expected Scale: {transforms[2]}")
            self.report({'ERROR'}, f"Object: {obj.name} has mismatched transforms. See Console")
            return True
    return False

def MaterialsNumberNames(self):
    mesh_objs = [ob for ob in bpy.context.selected_objects if ob.type == 'MESH']
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

def HasZeroVerticies(self):
    mesh_objs = [ob for ob in bpy.context.selected_objects if ob.type == 'MESH']
    for mesh in mesh_objs:
        verts = len(mesh.data.vertices)
        PrettyPrint(f"Object: {mesh.name} Verticies: {verts}")
        if verts <= 0:
            self.report({'ERROR'}, f"Object: {mesh.name} has no zero verticies")
            return True
    return False

def MeshNotValidToSave(self):
    return PatchesNotLoaded(self) or DuplicateIDsInScene(self) or IncorrectVertexGroupNaming(self) or ObjectHasModifiers(self) or MaterialsNumberNames(self) or HasZeroVerticies(self) or ObjectHasShapeKeys(self)

def CopyToClipboard(txt):
    cmd='echo '+txt.strip()+'|clip'
    return subprocess.check_call(cmd, shell=True)

def hex_to_decimal(hex_string):
    try:
        decimal_value = int(hex_string, 16)
        return decimal_value
    except ValueError:
        print(f"Invalid hexadecimal string: {hex_string}")

def SearchByEntryID(self, file):
    if Global_searchpath == "":
        self.report({'ERROR'}, "Change Search Path!")
        return{'CANCELLED'}
    toc = StreamToc()
    found = []
    start_time = time.time()
    findme = open(file, "r")
    fileIDs = findme.read().splitlines()
    findme.close()

    forceSearch = bpy.context.scene.Hd2ToolPanelSettings.ForceSearchAll

    directorys = os.listdir(Global_gamepath)
    searched = 0
    foundIDs = 0
    totalIDs = len(fileIDs)
    PrettyPrint(f"Searching for {len(fileIDs)} IDs in {len(directorys)} files\n\n")
    for filename in directorys:
        searched += 1
        PrettyPrint(f"Searching: {filename}    File: {searched}/{len(directorys)}\r")
        f = os.path.join(Global_gamepath, filename)
        if not os.path.splitext(f)[1]:
            if os.path.isfile(f):
                toc.FromFile(f)
                for entry in toc.TocEntries:
                    for fileID in fileIDs:
                        ID = fileID.split()[0]
                        if ID.upper() != ID.lower():
                            ID = str(hex_to_decimal(ID))
                        if str(entry.FileID) == ID:
                            try:
                                name = fileID.split(" ", 1)[1]
                            except:
                                name = "No Name"
                            PrettyPrint("")
                            PrettyPrint(f"Archive: {filename} Entry ID: {ID} Name: {name}")
                            totaltime = time.time() - start_time
                            hours = round(totaltime / 3600)
                            minutes = round(totaltime / 60)
                            seconds = round(totaltime % 60)
                            PrettyPrint(f"Overall Time: {hours} hrs {minutes} min {seconds} sec")

                            foundItem = f"{filename} {name}"
                            if foundItem not in found:
                                found.append(foundItem)
                            if not forceSearch:
                                fileIDs.remove(fileID)
                                foundIDs += 1
                                PrettyPrint(f"Found {foundIDs}/{totalIDs} IDs\n")
                            else:
                                PrettyPrint(f"Found {foundIDs} total occurrences of any IDs\n")
                            if len(fileIDs) == 0:
                                PrettyPrint(f"Finished Searching {searched}/{len(directorys)} files")
                                curenttime = str(datetime.datetime.now()).replace(":", "-").replace(".", "_")
                                outputfile = f"{Global_searchpath}output_{curenttime}.txt"
                                output = open(outputfile, "w")
                                for item in found:
                                    output.write(item + "\n")
                                output.close()
                                PrettyPrint(f"Created Output file at {outputfile}")
                                return{'FINISHED'}
    if forceSearch:
        PrettyPrint(f"Finished Force Searching {searched} files")
    else:
        PrettyPrint(fileIDs)
        PrettyPrint(f"Could not find {len(fileIDs)} IDs", "ERROR")
    curenttime = str(datetime.datetime.now()).replace(":", "-").replace(".", "_")
    outputfile = f"{Global_searchpath}output_{curenttime}.txt"
    output = open(outputfile, "w")
    for item in found:
        output.write(item + "\n")
    output.close()
    PrettyPrint(f"Created Output file at {outputfile}")
    return{'FINISHED'}

class ChangeFilepathOperator(Operator, ImportHelper):
    bl_label = "Change Filepath"
    bl_idname = "helldiver2.change_filepath"
    bl_description = "Change the game's data folder directory"
    #filename_ext = "."
    use_filter_folder = True

    filter_glob: StringProperty(options={'HIDDEN'}, default='')

    def __init__(self):
        global Global_gamepath
        self.filepath = bpy.path.abspath(Global_gamepath)
        
    def execute(self, context):
        global Global_gamepath
        filepath = self.filepath
        steamapps = "steamapps"
        if steamapps in filepath:
            filepath = f"{filepath.partition(steamapps)[0]}steamapps\common\Helldivers 2\data\ "[:-1]
        else:
            self.report({'ERROR'}, f"Could not find steamapps folder in filepath: {filepath}")
            return{'CANCELLED'}
        Global_gamepath = filepath
        UpdateConfig()
        PrettyPrint(f"Changed Game File Path: {Global_gamepath}")
        return{'FINISHED'}
    
class ChangeSearchpathOperator(Operator, ImportHelper):
    bl_label = "Change Searchpath"
    bl_idname = "helldiver2.change_searchpath"
    bl_description = "Change the output directory for searching by entry ID"
    use_filter_folder = True

    filter_glob: StringProperty(options={'HIDDEN'}, default='')

    def __init__(self):
        global Global_searchpath
        self.filepath = bpy.path.abspath(Global_searchpath)
        
    def execute(self, context):
        global Global_searchpath
        Global_searchpath = self.filepath
        UpdateConfig()
        PrettyPrint(f"Changed Game Search Path: {Global_searchpath}")
        return{'FINISHED'}

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

class UnloadArchivesOperator(Operator):
    bl_label = "Unload Archives"
    bl_idname = "helldiver2.archive_unloadall"
    bl_description = "Unloads All Current Loaded Archives"

    def execute(self, context):
        Global_TocManager.UnloadArchives()
        return{'FINISHED'}
    
class UnloadPatchesOperator(Operator):
    bl_label = "Unload Patches"
    bl_idname = "helldiver2.patches_unloadall"
    bl_description = "Unloads All Current Loaded Patches"

    def execute(self, context):
        Global_TocManager.UnloadPatches()
        return{'FINISHED'}
    
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
        return SearchByEntryID(self, self.filepath)

class CreatePatchFromActiveOperator(Operator):
    bl_label = "Create Patch"
    bl_idname = "helldiver2.archive_createpatch"
    bl_description = "Creates Patch from Current Active Archive"

    def execute(self, context):
        if ArchivesNotLoaded(self):
            return{'CANCELLED'}
        
        if bpy.context.scene.Hd2ToolPanelSettings.PatchBaseArchiveOnly:
            baseArchivePath = Global_gamepath + BaseArchiveHexID
            Global_TocManager.LoadArchive(baseArchivePath)
            Global_TocManager.SetActiveByName(BaseArchiveHexID)
        else:
            self.report({'WARNING'}, f"Patch Created Was Not From Base Archive.")
        
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
        exportpath = filepath.replace(".zip", "")
        exportname = filepath.split(Global_backslash)[-1]
        
        patchName = Global_TocManager.ActivePatch.Name
        patchFile = Global_TocManager.ActivePatch.Name
        tempDirectory = bpy.app.tempdir + patchName
        patchPath = Global_gamepath + patchFile

        if not os.path.exists(tempDirectory):
            os.makedirs(tempDirectory)
        if not os.path.exists(patchPath):
            self.report({'ERROR'}, "No Patch Has Been Written Yet")
            return {'CANCELLED'}
        file = patchPath
        shutil.copyfile(file, f"{tempDirectory}\{patchFile}")
        file = patchPath + ".gpu_resources"
        shutil.copyfile(file, f"{tempDirectory}\{patchFile}.gpu_resources")
        file = patchPath + ".stream"
        shutil.copyfile(file, f"{tempDirectory}\{patchFile}.stream")
        shutil.make_archive(exportpath, 'zip', tempDirectory)

        if os.path.exists(filepath):
            self.report({'INFO'}, f"{patchName} Exported Successfully As {exportname}")
        else: 
            self.report({'ERROR'}, f"Failed to Export {patchName}")

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
#endregion

#region Operators: Entries

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
    
class MaterialTextureEntryOperator(Operator):
    bl_label  = "Texture Entry"
    bl_idname = "helldiver2.material_texture_entry"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        return{'FINISHED'}

    def invoke(self, context, event):
        return {'FINISHED'}
    
class MaterialShaderVariableEntryOperator(Operator):
    bl_label = "Shader Variable"
    bl_idname = "helldiver2.material_shader_variable"
    bl_description = "Material Shader Variable"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    value_index: bpy.props.IntProperty()
    value: bpy.props.FloatProperty(
        name="Variable Value",
        description="Enter a floating point number"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "value")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            Entry.LoadedData.ShaderVariables[self.variable_index].values[self.value_index] = self.value
            PrettyPrint(f"Set value to: {self.value} at variable: {self.variable_index} value: {self.value_index} for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class MaterialShaderVariableColorEntryOperator(Operator):
    bl_label = "Color Picker"
    bl_idname = "helldiver2.material_shader_variable_color"
    bl_description = "Material Shader Variable Color"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    color: bpy.props.FloatVectorProperty(
                name=f"Color",
                subtype="COLOR",
                size=3,
                min=0.0,
                max=1.0,
                default=(1.0, 1.0, 1.0)
            )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                Entry.LoadedData.ShaderVariables[self.variable_index].values[idx] = self.color[idx]
            PrettyPrint(f"Set color to: {self.color}for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return {'FINISHED'}
    
    def invoke(self, context, event):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                self.color[idx] = Entry.LoadedData.ShaderVariables[self.variable_index].values[idx]
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

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
        if Global_TocManager.ActivePatch == None:
            raise Exception("No patch exists, please create one first")

        Entries = EntriesFromStrings(self.object_id, self.object_typeid)
        for Entry in Entries:
            if Entry != None:
                if not Entry.IsLoaded: Entry.Load(False, False)
                path = self.filepath
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
        return{'FINISHED'}

#endregion

#region Operators: Meshes

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
        try:
            ID = bpy.context.selected_objects[0]["Z_ObjectID"]
        except:
            self.report({'ERROR'}, f"{bpy.context.selected_objects[0].name} has no HD2 custom properties")
            return{'CANCELLED'}
        model = GetObjectsMeshData()
        BlenderOpts = bpy.context.scene.Hd2ToolPanelSettings.get_settings_dict()
        Entry = Global_TocManager.GetEntry(int(ID), MeshID)
        m = model[ID]
        for n in range(len(Entry.LoadedData.RawMeshes)):
            if Entry.LoadedData.RawMeshes[n].MeshInfoIndex == m.MeshInfoIndex:
                Entry.LoadedData.RawMeshes[n] = m
                break
        wasSaved = Entry.Save(BlenderOpts=BlenderOpts)
        if not wasSaved:
                for object in bpy.data.objects:
                    try:
                        ID = object["Z_ObjectID"]
                        self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Object: {object.name} ID: {ID}")
                        return{'CANCELLED'}
                    except:
                        self.report({'ERROR'}, f"Failed to find object with custom property ID. Object: {object.name}")
                        return{'CANCELLED'}
        self.report({'INFO'}, f"Saved Mesh Object ID: {self.object_id}")
        return{'FINISHED'}

class BatchSaveStingrayMeshOperator(Operator):
    bl_label  = "Save Meshes"
    bl_idname = "helldiver2.archive_mesh_batchsave"
    bl_description = "Saves Meshes"
    bl_options = {'REGISTER', 'UNDO'} 

    def execute(self, context):
        start = time.time()
        if MeshNotValidToSave(self):
            return{'CANCELLED'}

        objects = bpy.context.selected_objects
        if len(objects) == 0:
            self.report({'WARNING'}, "No Objects Selected")
        #bpy.ops.object.select_all(action='DESELECT')
        IDs = []
        for object in objects:
            try:
                ID = object["Z_ObjectID"]
                if ID not in IDs:
                    IDs.append(ID)
            except:
                self.report({'ERROR'}, f"{object.name} has no HD2 custom properties")
                return{'CANCELLED'}
        MeshData = GetObjectsMeshData()
        BlenderOpts = bpy.context.scene.Hd2ToolPanelSettings.get_settings_dict()
        for ID in IDs:
            Entry = Global_TocManager.GetEntry(int(ID), MeshID)
            BlenderMesh = MeshData[ID]
            for n in range(len(Entry.LoadedData.RawMeshes)):
                if Entry.LoadedData.RawMeshes[n].MeshInfoIndex == BlenderMesh.MeshInfoIndex:
                    Entry.LoadedData.RawMeshes[n] = BlenderMesh
                    break
            wasSaved = Entry.Save(BlenderOpts=BlenderOpts)
            if not wasSaved:
                for object in bpy.data.objects:
                    try:
                        if ID == object["Z_ObjectID"]:
                            self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Object: {object.name}")
                            return{'CANCELLED'}
                    except:
                        PrettyPrint(f"Couldn't find Object: {object.name} at ID: {ID}")
                self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Could not find custom property object at ID: {ID}")
                return{'CANCELLED'}
        print("Saving mesh materials")
        SaveMeshMaterials(objects)
        self.report({'INFO'}, f"Saved {len(objects)} Meshes")
        PrettyPrint(f"Time to save meshes: {time.time()-start}")
        return{'FINISHED'}

def SaveMeshMaterials(objects):
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


#endregion

#region Operators: Textures

# save texture from blender to archive button
# TODO: allow the user to choose an image, instead of looking for one of the same name
class SaveTextureFromBlendImageOperator(Operator):
    bl_label = "Save Texture"
    bl_idname = "helldiver2.texture_saveblendimage"
    bl_description = "Saves Texture"

    object_id: StringProperty()
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        Entries = EntriesFromString(self.object_id, TexID)
        for Entry in Entries:
            if Entry != None:
                if not Entry.IsLoaded: Entry.Load()
                try:
                    BlendImageToStingrayTexture(bpy.data.images[str(self.object_id)], Entry.LoadedData)
                except:
                    PrettyPrint("No blend texture was found for saving, using original", "warn"); pass
            Global_TocManager.Save(Entry.FileID, TexID)
        return{'FINISHED'}

# import texture from archive button
class ImportTextureOperator(Operator):
    bl_label = "Import Texture"
    bl_idname = "helldiver2.texture_import"
    bl_description = "Loads Texture into Blender Project"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), TexID)
        return{'FINISHED'}

# export texture to file
class ExportTextureOperator(Operator, ExportHelper):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_export"
    bl_description = "Export Texture to a Desired File Location"
    filename_ext = ".dds"

    filter_glob: StringProperty(default='*.dds', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            data = Entry.Load(False, False)
            with open(self.filepath, 'w+b') as f:
                f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}
    
    def invoke(self, context, _event):
        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = self.object_id
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]

            self.filepath = blend_filepath + self.filename_ext

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class ExportTexturePNGOperator(Operator, ExportHelper):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_export_png"
    bl_description = "Export Texture to a Desired File Location"
    filename_ext = ".png"

    filter_glob: StringProperty(default='*.png', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Global_TocManager.Load(int(self.object_id), TexID)
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            tempdir = tempfile.gettempdir()
            for i in range(Entry.LoadedData.ArraySize):
                filename = self.filepath.split(Global_backslash)[-1]
                directory = self.filepath.replace(filename, "")
                filename = filename.replace(".png", "")
                layer = "" if Entry.LoadedData.ArraySize == 1 else f"_layer{i}"
                dds_path = f"{tempdir}\\{filename}{layer}.dds"
                with open(dds_path, 'w+b') as f:
                    if Entry.LoadedData.ArraySize == 1:
                        f.write(Entry.LoadedData.ToDDS())
                    else:
                        f.write(Entry.LoadedData.ToDDSArray()[i])
                subprocess.run([Global_texconvpath, "-y", "-o", directory, "-ft", "png", "-f", "R8G8B8A8_UNORM", "-sepalpha", "-alpha", dds_path])
                if os.path.isfile(dds_path):
                    self.report({'INFO'}, f"Saved PNG Texture to: {dds_path}")
                else:
                    self.report({'ERROR'}, f"Failed to Save Texture: {dds_path}")
        return{'FINISHED'}
    
    def invoke(self, context, event):
        blend_filepath = context.blend_data.filepath
        filename = f"{self.object_id}.png"
        self.filepath = blend_filepath + filename
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# batch export texture to file
class BatchExportTextureOperator(Operator):
    bl_label = "Export Textures"
    bl_idname = "helldiver2.texture_batchexport"
    bl_description = "Export Textures to a Desired File Location"
    filename_ext = ".dds"

    directory: StringProperty(name="Outdir Path",description="dds output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Entry = Global_TocManager.GetEntry(EntryID, TexID)
            if Entry != None:
                data = Entry.Load(False, False)
                with open(self.directory + str(Entry.FileID)+".dds", 'w+b') as f:
                    f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class BatchExportTexturePNGOperator(Operator):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_batchexport_png"
    bl_description = "Export Textures to a Desired File Location"
    filename_ext = ".png"

    directory: StringProperty(name="Outdir Path",description="png output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        exportedfiles = 0
        for EntryID in EntriesIDs:
            Global_TocManager.Load(EntryID, TexID)
            Entry = Global_TocManager.GetEntry(EntryID, TexID)
            if Entry != None:
                tempdir = tempfile.gettempdir()
                dds_path = f"{tempdir}\\{EntryID}.dds"
                with open(dds_path, 'w+b') as f:
                    f.write(Entry.LoadedData.ToDDS())
                subprocess.run([Global_texconvpath, "-y", "-o", self.directory, "-ft", "png", "-f", "R8G8B8A8_UNORM", "-alpha", dds_path])
                filepath = f"{self.directory}\\{EntryID}.png"
                if os.path.isfile(filepath):
                    exportedfiles += 1
                else:
                    self.report({'ERROR'}, f"Failed to save texture as PNG: {filepath}")
        self.report({'INFO'}, f"Exported {exportedfiles} PNG Files To: {self.directory}")
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# import texture from archive button
class SaveTextureFromDDSOperator(Operator, ImportHelper):
    bl_label = "Import DDS"
    bl_idname = "helldiver2.texture_savefromdds"
    bl_description = "Override Current Texture with a Selected DDS File"

    filter_glob: StringProperty(default='*.dds', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        SaveImageDDS(self.filepath, self.object_id)
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return{'FINISHED'}


class SaveTextureFromPNGOperator(Operator, ImportHelper):
    bl_label = "Import PNG"
    bl_idname = "helldiver2.texture_savefrompng"
    bl_description = "Override Current Texture with a Selected PNG File"

    filter_glob: StringProperty(default='*.png', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        SaveImagePNG(self.filepath, self.object_id)
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return{'FINISHED'}

def SaveImagePNG(filepath, object_id):
    Entry = Global_TocManager.GetEntry(int(object_id), TexID)
    if Entry != None:
        if len(filepath) > 1:
            # get texture data
            Entry.Load()
            StingrayTex = Entry.LoadedData
            tempdir = tempfile.gettempdir()
            PrettyPrint(filepath)
            PrettyPrint(StingrayTex.Format)
            subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-dx10", "-f", StingrayTex.Format, "-sepalpha", "-alpha", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            nameIndex = filepath.rfind("\.".strip(".")) + 1
            fileName = filepath[nameIndex:].replace(".png", ".dds")
            dds_path = f"{tempdir}\\{fileName}"
            PrettyPrint(dds_path)
            if not os.path.exists(dds_path):
                raise Exception(f"Failed to convert to dds texture for: {dds_path}")
            with open(dds_path, 'r+b') as f:
                StingrayTex.FromDDS(f.read())
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture to entry
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)

            Global_TocManager.Save(int(object_id), TexID)

def SaveImageDDS(filepath, object_id):
    Entry = Global_TocManager.GetEntry(int(object_id), TexID)
    if Entry != None:
        if len(filepath) > 1:
            PrettyPrint(f"Saving image DDS: {filepath} to ID: {object_id}")
            # get texture data
            Entry.Load()
            StingrayTex = Entry.LoadedData
            with open(filepath, 'r+b') as f:
                StingrayTex.FromDDS(f.read())
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture to entry
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)

            Global_TocManager.Save(int(object_id), TexID)
#endregion

#region Operators: Materials

class SaveMaterialOperator(Operator):
    bl_label = "Save Material"
    bl_idname = "helldiver2.material_save"
    bl_description = "Saves Material"

    object_id: StringProperty()
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Save(int(EntryID), MaterialID)
        return{'FINISHED'}

class ImportMaterialOperator(Operator):
    bl_label = "Import Material"
    bl_idname = "helldiver2.material_import"
    bl_description = "Loads Materials into Blender Project"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), MaterialID)
        return{'FINISHED'}

class AddMaterialOperator(Operator):
    bl_label = "Add Material"
    bl_idname = "helldiver2.material_add"
    bl_description = "Adds a New Material to Current Active Patch"

    global Global_Materials
    selected_material: EnumProperty(items=Global_Materials, name="Template", default=0)

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        
        CreateModdedMaterial(self.selected_material)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
class SetMaterialTemplateOperator(Operator):
    bl_label = "Set Template"
    bl_idname = "helldiver2.material_set_template"
    bl_description = "Sets the material to a modded material template"
    
    global Global_Materials
    selected_material: EnumProperty(items=Global_Materials, name="Template", default=0)

    entry_id: StringProperty()

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        
        PrettyPrint(f"Found: {self.entry_id}")
            
        Entry = Global_TocManager.GetEntry(int(self.entry_id), MaterialID)
        if not Entry:
            raise Exception(f"Could not find entry at ID: {self.entry_id}")

        Entry.MaterialTemplate = self.selected_material
        Entry.Load(True)
        
        PrettyPrint(f"Finished Set Template: {self.selected_material}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def CreateModdedMaterial(template, ID=None):
    path = f"{Global_materialpath}\\{template}.material"
    if not os.path.exists(path):
        raise Exception(f"Selected material template: {template} does not exist")

    Entry = TocEntry()
    if ID == None:
        Entry.FileID = RandomHash16()
        PrettyPrint(f"File ID is now: {Entry.FileID}")
    else:
        Entry.FileID = ID
        PrettyPrint(f"Found pre-existing file ID: {ID}")

    Entry.TypeID = MaterialID
    Entry.MaterialTemplate = template
    Entry.IsCreated = True
    with open(path, 'r+b') as f:
        data = f.read()
    Entry.TocData_OLD   = data
    Entry.TocData       = data

    Global_TocManager.AddNewEntryToPatch(Entry)
        
    EntriesIDs = IDsFromString(str(Entry.FileID))
    for EntryID in EntriesIDs:
        Global_TocManager.Load(int(EntryID), MaterialID)

class ShowMaterialEditorOperator(Operator):
    bl_label = "Show Material Editor"
    bl_idname = "helldiver2.material_showeditor"
    bl_description = "Show List of Textures in Material"

    object_id: StringProperty()
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if not Entry.IsLoaded: Entry.Load(False, False)
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                mat.DEV_ShowEditor = False
            else:
                mat.DEV_ShowEditor = True
        return{'FINISHED'}

class SetMaterialTexture(Operator, ImportHelper):
    bl_label = "Set Material Texture"
    bl_idname = "helldiver2.material_settex"

    filename_ext = ".dds"

    filter_glob: StringProperty(default="*.dds", options={'HIDDEN'})

    object_id: StringProperty(options={"HIDDEN"})
    tex_idx: IntProperty(options={"HIDDEN"})

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if Entry.IsLoaded:
                Entry.LoadedData.DEV_DDSPaths[self.tex_idx] = self.filepath
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

#endregion

#region Operators: Particles
class SaveStingrayParticleOperator(Operator):
    bl_label  = "Save Particle"
    bl_idname = "helldiver2.particle_save"
    bl_description = "Saves Particle"
    bl_options = {'REGISTER', 'UNDO'} 

    object_id: StringProperty()
    def execute(self, context):
        mode = context.mode
        if mode != 'OBJECT':
            self.report({'ERROR'}, f"You are Not in OBJECT Mode. Current Mode: {mode}")
            return {'CANCELLED'}
        if MeshNotValidToSave(self):
            return {'CANCELLED'}
        wasSaved = Global_TocManager.Save(int(self.object_id), ParticleID)

        # we can handle below later when we put a particle object into the blender scene

        # if not wasSaved:
        #         for object in bpy.data.objects:
        #             try:
        #                 ID = object["Z_ObjectID"]
        #                 self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Object: {object.name} ID: {ID}")
        #                 return{'CANCELLED'}
        #             except:
        #                 self.report({'ERROR'}, f"Failed to find object with custom property ID. Object: {object.name}")
        #                 return{'CANCELLED'}
        # self.report({'INFO'}, f"Saved Mesh Object ID: {self.object_id}")
        return{'FINISHED'}
class ImportStingrayParticleOperator(Operator):
    bl_label = "Import Particle"
    bl_idname = "helldiver2.archive_particle_import"
    bl_description = "Loads Particles into Blender Scene"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        Errors = []
        for EntryID in EntriesIDs:
            if len(EntriesIDs) == 1:
                Global_TocManager.Load(EntryID, ParticleID)
            else:
                try:
                    Global_TocManager.Load(EntryID, ParticleID)
                except Exception as error:
                    Errors.append([EntryID, error])

        if len(Errors) > 0:
            PrettyPrint("\nThese errors occurred while attempting to load particles...", "error")
            idx = 0
            for error in Errors:
                PrettyPrint(f"  Error {idx}: for particle {error[0]}", "error")
                PrettyPrint(f"    {error[1]}\n", "error")
                idx += 1
            raise Exception("One or more particles failed to load")
        return{'FINISHED'}
#endregion

#region Operators: Clipboard Functionality

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
        cmd='echo '+str(self.text).strip()+'|clip'
        subprocess.check_call(cmd, shell=True)
        self.report({'INFO'}, f"Copied: {self.text}")
        return{'FINISHED'}

#endregion

#region Operators: UI/UX

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

class SearchArchivesOperator(Operator):
    bl_label = "Search Found Archives"
    bl_idname = "helldiver2.search_archives"
    bl_description = "Search from Found Archives"

    SearchField : StringProperty(name="SearchField", default="")
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "SearchField", icon='VIEWZOOM')
        # Update displayed archives
        if self.PrevSearch != self.SearchField:
            self.PrevSearch = self.SearchField

            self.ArchivesToDisplay = []
            for Entry in Global_ArchiveHashes:
                if Entry[1].lower().find(self.SearchField.lower()) != -1:
                    self.ArchivesToDisplay.append([Entry[0], Entry[1]])
    
        if self.SearchField != "" and len(self.ArchivesToDisplay) == 0:
            row = layout.row(); row.label(text="No Archive IDs Found")
            row = layout.row(); row.label(text="Know an ID that's Not Here?")
            row = layout.row(); row.label(text="Make an issue on the github.")
            row = layout.row(); row.label(text="Archive ID and In Game Name")
            row = layout.row(); row.operator("helldiver2.github", icon= 'URL')

        else:
            for Archive in self.ArchivesToDisplay:
                row = layout.row()
                row.label(text=Archive[1], icon='GROUP')
                row.operator("helldiver2.archives_import", icon= 'FILE_NEW', text="").paths_str = Global_gamepath + str(Archive[0])

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        self.PrevSearch = "NONE"
        self.ArchivesToDisplay = []

        wm = context.window_manager
        return wm.invoke_props_dialog(self)

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

#endregion

#region Operators: Help

class HelpOperator(Operator):
    bl_label  = "Help"
    bl_idname = "helldiver2.help"
    bl_description = "Link to Modding Discord"

    def execute(self, context):
        url = "https://discord.gg/helldiversmodding"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

class ArchiveSpreadsheetOperator(Operator):
    bl_label  = "Archive Spreadsheet"
    bl_idname = "helldiver2.archive_spreadsheet"
    bl_description = "Opens Spreadsheet with Indentified Archives"

    def execute(self, context):
        url = "https://docs.google.com/spreadsheets/d/1oQys_OI5DWou4GeRE3mW56j7BIi4M7KftBIPAl1ULFw"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

class GithubOperator(Operator):
    bl_label  = "Github"
    bl_idname = "helldiver2.github"
    bl_description = "Opens The Github Page"

    def execute(self, context):
        url = "https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}
    
class LatestReleaseOperator(Operator):
    bl_label  = "Update Helldivers 2 SDK"
    bl_idname = "helldiver2.latest_release"
    bl_description = "Opens The Github Page to the latest release"

    def execute(self, context):
        url = "https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/releases/latest"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

class MeshFixOperator(Operator, ImportHelper):
    bl_label = "Fix Meshes"
    bl_idname = "helldiver2.meshfixtool"
    bl_description = "Auto-fixes meshes in the currently loaded patch. Warning, this may take some time."

    directory: StringProperty(
        name="Directory",
        description="Choose a directory",
        subtype='DIR_PATH'
    )
    
    filter_folder: BoolProperty(
        default=True,
        options={'HIDDEN'}
    )
    
    use_filter_folder = True
    def execute(self, context):   
        path = self.directory
        output = RepatchMeshes(self, path)
        if output == {'CANCELLED'}: return {'CANCELLED'}
        
        return{'FINISHED'}
#endregion

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
    
    if len(Global_TocManager.LoadedArchives) < len(Global_ArchiveHashes) - 10:
        for hash in Global_ArchiveHashes:
            path = f"{Global_gamepath}{hash[0]}"
            if os.path.exists(path):
                Global_TocManager.LoadArchive(path)

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
            
#region Operators: Context Menu

stored_custom_properties = {}
class CopyCustomPropertyOperator(Operator):
    bl_label = "Copy HD2 Properties"
    bl_idname = "helldiver2.copy_custom_properties"
    bl_description = "Copies Custom Property Data for Helldivers 2 Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties
        
        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}
        PrettyPrint(selectedObjects)

        obj = context.active_object
        stored_custom_properties.clear()
        for key, value in obj.items():
            if key not in obj.bl_rna.properties:  # Skip built-in properties
                stored_custom_properties[key] = value

        self.report({'INFO'}, f"Copied {len(stored_custom_properties)} custom properties")
        return {'FINISHED'}

class PasteCustomPropertyOperator(Operator):
    bl_label = "Paste HD2 Properties"
    bl_idname = "helldiver2.paste_custom_properties"
    bl_description = "Pastes Custom Property Data for Helldivers 2 Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties

        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}

        obj = context.active_object
        if not stored_custom_properties:
            self.report({'WARNING'}, "No custom properties to paste")
            return {'CANCELLED'}

        for key, value in stored_custom_properties.items():
            obj[key] = value

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        self.report({'INFO'}, f"Pasted {len(stored_custom_properties)} custom properties")
        return {'FINISHED'}

def CustomPropertyContext(self, context):
    layout = self.layout
    layout.separator()
    layout.label(text=Global_SectionHeader)
    layout.separator()
    layout.operator("helldiver2.copy_hex_id", icon='COPY_ID')
    layout.operator("helldiver2.copy_decimal_id", icon='COPY_ID')
    layout.separator()
    layout.operator("helldiver2.copy_custom_properties", icon= 'COPYDOWN')
    layout.operator("helldiver2.paste_custom_properties", icon= 'PASTEDOWN')
    layout.operator("helldiver2.archive_mesh_batchsave", icon= 'FILE_BLEND')

class CopyArchiveIDOperator(Operator):
    bl_label = "Copy Archive ID"
    bl_idname = "helldiver2.copy_archive_id"
    bl_description = "Copies the Active Archive's ID to Clipboard"

    def execute(self, context):
        if ArchivesNotLoaded(self):
            return {'CANCELLED'}
        archiveID = str(Global_TocManager.ActiveArchive.Name)
        bpy.context.window_manager.clipboard = archiveID
        self.report({'INFO'}, f"Copied Archive ID: {archiveID}")

        return {'FINISHED'}
    
class CopyHexIDOperator(Operator):
    bl_label = "Copy Hex ID"
    bl_idname = "helldiver2.copy_hex_id"
    bl_description = "Copy the Hexidecimal ID of the selected mesh for the Diver tool"

    def execute(self, context):
        object = context.active_object
        if not object:
            self.report({"ERROR"}, "No object is selected")
        try:
            ID = int(object["Z_ObjectID"])
        except:
            self.report({'ERROR'}, f"Object: {object.name} has not Helldivers property ID")
            return {'CANCELLED'}

        try:
            hexID = hex(ID)
        except:
            self.report({'ERROR'}, f"Object: {object.name} ID: {ID} cannot be converted to hex")
            return {'CANCELLED'}
        
        CopyToClipboard(hexID)
        self.report({'INFO'}, f"Copied {object.name}'s property of {hexID}")
        return {'FINISHED'}

class CopyDecimalIDOperator(Operator):
    bl_label = "Copy ID"
    bl_idname = "helldiver2.copy_decimal_id"
    bl_description = "Copy the decimal ID of the selected mesh"

    def execute(self, context):
        object = context.active_object
        if not object:
            self.report({"ERROR"}, "No object is selected")
        try:
            ID = str(object["Z_ObjectID"])
        except:
            self.report({'ERROR'}, f"Object: {object.name} has not Helldivers property ID")
            return {'CANCELLED'}
        
        CopyToClipboard(ID)
        self.report({'INFO'}, f"Copied {object.name}'s property of {ID}")
        return {'FINISHED'}

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
#endregion

#region Menus and Panels

def LoadedArchives_callback(scene, context):
    return [(Archive.Name, GetArchiveNameFromID(Archive.Name) if GetArchiveNameFromID(Archive.Name) != "" else Archive.Name, Archive.Name) for Archive in Global_TocManager.LoadedArchives]

def Patches_callback(scene, context):
    return [(Archive.Name, Archive.Name, Archive.Name) for Archive in Global_TocManager.Patches]

class Hd2ToolPanelSettings(PropertyGroup):
    # Patches
    Patches   : EnumProperty(name="Patches", items=Patches_callback)
    PatchOnly : BoolProperty(name="Show Patch Entries Only", description = "Filter list to entries present in current patch", default = False)
    # Archive
    ContentsExpanded : BoolProperty(default = True)
    LoadedArchives   : EnumProperty(name="LoadedArchives", items=LoadedArchives_callback)
    # Settings
    MenuExpanded     : BoolProperty(default = False)

    ShowExtras       : BoolProperty(name="Extra Entry Types", description = "Shows all Extra entry types.", default = False)
    FriendlyNames    : BoolProperty(name="Show Friendly Names", description="Enable friendly names for entries if they have any. Disabling this option can greatly increase UI preformance if a patch has a large number of entries.", default = True)

    ImportMaterials  : BoolProperty(name="Import Materials", description = "Fully import materials by appending the textures utilized, otherwise create placeholders", default = True)
    ImportLods       : BoolProperty(name="Import LODs", description = "Import LODs", default = False)
    ImportGroup0     : BoolProperty(name="Import Group 0 Only", description = "Only import the first vertex group, ignore others", default = True)
    ImportCulling    : BoolProperty(name="Import Culling Bounds", description = "Import Culling Bodies", default = False)
    ImportStatic     : BoolProperty(name="Import Static Meshes", description = "Import Static Meshes", default = False)
    MakeCollections  : BoolProperty(name="Make Collections", description = "Make new collection when importing meshes", default = False)
    Force2UVs        : BoolProperty(name="Force 2 UV Sets", description = "Force at least 2 UV sets, some materials require this", default = True)
    Force1Group      : BoolProperty(name="Force 1 Group", description = "Force mesh to only have 1 vertex group", default = True)
    AutoLods         : BoolProperty(name="Auto LODs", description = "Automatically generate LOD entries based on LOD0, does not actually reduce the quality of the mesh", default = True)
    RemoveGoreMeshes : BoolProperty(name="Remove Gore Meshes", description = "Automatically delete all of the verticies with the gore material when loading a model", default = False)
    # Search
    SearchField      : StringProperty(default = "")

    # Tools
    EnableTools           : BoolProperty(name="Special Tools", description = "Enable advanced SDK Tools", default = False)
    UnloadEmptyArchives   : BoolProperty(name="Unload Empty Archives", description="Unload Archives that do not Contain any Textures, Materials, or Meshes", default = True)
    DeleteOnLoadArchive   : BoolProperty(name="Nuke Files on Archive Load", description="Delete all Textures, Materials, and Meshes in project when selecting a new archive", default = False)
    ForceSearchAll        : BoolProperty(name="Force Search All Files", description="Searches for all IDs in every file instead of ending early")
    UnloadPatches         : BoolProperty(name="Unload Previous Patches", description="Unload Previous Patches when bulk loading")

    SaveNonSDKMaterials   : BoolProperty(name="Save Non-SDK Materials", description="Toggle if non-SDK materials should be autosaved when saving a mesh", default = False)
    PatchBaseArchiveOnly  : BoolProperty(name="Patch Base Archive Only", description="When enabled, it will allow patched to only be created if the base archive is selected. This is helpful for new users.", default = True)
    LegacyWeightNames     : BoolProperty(name="Legacy Weight Names", description="Brings back the old naming system for vertex groups using the X_Y schema", default = True)
    
    def get_settings_dict(self):
        dict = {}
        dict["MenuExpanded"] = self.MenuExpanded
        dict["ShowExtras"] = self.ShowExtras
        dict["Force2UVs"] = self.Force2UVs
        dict["Force1Group"] = self.Force1Group
        dict["AutoLods"] = self.AutoLods
        return dict

class HellDivers2ToolsPanel(Panel):
    bl_label = f"Helldivers 2 SDK: Community Edition v{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
    bl_idname = "SF_PT_Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Modding"

    def draw_material_editor(self, Entry, layout, row):
        if Entry.IsLoaded:
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                for i, t in enumerate(mat.TexIDs):
                    row = layout.row(); row.separator(factor=2.0)
                    ddsPath = mat.DEV_DDSPaths[i]
                    if ddsPath != None: filepath = Path(ddsPath)
                    label = filepath.name if ddsPath != None else str(t)
                    if Entry.MaterialTemplate != None:
                        label = TextureTypeLookup[Entry.MaterialTemplate][i] + ": " + label
                    row.operator("helldiver2.material_texture_entry", icon='FILE_IMAGE', text=label, emboss=False).object_id = str(t)
                    # props = row.operator("helldiver2.material_settex", icon='FILEBROWSER', text="")
                    # props.object_id = str(Entry.FileID)
                    # props.tex_idx = i
                for i, variable in enumerate(mat.ShaderVariables):
                    row = layout.row(); row.separator(factor=2.0)
                    split = row.split(factor=0.5)
                    row = split.column()
                    row.alignment = 'RIGHT'
                    name = variable.ID
                    if variable.name != "": name = variable.name
                    row.label(text=f"{variable.klassName}: {name}", icon='OPTIONS')
                    row = split.column()
                    row.alignment = 'LEFT'
                    sections = len(variable.values)
                    if sections == 3: sections = 4 # add an extra for the color picker
                    row = row.split(factor=1/sections)
                    for j, value in enumerate(variable.values):
                        ShaderVariable = row.operator("helldiver2.material_shader_variable", text=str(round(value, 2)))
                        ShaderVariable.value = value
                        ShaderVariable.object_id = str(Entry.FileID)
                        ShaderVariable.variable_index = i
                        ShaderVariable.value_index = j
                    if len(variable.values) == 3:
                        ColorPicker = row.operator("helldiver2.material_shader_variable_color", text="", icon='EYEDROPPER')
                        ColorPicker.object_id = str(Entry.FileID)
                        ColorPicker.variable_index = i

    def draw_entry_buttons(self, box, row, Entry, PatchOnly):
        if Entry.TypeID == MeshID:
            row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
        elif Entry.TypeID == TexID:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.texture_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
        elif Entry.TypeID == MaterialID:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_showeditor", icon='MOD_LINEART', text="").object_id = str(Entry.FileID)
            self.draw_material_editor(Entry, box, row)
        elif Entry.TypeID == ParticleID:
            row.operator("helldiver2.particle_save", icon='FILE_BLEND', text = "").object_id = str(Entry.FileID)
            row.operator("helldiver2.archive_particle_import", icon='IMPORT', text = "").object_id = str(Entry.FileID)
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='FAKE_USER_ON', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='FAKE_USER_OFF', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if PatchOnly:
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        global OnCorrectBlenderVersion
        if not OnCorrectBlenderVersion:
            row.label(text="Using Incorrect Blender Version!")
            row = layout.row()
            row.label(text="Please Use Blender 4.0.X to 4.3.X")
            return
        
        if bpy.app.version[1] > 0:
            row.label(text="Warning! Soft Supported Blender Version. Issues may Occur.", icon='ERROR')


        row = layout.row()
        row.alignment = 'CENTER'
        global Global_addonUpToDate
        global Global_latestAddonVersion

        if Global_addonUpToDate == None:
            row.label(text="Addon Failed to Check latest Version")
        elif not Global_addonUpToDate:
            row.label(text="Addon is Outdated!")
            row.label(text=f"Latest Version: {Global_latestAddonVersion}")
            row = layout.row()
            row.alignment = 'CENTER'
            row.scale_y = 2
            row.operator("helldiver2.latest_release", icon = 'URL')
            row.separator()

        # Draw Settings, Documentation and Spreadsheet
        mainbox = layout.box()
        row = mainbox.row()
        row.prop(scene.Hd2ToolPanelSettings, "MenuExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.MenuExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text="Settings")
        row.label(icon="SETTINGS")
        
        if scene.Hd2ToolPanelSettings.MenuExpanded:
            row = mainbox.grid_flow(columns=2)
            row = mainbox.row(); row.separator(); row.label(text="Display Types"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ShowExtras")
            row.prop(scene.Hd2ToolPanelSettings, "FriendlyNames")
            row = mainbox.row(); row.separator(); row.label(text="Import Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ImportMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "ImportLods")
            row.prop(scene.Hd2ToolPanelSettings, "ImportGroup0")
            row.prop(scene.Hd2ToolPanelSettings, "MakeCollections")
            row.prop(scene.Hd2ToolPanelSettings, "ImportCulling")
            row.prop(scene.Hd2ToolPanelSettings, "ImportStatic")
            row.prop(scene.Hd2ToolPanelSettings, "RemoveGoreMeshes")
            row = mainbox.row(); row.separator(); row.label(text="Export Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "Force2UVs")
            row.prop(scene.Hd2ToolPanelSettings, "Force1Group")
            row.prop(scene.Hd2ToolPanelSettings, "AutoLods")
            row = mainbox.row(); row.separator(); row.label(text="Other Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "SaveNonSDKMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "PatchBaseArchiveOnly")
            #row.prop(scene.Hd2ToolPanelSettings, "LegacyWeightNames")

            #Custom Searching tools
            row = mainbox.row(); row.separator(); row.label(text="Special Tools"); box = row.box(); row = box.grid_flow(columns=1)
            # Draw Bulk Loader Extras
            row.prop(scene.Hd2ToolPanelSettings, "EnableTools")
            if scene.Hd2ToolPanelSettings.EnableTools:
                row = mainbox.row(); box = row.box(); row = box.grid_flow(columns=1)
                #row.label()
                row.label(text="WARNING! Developer Tools, Please Know What You Are Doing!")
                row.prop(scene.Hd2ToolPanelSettings, "UnloadEmptyArchives")
                row.prop(scene.Hd2ToolPanelSettings, "ForceSearchAll")
                row.prop(scene.Hd2ToolPanelSettings, "UnloadPatches")
                #row.prop(scene.Hd2ToolPanelSettings, "DeleteOnLoadArchive")
                col = box.grid_flow(columns=2)
                col.operator("helldiver2.bulk_load", icon= 'IMPORT', text="Bulk Load")
                col.operator("helldiver2.search_by_entry", icon= 'VIEWZOOM')
                #row = box.grid_flow(columns=1)
                row.operator("helldiver2.meshfixtool", icon='MODIFIER')
                search = mainbox.row()
                search.label(text=Global_searchpath)
                search.operator("helldiver2.change_searchpath", icon='FILEBROWSER')
                mainbox.separator()
            row = mainbox.row()
            row.label(text=Global_gamepath)
            row.operator("helldiver2.change_filepath", icon='FILEBROWSER')
            mainbox.separator()

        # Draw Archive Import/Export Buttons
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.help", icon='HELP', text="Discord")
        row.operator("helldiver2.archive_spreadsheet", icon='INFO', text="Archive IDs")
        row.operator("helldiver2.github", icon='URL', text= "")
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.archive_import_default", icon= 'SOLO_ON', text="")
        row.operator("helldiver2.search_archives", icon= 'VIEWZOOM')
        row.operator("helldiver2.archive_unloadall", icon= 'FILE_REFRESH', text="")
        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "LoadedArchives", text="Archives")
        if scene.Hd2ToolPanelSettings.EnableTools:
            row.scale_x = 0.33
            ArchiveNum = "0/0"
            if Global_TocManager.ActiveArchive != None:
                Archiveindex = Global_TocManager.LoadedArchives.index(Global_TocManager.ActiveArchive) + 1
                Archiveslength = len(Global_TocManager.LoadedArchives)
                ArchiveNum = f"{Archiveindex}/{Archiveslength}"
            row.operator("helldiver2.next_archive", icon= 'RIGHTARROW', text=ArchiveNum)
            row.scale_x = 1
        row.operator("helldiver2.archive_import", icon= 'FILEBROWSER', text= "").is_patch = False
        row = layout.row()
        if len(Global_TocManager.LoadedArchives) > 0:
            Global_TocManager.SetActiveByName(scene.Hd2ToolPanelSettings.LoadedArchives)


        # Draw Patch Stuff
        row = layout.row(); row = layout.row()

        row.operator("helldiver2.archive_createpatch", icon= 'COLLECTION_NEW', text="New Patch")
        row.operator("helldiver2.archive_export", icon= 'DISC', text="Write Patch")
        row.operator("helldiver2.export_patch", icon= 'EXPORT')
        row.operator("helldiver2.patches_unloadall", icon= 'FILE_REFRESH', text="")

        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "Patches", text="Patches")
        if len(Global_TocManager.Patches) > 0:
            Global_TocManager.SetActivePatchByName(scene.Hd2ToolPanelSettings.Patches)
        row.operator("helldiver2.rename_patch", icon='GREASEPENCIL', text="")
        row.operator("helldiver2.archive_import", icon= 'FILEBROWSER', text="").is_patch = True

        # Draw Archive Contents
        row = layout.row(); row = layout.row()
        title = "No Archive Loaded"
        if Global_TocManager.ActiveArchive != None:
            ArchiveID = Global_TocManager.ActiveArchive.Name
            name = GetArchiveNameFromID(ArchiveID)
            title = f"{name}    ID: {ArchiveID}"
        if Global_TocManager.ActivePatch != None and scene.Hd2ToolPanelSettings.PatchOnly:
            name = Global_TocManager.ActivePatch.Name
            title = f"Patch: {name}    File: {Global_TocManager.ActivePatch.Name}"
        row.prop(scene.Hd2ToolPanelSettings, "ContentsExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.ContentsExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text=title)
        row.prop(scene.Hd2ToolPanelSettings, "PatchOnly", text="")
        row.operator("helldiver2.copy_archive_id", icon='COPY_ID', text="")

        # Get Display Data
        DisplayData = GetDisplayData()
        DisplayTocEntries = DisplayData[0]
        DisplayTocTypes   = DisplayData[1]

        # Draw Contents
        NewFriendlyNames = []
        NewFriendlyIDs = []
        if scene.Hd2ToolPanelSettings.ContentsExpanded:
            if len(DisplayTocEntries) == 0: return

            # Draw Search Bar
            row = layout.row(); row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "SearchField", icon='VIEWZOOM', text="")

            DrawChain = []
            for Type in DisplayTocTypes:
                # check if there is any entry of this type that matches search field
                # TODO: should probably make a better way to do this
                bFound = False
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    if Entry.TypeID == Type.TypeID:
                        searchTerm = str(scene.Hd2ToolPanelSettings.SearchField)
                        if searchTerm.startswith("0x"):
                            searchTerm = str(hex_to_decimal(searchTerm))
                        if str(Entry.FileID).find(searchTerm) != -1:
                            bFound = True
                if not bFound: continue

                # Get Type Icon
                type_icon = 'FILE'
                show = None
                showExtras = scene.Hd2ToolPanelSettings.ShowExtras
                EntryNum = 0
                global Global_Foldouts
                if Type.TypeID == MeshID:
                    type_icon = 'FILE_3D'
                elif Type.TypeID == TexID:
                    type_icon = 'FILE_IMAGE'
                elif Type.TypeID == MaterialID:
                    type_icon = 'MATERIAL' 
                elif Type.TypeID == ParticleID: 
                    type_icon = 'PARTICLES'
                elif showExtras:
                    if Type.TypeID == BoneID: type_icon = 'BONE_DATA'
                    elif Type.TypeID == WwiseBankID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseDepID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseStreamID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseMetaDataID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == AnimationID: type_icon = 'ARMATURE_DATA'
                    elif Type.TypeID == StateMachineID: type_icon = 'DRIVER'
                    elif Type.TypeID == StringID: type_icon = 'WORDWRAP_ON'
                    elif Type.TypeID == PhysicsID: type_icon = 'PHYSICS'
                else:
                    continue
                
                for section in Global_Foldouts:
                    if section[0] == str(Type.TypeID):
                        show = section[1]
                        break
                if show == None:
                    fold = False
                    if Type.TypeID == MaterialID or Type.TypeID == TexID or Type.TypeID == MeshID: fold = True
                    foldout = [str(Type.TypeID), fold]
                    Global_Foldouts.append(foldout)
                    PrettyPrint(f"Adding Foldout ID: {foldout}")
                    

                fold_icon = "DOWNARROW_HLT" if show else "RIGHTARROW"

                # Draw Type Header
                box = layout.box(); row = box.row()
                typeName = GetTypeNameFromID(Type.TypeID)
                split = row.split()
                
                sub = split.row(align=True)
                sub.operator("helldiver2.collapse_section", text=f"{typeName}: {str(Type.TypeID)}", icon=fold_icon, emboss=False).type = str(Type.TypeID)

                # Skip drawling entries if section hidden
                if not show: 
                    sub.label(icon=type_icon)
                    continue
                
                #sub.operator("helldiver2.import_type", icon='IMPORT', text="").object_typeid = str(Type.TypeID)
                sub.operator("helldiver2.select_type", icon='RESTRICT_SELECT_OFF', text="").object_typeid = str(Type.TypeID)
                # Draw Add Material Button
                
                if typeName == "material": sub.operator("helldiver2.material_add", icon='FILE_NEW', text="")

                # Draw Archive Entries
                col = box.column()
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    PatchOnly = EntryInfo[1]
                    # Exclude entries that should not be drawn
                    if Entry.TypeID != Type.TypeID: continue
                    searchTerm = str(scene.Hd2ToolPanelSettings.SearchField)
                    if searchTerm.startswith("0x"):
                        searchTerm = str(hex_to_decimal(searchTerm))
                    if str(Entry.FileID).find(searchTerm) == -1: continue
                    # Deal with friendly names
                    FriendlyName = str(Entry.FileID)
                    if scene.Hd2ToolPanelSettings.FriendlyNames:
                        if len(Global_TocManager.SavedFriendlyNameIDs) > len(DrawChain) and Global_TocManager.SavedFriendlyNameIDs[len(DrawChain)] == Entry.FileID:
                            FriendlyName = Global_TocManager.SavedFriendlyNames[len(DrawChain)]
                        else:
                            try:
                                FriendlyName = Global_TocManager.SavedFriendlyNames[Global_TocManager.SavedFriendlyNameIDs.index(Entry.FileID)]
                                NewFriendlyNames.append(FriendlyName)
                                NewFriendlyIDs.append(Entry.FileID)
                            except:
                                FriendlyName = GetFriendlyNameFromID(Entry.FileID)
                                NewFriendlyNames.append(FriendlyName)
                                NewFriendlyIDs.append(Entry.FileID)


                    # Draw Entry
                    PatchEntry = Global_TocManager.GetEntry(int(Entry.FileID), int(Entry.TypeID))
                    PatchEntry.DEV_DrawIndex = len(DrawChain)
                    
                    previous_type_icon = type_icon
                    if PatchEntry.MaterialTemplate != None:
                        type_icon = "NODE_MATERIAL"

                    row = col.row(align=True); row.separator()
                    props = row.operator("helldiver2.archive_entry", icon=type_icon, text=FriendlyName, emboss=PatchEntry.IsSelected, depress=PatchEntry.IsSelected)
                    type_icon = previous_type_icon
                    props.object_id     = str(Entry.FileID)
                    props.object_typeid = str(Entry.TypeID)
                    # Draw Entry Buttons
                    self.draw_entry_buttons(col, row, PatchEntry, PatchOnly)
                    # Update Draw Chain
                    DrawChain.append(PatchEntry)
            Global_TocManager.DrawChain = DrawChain
        if scene.Hd2ToolPanelSettings.FriendlyNames:  
            Global_TocManager.SavedFriendlyNames = NewFriendlyNames
            Global_TocManager.SavedFriendlyNameIDs = NewFriendlyIDs

class WM_MT_button_context(Menu):
    bl_label = "Entry Context Menu"

    def draw_entry_buttons(self, row, Entry):
        if not Entry.IsSelected:
            Global_TocManager.SelectEntries([Entry])

        # Combine entry strings to be passed to operators
        FileIDStr = ""
        TypeIDStr = ""
        for SelectedEntry in Global_TocManager.SelectedEntries:
            FileIDStr += str(SelectedEntry.FileID)+","
            TypeIDStr += str(SelectedEntry.TypeID)+","
        # Get common class
        AreAllMeshes    = True
        AreAllTextures  = True
        AreAllMaterials = True
        AreAllParticles = True
        SingleEntry = True
        NumSelected = len(Global_TocManager.SelectedEntries)
        if len(Global_TocManager.SelectedEntries) > 1:
            SingleEntry = False
        for SelectedEntry in Global_TocManager.SelectedEntries:
            if SelectedEntry.TypeID == MeshID:
                AreAllTextures = False
                AreAllMaterials = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == TexID:
                AreAllMeshes = False
                AreAllMaterials = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == MaterialID:
                AreAllTextures = False
                AreAllMeshes = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == ParticleID:
                AreAllTextures = False
                AreAllMeshes = False
                AreAllMaterials = False
            else:
                AreAllMeshes = False
                AreAllTextures = False
                AreAllMaterials = False
                AreAllParticles = False
        
        RemoveFromPatchName = "Remove From Patch" if SingleEntry else f"Remove {NumSelected} From Patch"
        AddToPatchName = "Add To Patch" if SingleEntry else f"Add {NumSelected} To Patch"
        ImportMeshName = "Import Mesh" if SingleEntry else f"Import {NumSelected} Meshes"
        ImportTextureName = "Import Texture" if SingleEntry else f"Import {NumSelected} Textures"
        ImportMaterialName = "Import Material" if SingleEntry else f"Import {NumSelected} Materials"
        ImportParticleName = "Import Particle" if SingleEntry else f"Import {NumSelected} Particles"
        DumpObjectName = "Export Object Dump" if SingleEntry else f"Export {NumSelected} Object Dumps"
        ImportDumpObjectName = "Import Object Dump" if SingleEntry else f"Import {NumSelected} Object Dumps"
        SaveTextureName = "Save Blender Texture" if SingleEntry else f"Save Blender {NumSelected} Textures"
        SaveMaterialName = "Save Material" if SingleEntry else f"Save {NumSelected} Materials"
        SaveParticleName = "Save Particle" if SingleEntry else f"Save {NumSelected} Particles"
        UndoName = "Undo Modifications" if SingleEntry else f"Undo {NumSelected} Modifications"
        CopyName = "Copy Entry" if SingleEntry else f"Copy {NumSelected} Entries"
        
        # Draw seperator
        row.separator()
        row.label(text=Global_SectionHeader)

        # Draw copy button
        row.separator()
        props = row.operator("helldiver2.archive_copy", icon='COPYDOWN', text=CopyName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        if len(Global_TocManager.CopyBuffer) != 0:
            row.operator("helldiver2.archive_paste", icon='PASTEDOWN', text="Paste "+str(len(Global_TocManager.CopyBuffer))+" Entries")
            row.operator("helldiver2.archive_clearclipboard", icon='TRASH', text="Clear Clipboard")
        if SingleEntry:
            props = row.operator("helldiver2.archive_duplicate", icon='DUPLICATE', text="Duplicate Entry")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text=RemoveFromPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='PLUS', text=AddToPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        # Draw import buttons
        # TODO: Add generic import buttons
        row.separator()
        if AreAllMeshes:
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text=ImportMeshName).object_id = FileIDStr
        elif AreAllTextures:
            row.operator("helldiver2.texture_import", icon='IMPORT', text=ImportTextureName).object_id = FileIDStr
        elif AreAllMaterials:
            row.operator("helldiver2.material_import", icon='IMPORT', text=ImportMaterialName).object_id = FileIDStr
        elif AreAllParticles:
            row.operator("helldiver2.archive_particle_import", icon='IMPORT', text=ImportParticleName).object_id = FileIDStr
        # Draw export buttons
        row.separator()
        if SingleEntry:
            props = row.operator("helldiver2.archive_object_dump_import", icon='PACKAGE', text=ImportDumpObjectName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr
        props = row.operator("helldiver2.archive_object_dump_export", icon='PACKAGE', text=DumpObjectName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        # Draw dump import button
        # if AreAllMaterials and SingleEntry: row.operator("helldiver2.archive_object_dump_import", icon="IMPORT", text="Import Raw Dump").object_id = FileIDStr
        # Draw save buttons
        row.separator()
        if AreAllMeshes:
            if SingleEntry:
                row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="Save Mesh").object_id = str(Entry.FileID)
            else:
              row.operator("helldiver2.archive_mesh_batchsave", icon='FILE_BLEND', text=f"Save {NumSelected} Meshes")
        elif AreAllTextures:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text=SaveTextureName).object_id = FileIDStr
            if SingleEntry:
                row.separator()
                row.operator("helldiver2.texture_savefromdds", icon='FILE_IMAGE', text="Import DDS Texture").object_id = str(Entry.FileID)
                row.operator("helldiver2.texture_savefrompng", icon='FILE_IMAGE', text="Import PNG Texture").object_id = str(Entry.FileID)
                row.separator()
                row.operator("helldiver2.texture_export", icon='OUTLINER_OB_IMAGE', text="Export DDS Texture").object_id = str(Entry.FileID)
                row.operator("helldiver2.texture_export_png", icon='OUTLINER_OB_IMAGE', text="Export PNG Texture").object_id = str(Entry.FileID)
            else:
                row.separator()
                row.operator("helldiver2.texture_batchexport", icon='OUTLINER_OB_IMAGE', text=f"Export {NumSelected} DDS Textures").object_id = FileIDStr
                row.operator("helldiver2.texture_batchexport_png", icon='OUTLINER_OB_IMAGE', text=f"Export {NumSelected} PNG Textures").object_id = FileIDStr
        elif AreAllMaterials:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text=SaveMaterialName).object_id = FileIDStr
            if SingleEntry:
                row.operator("helldiver2.material_set_template", icon='MATSHADERBALL').entry_id = str(Entry.FileID)
                if Entry.LoadedData != None:
                    row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Parent Material Entry ID").text = str(Entry.LoadedData.ParentMaterialID)
        elif AreAllParticles:
            row.operator("helldiver2.particle_save", icon='FILE_BLEND', text=SaveParticleName).object_id = FileIDStr
        # Draw copy ID buttons
        if SingleEntry:
            row.separator()
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry ID").text = str(Entry.FileID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry Hex ID").text = str(hex(Entry.FileID))
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Type ID").text  = str(Entry.TypeID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Friendly Name").text  = GetFriendlyNameFromID(Entry.FileID)
            if Global_TocManager.IsInPatch(Entry):
                props = row.operator("helldiver2.archive_entryrename", icon='TEXT', text="Rename")
                props.object_id     = str(Entry.FileID)
                props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            row.separator()
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text=UndoName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        if SingleEntry:
            row.operator("helldiver2.archive_setfriendlyname", icon='WORDWRAP_ON', text="Set Friendly Name").object_id = str(Entry.FileID)
            
    def draw_material_editor_context_buttons(self, layout, FileID):
        row = layout
        row.separator()
        row.label(text=Global_SectionHeader)
        row.separator()
        row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry ID").text = str(FileID)
        row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry Hex ID").text = str(hex(int(FileID)))
    
    def draw(self, context):
        value = getattr(context, "button_operator", None)
        menuName = type(value).__name__
        if menuName == "HELLDIVER2_OT_archive_entry":
            layout = self.layout
            FileID = getattr(value, "object_id")
            TypeID = getattr(value, "object_typeid")
            self.draw_entry_buttons(layout, Global_TocManager.GetEntry(int(FileID), int(TypeID)))
        elif menuName == "HELLDIVER2_OT_material_texture_entry":
            layout = self.layout
            FileID = getattr(value, "object_id")
            self.draw_material_editor_context_buttons(layout, FileID)
            

#endregion

classes = (
    LoadArchiveOperator,
    PatchArchiveOperator,
    ImportStingrayMeshOperator,
    SaveStingrayMeshOperator,
    ImportMaterialOperator,
    ImportTextureOperator,
    ExportTextureOperator,
    DumpArchiveObjectOperator,
    ImportDumpOperator,
    Hd2ToolPanelSettings,
    HellDivers2ToolsPanel,
    UndoArchiveEntryModOperator,
    AddMaterialOperator,
    SaveMaterialOperator,
    SaveTextureFromBlendImageOperator,
    ShowMaterialEditorOperator,
    SetMaterialTexture,
    SearchArchivesOperator,
    LoadArchivesOperator,
    CopyArchiveEntryOperator,
    PasteArchiveEntryOperator,
    ClearClipboardOperator,
    SaveTextureFromDDSOperator,
    HelpOperator,
    ArchiveSpreadsheetOperator,
    UnloadArchivesOperator,
    ArchiveEntryOperator,
    CreatePatchFromActiveOperator,
    AddEntryToPatchOperator,
    RemoveEntryFromPatchOperator,
    CopyTextOperator,
    BatchExportTextureOperator,
    BatchSaveStingrayMeshOperator,
    SelectAllOfTypeOperator,
    RenamePatchEntryOperator,
    DuplicateEntryOperator,
    SetEntryFriendlyNameOperator,
    DefaultLoadArchiveOperator,
    BulkLoadOperator,
    ImportAllOfTypeOperator,
    UnloadPatchesOperator,
    GithubOperator,
    ChangeFilepathOperator,
    CopyCustomPropertyOperator,
    PasteCustomPropertyOperator,
    CopyArchiveIDOperator,
    ExportPatchAsZipOperator,
    RenamePatchOperator,
    NextArchiveOperator,
    MaterialTextureEntryOperator,
    EntrySectionOperator,
    SaveTextureFromPNGOperator,
    SearchByEntryIDOperator,
    ChangeSearchpathOperator,
    ExportTexturePNGOperator,
    BatchExportTexturePNGOperator,
    CopyDecimalIDOperator,
    CopyHexIDOperator,
    GenerateEntryIDOperator,
    SetMaterialTemplateOperator,
    LatestReleaseOperator,
    MaterialShaderVariableEntryOperator,
    MaterialShaderVariableColorEntryOperator,
    MeshFixOperator,
    ImportStingrayParticleOperator,
    SaveStingrayParticleOperator,
)

Global_TocManager = TocManager()

def register():
    if Global_CPPHelper == None: raise Exception("HDTool_Helper is required by the addon but failed to load!")
    if not os.path.exists(Global_texconvpath): raise Exception("Texconv is not found, please install Texconv in /deps/")
    CheckBlenderVersion()
    CheckAddonUpToDate()
    InitializeConfig()
    LoadNormalPalette(Global_palettepath)
    UpdateArchiveHashes()
    LoadTypeHashes()
    LoadNameHashes()
    LoadArchiveHashes()
    LoadShaderVariables()
    LoadBoneHashes()
    for cls in classes:
        bpy.utils.register_class(cls)
    Scene.Hd2ToolPanelSettings = PointerProperty(type=Hd2ToolPanelSettings)
    bpy.utils.register_class(WM_MT_button_context)
    bpy.types.VIEW3D_MT_object_context_menu.append(CustomPropertyContext)

def unregister():
    global Global_CPPHelper
    bpy.utils.unregister_class(WM_MT_button_context)
    del Scene.Hd2ToolPanelSettings
    del Global_CPPHelper
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.remove(CustomPropertyContext)


if __name__=="__main__":
    register()
