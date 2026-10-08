import os
import struct

from ..utils.logger import PrettyPrint
from ..utils.memoryStream import MemoryStream

Global_ShaderVariables = {}
Global_TextureTypes = {}

class StingrayMaterial:
    def __init__(self):
        self.undat1 = self.undat3 = self.undat4 = self.undat5 = self.undat6 = self.RemainingData = bytearray()
        self.EndOffset = self.undat2 = self.ParentMaterialID = self.NumTextures = self.NumVariables = self.VariableDataSize = 0
        self.TextureTypes = []
        self.TexIDs  = []
        self.ShaderVariables = []

        self.DEV_ShowEditor = False
        self.DEV_DDSPaths = []
        self.DEV_FileID = 0

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
            self.TextureTypes = [TextureType() for n in range(self.NumTextures)]
            self.TexIDs = [0 for n in range(self.NumTextures)]
            self.ShaderVariables = [ShaderVariable() for n in range(self.NumVariables)]
        for textureType in self.TextureTypes:
            textureType.ID = f.uint32(textureType.ID)
            if textureType.ID in Global_TextureTypes:
                textureType.name = Global_TextureTypes[textureType.ID]
            else: textureType.name = hex(textureType.ID)
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

    def set_encoded_data(self, data: str):
        parts = data.split()
        found_ID = int(parts[0], 16)

        for variable in self.ShaderVariables:
            if variable.ID == found_ID:
                variable.values = [hex_to_float(part) for part in parts[1:]]
                PrettyPrint(f"Set encoded data for variable {variable.name} (ID: {variable.ID}) to: {variable.values}")
                break
        else:
            PrettyPrint(f"Shader Variable ID {found_ID} not found in material. \n\n {[(variable.name, variable.ID) for variable in self.ShaderVariables]}", "ERROR")

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

    def get_encoded_data(self) -> str:
        data = f"{self.ID:08X}"
        for value in self.values:
            hex_value = float_to_hex(value)
            data += f" {hex_value}"
        return data

class TextureType:
    def __init__(self):
        self.ID = 0
        self.name = ""

def LoadShaderVariables(path):
    global Global_ShaderVariables
    file = open(path, "r")
    text = file.read()
    for line in text.splitlines():
        Global_ShaderVariables[int(line.split()[1], 16)] = line.split()[0]

def LoadTextureTypes(path):
    global Global_TextureTypes
    file = open(path, "r")
    text = file.read()
    for line in text.splitlines():
        Global_TextureTypes[int(line.split()[1], 16)] = line.split()[0]

def float_to_hex(float_value) -> str:
    return f"{struct.unpack('>I', struct.pack('>f', float_value))[0]:08X}"

def hex_to_float(hex_value: str):
    return struct.unpack('>f', struct.pack('>I', int(hex_value, 16)))[0]
