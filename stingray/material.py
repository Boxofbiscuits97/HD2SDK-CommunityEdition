from copy import deepcopy
import os
import tempfile
import bpy
import random as r

from memoryStream import MemoryStream
from operators.texture import SaveImageDDS, SaveImagePNG
from stingray.archives.tocentry import TocEntry
from __init__ import Global_ShaderVariables, Global_TocManager, MaterialID, PrettyPrint, TexID
from stingray.hashing import RandomHash16
from stingray.texture import StingrayTexture


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
        "armorlut": (
        "Decal", 
        "", 
        "Pattern LUT", 
        "Normal", 
        "", 
        "", 
        "Pattern Mask", 
        "ID Mask Array", 
        "", 
        "Primary LUT", 
        "",
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
        ("basic+", "Basic+", "A basic material with a color, normal, and PBR map which renders in the UI, Sourced from a SEAF NPC"),
        ("translucent", "Translucent", "A translucent with a solid set color and normal map. Sourced from the Terminid Larva Backpack."),
        ("alphaclip", "Alpha Clip", "A material that supports an alpha mask which does not render in the UI. Sourced from a skeleton pile"),
        ("original", "Original", "The original template used for all mods uploaded to Nexus prior to the addon's public release, which is bloated with additional unnecessary textures. Sourced from a terminid"),
        ("basic", "Basic", "A basic material with a color, normal, and PBR map. Sourced from a trash bag prop"),
        ("emissive", "Emissive", "A basic material with a color, normal, and emission map. Sourced from a vending machine"),
        ("armorlut", "Armor LUT", "An advanced material using multiple mask textures and LUTs to texture the mesh only advanced users should be using this. Sourced from the base game material on Armors"),
    )


Global_MaterialParentIDs = {
    3430705909399566334 : "basic+",
    15586118709890920288 : "alphaclip",
    6101987038150196875 : "original",
    15356477064658408677 : "basic",
    15235712479575174153 : "emissive",
    17265463703140804126 : "advanced",
    17720495965476876300 : "armorlut",
    9576304397847579354  : "translucent",
    8580182439406660688 : "basic+"
}


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
                if image.packed_file:
                    raise Exception(f"Image: {image.name} is packed. Please unpack your image.")
                path = bpy.path.abspath(image.filepath)
                PrettyPrint(f"Getting image path at: {path}")
                ID = image.name.split(".")[0]
                if not os.path.exists(path) and ID.isnumeric():
                    PrettyPrint(f"Image not found. Attempting to find image: {ID} in temp folder.", 'WARN')
                    tempdir = tempfile.gettempdir()
                    path = f"{tempdir}\\{ID}.png"
                filepaths.append(path)

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
