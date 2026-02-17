from math import ceil, sqrt
import math

import mathutils
import bpy
import random
import bmesh

from ..utils.memoryStream import MemoryStream, MakeTenBitUnsigned, TenBitUnsigned
from ..utils.logger import PrettyPrint
from ..utils.hashing import murmur32_hash

from ..utils.constants import *

Global_MaterialSlotNames = {}

class StingrayMeshFile:
    def __init__(self):
        self.HeaderData1        = bytearray(28);  self.HeaderData2        = bytearray(20); self.UnReversedData1  = bytearray(); self.UnReversedData2    = bytearray()
        self.StreamInfoOffset   = self.EndingOffset = self.MeshInfoOffset = self.NumStreams = self.NumMeshes = self.EndingBytes = self.StreamInfoUnk2 = self.HeaderUnk = self.MaterialsOffset = self.NumMaterials = self.NumBoneInfo = self.BoneInfoOffset = 0
        self.StreamInfoOffsets  = self.StreamInfoUnk = self.StreamInfoArray = self.MeshInfoOffsets = self.MeshInfoUnk = self.MeshInfoArray = []
        self.CustomizationInfoOffset = self.UnkHeaderOffset1 = self.ConnectingBoneHashOffset = self.TransformInfoOffset = self.UnkRef1 = self.BonesRef = self.CompositeRef = 0
        self.BoneInfoOffsets = self.BoneInfoArray = []
        self.RawMeshes = []
        self.SectionsIDs = []
        self.MaterialIDs = []
        self.LightList = LightList()
        self.DEV_MeshInfoMap = [] # Allows removing of meshes while mapping them to the original meshes
        self.CustomizationInfo = CustomizationInfo()
        self.TransformInfo     = TransformInfo()
        self.BoneNames = None
        self.UnreversedCustomizationData = bytearray()
        self.UnreversedConnectingBoneData = bytearray()
        self.UnreversedLODGroupListData = bytearray()
        self.UnreversedWwiseCallbackData = bytearray()
        self.UnreversedPreLightListData = bytearray()
        self.UnreversedLODGroupListDataOffset = 0
        self.UnkHeaderData1 = bytearray()
        self.StateMachineRef = self.UnkRef2 = self.LodGroupOffset = 0
        self.NameHash = 0
        self.LightListOffset = 0
        self.UnkPreLightListOffset = 0
        self.WwiseCallbackOffset = 0
        self.LoadMaterialSlotNames = True

    # -- Serialize Mesh -- #
    def Serialize(self, f: MemoryStream, gpu, Global_TocManager, redo_offsets = False, BlenderOpts=None):
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
                Mesh_info.NumSections = 0
                Mesh_info.NumMaterials = 0
                for Material in Raw_Mesh.Materials:
                    Section = MeshSectionInfo()
                    Section.ID          = int(Material.ShortID)
                    Section.NumIndices  = Material.NumIndices
                    Section.VertexOffset  = Order # | Used for ordering function
                    Section.IndexOffset   = Order # /

                    # This doesnt do what it was intended to do
                    if Material.DEV_BoneInfoOverride != None:
                        PrettyPrint("Overriding unknown material values")
                        Section.MaterialIndex = Material.DEV_BoneInfoOverride
                        Section.GroupIndex = Material.DEV_BoneInfoOverride
                    else:
                        Section.MaterialIndex = len(Mesh_info.Sections) # | dont know what these actually are, but this is usually correct it seems
                        Section.GroupIndex = len(Mesh_info.Sections) # /

                    Mesh_info.Sections.append(Section)
                    Mesh_info.NumSections += 1
                    Mesh_info.NumMaterials += 1
                    Order -= 1
                    try: # if material ID uses the defualt material string it will throw an error, but thats fine as we dont want to include those ones anyway
                        #if int(Material.MatID) not in self.MaterialIDs:
                        self.MaterialIDs.append(int(Material.MatID))
                        self.SectionsIDs.append(int(Material.ShortID)) # MATERIAL SLOT NAME
                    except:
                        pass

        # serialize file
        self.UnkRef1            = f.uint64(self.UnkRef1)
        self.BonesRef           = f.uint64(self.BonesRef)
        if f.IsWriting():         f.uint64(0)
        else: self.CompositeRef = f.uint64(self.CompositeRef)
        self.UnkRef2            = f.uint64(self.UnkRef2)
        self.StateMachineRef    = f.uint64(self.StateMachineRef)
        self.HeaderData1        = f.uint64(self.HeaderData1)
        self.UnreversedLODGroupListDataOffset = f.uint32(self.UnreversedLODGroupListDataOffset)
        self.TransformInfoOffset= f.uint32(self.TransformInfoOffset)
        self.LightListOffset    = f.uint32(self.LightListOffset)
        self.UnkPreLightListOffset = f.uint32(self.UnkPreLightListOffset)
        self.WwiseCallbackOffset= f.uint32(self.WwiseCallbackOffset)
        self.HeaderData2        = f.bytes(self.HeaderData2, 8)
        self.CustomizationInfoOffset  = f.uint32(self.CustomizationInfoOffset)
        self.UnkHeaderOffset1   = f.uint32(self.UnkHeaderOffset1)
        self.ConnectingBoneHashOffset   = f.uint32(self.ConnectingBoneHashOffset)
        self.BoneInfoOffset     = f.uint32(self.BoneInfoOffset)
        self.StreamInfoOffset   = f.uint32(self.StreamInfoOffset)
        self.EndingOffset       = f.uint32(self.EndingOffset)
        self.MeshInfoOffset     = f.uint32(self.MeshInfoOffset)
        self.HeaderUnk          = f.uint64(self.HeaderUnk)
        self.MaterialsOffset    = f.uint32(self.MaterialsOffset)
        
        f.seek(f.tell() + 12)

        if f.IsReading() and self.MeshInfoOffset == 0:
            raise Exception("Unsupported Mesh Format (No geometry)")

        if f.IsReading() and (self.StreamInfoOffset == 0 and self.CompositeRef == 0):
            raise Exception("Unsupported Mesh Format (No buffer stream)")

        # Get bones file
        if f.IsReading() and self.BonesRef != 0:
            Entry = Global_TocManager.GetEntry(self.BonesRef, BoneID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                self.BoneNames = Entry.LoadedData.Names
                self.BoneHashes = Entry.LoadedData.BoneHashes

        # Get Customization data: READ ONLY
        if f.IsReading() and self.CustomizationInfoOffset > 0:
            loc = f.tell(); f.seek(self.CustomizationInfoOffset)
            self.CustomizationInfo.Serialize(f)
            f.seek(loc)
            
        # Wwise Callback Data
        if self.WwiseCallbackOffset > 0:
            if f.IsReading():
                f.seek(self.WwiseCallbackOffset)
                if self.UnkPreLightListOffset > 0:
                    data_size = self.UnkPreLightListOffset - f.tell()
                elif self.LightListOffset > 0:
                    data_size = self.LightListOffset - f.tell()
            else:
                data_size = len(self.UnreversedWwiseCallbackData)
                self.WwiseCallbackOffset = f.tell()
            self.UnreversedWwiseCallbackData = f.bytes(self.UnreversedWwiseCallbackData, data_size)
        
        # Pre light list data
        if self.UnkPreLightListOffset > 0:
            if f.IsReading():
                f.seek(self.UnkPreLightListOffset)
                data_size = self.LightListOffset - self.UnkPreLightListOffset
            else:
                data_size = len(self.UnreversedPreLightListData)
                self.UnkPreLightListOffset = f.tell()
            self.UnreversedPreLightListData = f.bytes(self.UnreversedPreLightListData, data_size)
        
        # Get Light data
        if f.IsReading():
            f.seek(self.LightListOffset)
        else:
            self.LightListOffset = f.tell()
        self.LightList.Serialize(f)
        
        print(len(self.LightList.lights))
        
        # Get Unreversed data before transform info (LOD Group List)
        if f.IsReading():
            if self.TransformInfoOffset > 0:
                UnreversedLODGroupListDataSize = self.TransformInfoOffset - f.tell()
            elif self.CustomizationInfoOffset > 0:
                UnreversedLODGroupListDataSize = self.CustomizationInfoOffset - f.tell()
            elif self.UnkHeaderOffset1 > 0:
                UnreversedLODGroupListDataSize = self.UnkHeaderOffset1 - f.tell()
            elif self.ConnectingBoneHashOffset > 0:
                UnreversedLODGroupListDataSize = self.ConnectingBoneHashOffset - f.tell()
            elif self.BoneInfoOffset > 0:
                UnreversedLODGroupListDataSize = self.BoneInfoOffset-f.tell()
            elif self.StreamInfoOffset > 0:
                UnreversedLODGroupListDataSize = self.StreamInfoOffset-f.tell()
            elif self.MeshInfoOffset > 0:
                UnreversedLODGroupListDataSize = self.MeshInfoOffset-f.tell()
        else:
            UnreversedLODGroupListDataSize = len(self.UnreversedLODGroupListData)
            self.UnreversedLODGroupListDataOffset = f.tell()
        try:
            self.UnreversedLODGroupListData    = f.bytes(self.UnreversedLODGroupListData, UnreversedLODGroupListDataSize)
        except:
            PrettyPrint(f"Could not set UnreversedLODGroupListData", "ERROR")
        
        # Get Transform data
        if self.TransformInfoOffset > 0:
            if f.IsReading():
                pass
            else:
                self.TransformInfoOffset = f.tell()
            self.TransformInfo.Serialize(f)
            if f.tell() % 16 != 0:
                f.seek(f.tell() + (16-f.tell()%16))
        
        # Get Customization Info
        UnreversedCustomizationData_Size = 0
        if self.CustomizationInfoOffset > 0:
            if f.IsReading():
                f.seek(self.CustomizationInfoOffset)
            else:
                self.CustomizationInfoOffset = f.tell()
            if f.IsReading():
                if self.UnkHeaderOffset1 > 0:
                    UnreversedCustomizationData_Size = self.UnkHeaderOffset1 - f.tell()
                elif self.ConnectingBoneHashOffset > 0:
                    UnreversedCustomizationData_Size = self.ConnectingBoneHashOffset - f.tell()
                elif self.BoneInfoOffset > 0:
                    UnreversedCustomizationData_Size = self.BoneInfoOffset-f.tell()
                elif self.StreamInfoOffset > 0:
                    UnreversedCustomizationData_Size = self.StreamInfoOffset-f.tell()
                elif self.MeshInfoOffset > 0:
                    UnreversedCustomizationData_Size = self.MeshInfoOffset-f.tell()
            else:
                UnreversedCustomizationData_Size = len(self.UnreversedCustomizationData)
            if UnreversedCustomizationData_Size > 0:
                self.UnreversedCustomizationData = f.bytes(self.UnreversedCustomizationData, UnreversedCustomizationData_Size)
                
        # Get Unknown data
        # If there is no transform info, this data is already contained in UnreversedLODGroupListData
        if self.UnkHeaderOffset1 > 0:
            data_size = 0
            if f.IsReading():
                f.seek(self.UnkHeaderOffset1)
            else:
                self.UnkHeaderOffset1 = f.tell()
            if f.IsReading():
                if self.ConnectingBoneHashOffset > 0:
                    data_size = self.ConnectingBoneHashOffset - f.tell()
                elif self.BoneInfoOffset > 0:
                    data_size = self.BoneInfoOffset-f.tell()
                elif self.StreamInfoOffset > 0:
                    data_size = self.StreamInfoOffset-f.tell()
                elif self.MeshInfoOffset > 0:
                    data_size = self.MeshInfoOffset-f.tell()
            else:
                data_size = len(self.UnkHeaderData1)
            if data_size > 0:
                self.UnkHeaderData1 = f.bytes(self.UnkHeaderData1, data_size)
            
                
        # ConnectingBoneHash Data
        if self.ConnectingBoneHashOffset > 0:
            if self.BoneInfoOffset > 0:
                UnreversedConnectingBoneDataSize = self.BoneInfoOffset-f.tell()
            elif self.StreamInfoOffset > 0:
                UnreversedConnectingBoneDataSize = self.StreamInfoOffset-f.tell()
            elif self.MeshInfoOffset > 0:
                UnreversedConnectingBoneDataSize = self.MeshInfoOffset-f.tell()
            if f.IsReading():
                f.seek(self.ConnectingBoneHashOffset)
            else:
                self.ConnectingBoneHashOffset = f.tell()
                UnreversedConnectingBoneDataSize = len(self.UnreversedConnectingBoneData)
            self.UnreversedConnectingBoneData = f.bytes(self.UnreversedConnectingBoneData, UnreversedConnectingBoneDataSize)

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
            
        # Get geometry group
        if f.IsReading() and self.CompositeRef != 0:
            Entry = Global_TocManager.GetEntry(self.CompositeRef, CompositeUnitID)
            if Entry != None:
                Global_TocManager.Load(Entry.FileID, Entry.TypeID)
                geometry_group = Entry.LoadedData
                unit_index = geometry_group.UnitHashes.index(int(self.NameHash))
                c_mesh_info = geometry_group.MeshInfos[unit_index]
                self.StreamInfoArray = Entry.LoadedData.StreamInfoArray
                self.NumStreams = len(self.StreamInfoArray)
                for i, mesh_info_item in enumerate(self.MeshInfoArray):
                    mesh_index = c_mesh_info.Meshes.index(mesh_info_item.MeshID)
                    c_mesh_info_item = c_mesh_info.MeshInfoItems[mesh_index]
                    mesh_info_item.StreamIndex      = c_mesh_info_item.MeshLayoutIdx
                    mesh_info_item.NumMaterials     = c_mesh_info_item.NumMaterials
                    mesh_info_item.MaterialOffset   = c_mesh_info_item.MaterialsOffset + 0x50
                    mesh_info_item.Sections         = c_mesh_info_item.Groups
                    mesh_info_item.MaterialIDs      = c_mesh_info_item.Materials
                    mesh_info_item.SectionsOffset   = c_mesh_info_item.GroupsOffset + 0x50
                    mesh_info_item.NumSections      = c_mesh_info_item.NumGroups
                self.StreamInfoOffset = 1
                gpu = Entry.LoadedData.GpuData
            else:
                raise Exception(f"Composite mesh file {self.CompositeRef} could not be found")

        # Materials
        if f.IsReading(): f.seek(self.MaterialsOffset)
        else            : self.MaterialsOffset = f.tell()
        self.NumMaterials = f.uint32(len(self.MaterialIDs))
        if f.IsReading():
            self.SectionsIDs = [0]*self.NumMaterials
            self.MaterialIDs = [0]*self.NumMaterials
        self.SectionsIDs = [f.uint32(ID) for ID in self.SectionsIDs]
        self.MaterialIDs = [f.uint64(ID) for ID in self.MaterialIDs]
        if f.IsReading() and self.LoadMaterialSlotNames:
            global Global_MaterialSlotNames
            id = str(self.NameHash)
            if id not in Global_MaterialSlotNames:
                Global_MaterialSlotNames[id] = {}
            for i in range(self.NumMaterials):
                if self.MaterialIDs[i] not in Global_MaterialSlotNames[id]: # probably going to have to save material slot names per LOD/mesh
                    Global_MaterialSlotNames[id][self.MaterialIDs[i]] = []
                PrettyPrint(f"Saving material slot name {self.SectionsIDs[i]} for material {self.MaterialIDs[i]}")
                if self.SectionsIDs[i] not in Global_MaterialSlotNames[id][self.MaterialIDs[i]]:
                    Global_MaterialSlotNames[id][self.MaterialIDs[i]].append(self.SectionsIDs[i])

        # Unreversed Data
        if f.IsReading(): UnreversedData2Size = self.EndingOffset-f.tell()
        else: UnreversedData2Size = len(self.UnReversedData2)
        self.UnReversedData2    = f.bytes(self.UnReversedData2, UnreversedData2Size)
        if f.IsWriting(): self.EndingOffset = f.tell()
        self.EndingBytes        = f.uint64(self.NumMeshes)
        if redo_offsets:
            return self

        # Serialize Data
        self.SerializeGpuData(gpu, Global_TocManager, BlenderOpts)

        # TODO: update offsets only instead of re-writing entire file
        if f.IsWriting() and not redo_offsets:
            f.seek(0)
            self.Serialize(f, gpu, Global_TocManager, True)
        return self

    def SerializeGpuData(self, gpu: MemoryStream, Global_TocManager, BlenderOpts=None):
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
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager)
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
            else:
                self.SerializeVertexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes)
                self.SerializeIndexBuffer(gpu, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager)

    def SerializeIndexBuffer(self, gpu: MemoryStream, Stream_Info, stream_idx, OrderedMeshes, Global_TocManager):
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
            mat_count = {}
            for Section in Mesh_Info.Sections:
                # Create mat info
                if gpu.IsReading():
                    mat = RawMaterialClass()
                    if Section.ID in self.SectionsIDs:
                        mat_idx = self.SectionsIDs.index(Section.ID)
                        mat.MatID = str(self.MaterialIDs[mat_idx])
                        if mat.MatID not in mat_count:
                            mat_count[mat.MatID] = -1
                        mat_count[mat.MatID] += 1
                        mat.IDFromName(str(self.NameHash), str(self.MaterialIDs[mat_idx]), mat_count[mat.MatID])
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
                if gpu.IsReading():
                    pass
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
            group_transform = self.TransformInfo.TransformMatrices[Mesh_Info.TransformIndex]
            NewMesh.DEV_Transform = group_transform.ToBlenderMatrix()
            
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
            HasColors    = False
            NumUVs       = 0
            NumBoneIndices = 0
            # get total number of components
            for mesh in OrderedMeshes[stream_idx][0]:
                if len(mesh.VertexPositions)  > 0: HasPositions  = True
                if len(mesh.VertexColors)     > 0: HasColors     = True
                if len(mesh.VertexNormals)    > 0: HasNormals    = True
                if len(mesh.VertexTangents)   > 0: HasTangents   = True
                if len(mesh.VertexBiTangents) > 0: HasBiTangents = True
                if len(mesh.VertexBoneIndices)> 0: IsSkinned     = True
                if len(mesh.VertexUVs)   > NumUVs: NumUVs = len(mesh.VertexUVs)
                if len(mesh.VertexBoneIndices) > NumBoneIndices: NumBoneIndices = len(mesh.VertexBoneIndices)
            if BlenderOpts:    
                if BlenderOpts.get("Force3UVs"):
                    NumUVs = max(3, NumUVs)
                if IsSkinned and NumBoneIndices > 1 and BlenderOpts.get("Force1Group"):
                    NumBoneIndices = 1
            for mesh in OrderedMeshes[stream_idx][0]: # fill default values for meshes which are missing some components
                if not len(mesh.VertexPositions)  > 0:
                    raise Exception("bruh... your mesh doesn't have any vertices")
                if HasNormals and not len(mesh.VertexNormals)    > 0:
                    mesh.VertexNormals = [[0,0,0] for n in mesh.VertexPositions]
                if HasColors and not len(mesh.VertexColors) > 0:
                    mesh.VertexColors = [[0, 0, 0, 0] for n in mesh.VertexColors]
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
            if HasColors:     Stream_Info.Components.append(StreamComponentInfo("color", "rgba_r8g8b8a8"))
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
            

class BoneInfo:
    def __init__(self):
        self.NumBones = self.unk1 = self.RealIndicesOffset = self.FakeIndicesOffset = self.NumFakeIndices = self.FakeIndicesUnk = 0
        self.Bones = self.RealIndices = self.FakeIndices = []
        self.NumRemaps = self.MatrixOffset = 0
        self.Remaps = self.RemapOffsets = self.RemapCounts = []
    def Serialize(self, f: MemoryStream, end=None):
        self.Serialize_REAL(f)
        return self

    def Serialize_REAL(self, f: MemoryStream): # still need to figure out whats up with the unknown bit
        RelPosition = f.tell()
        
        self.NumBones       = f.uint32(self.NumBones)
        self.MatrixOffset           = f.uint32(self.MatrixOffset) # matrix pointer
        self.RealIndicesOffset = f.uint32(self.RealIndicesOffset) # unit indices
        self.FakeIndicesOffset = f.uint32(self.FakeIndicesOffset) # remap indices
        # get bone data
        if f.IsReading():
            self.Bones = [StingrayMatrix4x4() for n in range(self.NumBones)]
            self.RealIndices = [0 for n in range(self.NumBones)]
            self.FakeIndices = [0 for n in range(self.NumBones)]
        if f.IsReading(): f.seek(RelPosition+self.MatrixOffset)
        else            : self.MatrixOffset = f.tell()-RelPosition
        # save the right bone
        for i, bone in enumerate(self.Bones):
            if i == self.NumBones:
                break
            bone.Serialize(f)
        #self.Bones = [bone.Serialize(f) for bone in self.Bones]
        # get real indices
        if f.IsReading(): f.seek(RelPosition+self.RealIndicesOffset)
        else            : self.RealIndicesOffset = f.tell()-RelPosition
        self.RealIndices = [f.uint32(index) for index in self.RealIndices]

        # get remapped indices
        if f.IsReading(): f.seek(RelPosition+self.FakeIndicesOffset)
        else            : self.FakeIndicesOffset = f.tell()-RelPosition
        if f.IsReading():
            RemapStartPosition = f.tell()
            self.NumRemaps = f.uint32(self.NumRemaps)
            self.RemapOffsets = [0]*self.NumRemaps
            self.RemapCounts = [0]*self.NumRemaps
            for i in range(self.NumRemaps):
                self.RemapOffsets[i] = f.uint32(self.RemapOffsets[i])
                self.RemapCounts[i] = f.uint32(self.RemapCounts[i])
            for i in range(self.NumRemaps):
                f.seek(RemapStartPosition+self.RemapOffsets[i])
                self.Remaps.append([0]*self.RemapCounts[i])
                self.Remaps[i] = [f.uint32(index) for index in self.Remaps[i]]
        else:
            RemapStartPosition = f.tell()
            self.NumRemaps = f.uint32(self.NumRemaps)
            for i in range(self.NumRemaps):
                self.RemapOffsets[i] = f.uint32(self.RemapOffsets[i])
                self.RemapCounts[i] = f.uint32(self.RemapCounts[i])
            for i in range(self.NumRemaps):
                f.seek(RemapStartPosition+self.RemapOffsets[i])
                self.Remaps[i] = [f.uint32(index) for index in self.Remaps[i]]
        return self
    def GetRealIndex(self, bone_index, material_index=0):
        FakeIndex = self.Remaps[material_index][bone_index]
        return self.RealIndices[FakeIndex]
        
    def GetRemappedIndex(self, bone_index, material_index=0):
        return self.Remaps[material_index].index(self.RealIndices.index(bone_index))
        
    def SetRemap(self, remap_info: list[list[str]], transform_info):
        # remap_info is a list of bones indexed by material
        # so the list of bones for material slot 0 is covered by remap_info[0]
        #ideally this eventually allows for creating a remap for any arbitrary bone; requires editing the transform_info
        #return
        # I wonder if you can just take the transform component from the previous bone it was on
        # remap index should match the transform_info index!!!!!
        self.NumRemaps = len(remap_info)
        self.RemapCounts = [0] * self.NumRemaps
        #self.RemapCounts = [len(bone_names) for bone_names in remap_info]
        self.Remaps = []
        self.RemapOffsets = [8*self.NumRemaps+4]
        for i, bone_names in enumerate(remap_info):
            r = []
            for bone in bone_names:
                try:
                    h = int(bone)
                except ValueError:
                    h = murmur32_hash(bone.encode("utf-8"))
                try:
                    real_index = transform_info.NameHashes.index(h)
                except ValueError: # bone not in transform info for unit, unrecoverable
                    PrettyPrint(f"Bone '{bone}' does not exist in unit transform info, skipping...")
                    continue
                try:
                    r.append(self.RealIndices.index(real_index))
                    self.RemapCounts[i] += 1
                except ValueError:
                    PrettyPrint(f"Bone '{bone}' does not exist in LOD bone info, adding...")
                    self.RealIndices.append(real_index)
                    r.append(len(self.RealIndices)-1)
                    self.RemapCounts[i] += 1
                    self.NumBones += 1
                    self.Bones.append(None)
                    
            self.Remaps.append(r)
            
        for i in range(1, self.NumRemaps):
            self.RemapOffsets.append(self.RemapOffsets[i-1]+4*self.RemapCounts[i])
                
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

class MeshSectionInfo: # material info
    def __init__(self, material_slot_list=[]):
        self.MaterialIndex = self.VertexOffset=self.NumVertices=self.IndexOffset=self.NumIndices=self.unk2 = 0
        self.DEV_MeshInfoOffset=0 # helper var, not in file
        self.material_slot_list = material_slot_list
        self.ID = 0
        self.MaterialIndex = self.GroupIndex = 0
    def Serialize(self, f: MemoryStream):
        self.DEV_MeshInfoOffset = f.tell()
        self.MaterialIndex           = f.uint32(self.MaterialIndex)
        if f.IsReading():
            self.ID = self.material_slot_list[self.MaterialIndex]
        self.VertexOffset   = f.uint32(self.VertexOffset)
        self.NumVertices    = f.uint32(self.NumVertices)
        self.IndexOffset    = f.uint32(self.IndexOffset)
        self.NumIndices     = f.uint32(self.NumIndices)
        self.GroupIndex           = f.uint32(self.GroupIndex)
        return self

class MeshInfo:
    def __init__(self):
        self.unk1 = self.unk3 = self.unk4 = self.TransformIndex = self.LodIndex = self.StreamIndex = self.NumSections = self.unk7 = self.unk8 = self.unk9 = self.NumSections_unk = self.MeshID = 0
        self.unk2 = bytearray(32); self.unk6 = bytearray(40)
        self.MaterialIDs = self.Sections = []
        self.NumMaterials = 0
        self.MaterialOffset = 0
        self.SectionsOffset = 0
    def Serialize(self, f: MemoryStream):
        start_offset = f.tell()
        self.unk1 = f.uint64(self.unk1)
        self.unk2 = f.bytes(self.unk2, 32)
        self.MeshID= f.uint32(self.MeshID)
        self.unk3 = f.uint32(self.unk3)
        self.TransformIndex = f.uint32(self.TransformIndex)
        self.unk4 = f.uint32(self.unk4)
        self.LodIndex       = f.int32(self.LodIndex)
        self.StreamIndex    = f.uint32(self.StreamIndex)
        self.unk6           = f.bytes(self.unk6, 40)
        self.NumMaterials = f.uint32(self.NumMaterials)
        self.MaterialOffset = f.uint32(self.MaterialOffset)
        self.unk8           = f.uint64(self.unk8)
        self.NumSections    = f.uint32(self.NumSections)
        if f.IsWriting(): self.SectionsOffset = self.MaterialOffset + 4*self.NumMaterials
        self.SectionsOffset  = f.uint32(self.SectionsOffset)
        if f.IsReading(): self.MaterialIDs  = [0 for n in range(self.NumMaterials)]
        else:             self.MaterialIDs  = [section.ID for section in self.Sections]
        self.MaterialIDs  = [f.uint32(ID) for ID in self.MaterialIDs]
        if f.IsReading(): self.Sections    = [MeshSectionInfo(self.MaterialIDs) for n in range(self.NumSections)]
        self.Sections   = [Section.Serialize(f) for Section in self.Sections]
        return self
    def GetNumIndices(self):
        total = 0
        for section in self.Sections:
            total += section.NumIndices
        return total
    def GetNumVertices(self):
        return self.Sections[0].NumVertices
    
class StingrayMatrix4x4: # Matrix4x4: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_89
    def __init__(self):
        self.v = [float(0)]*16
    def Serialize(self, f: MemoryStream):
        self.v = [f.float32(value) for value in self.v]
        return self
    def ToBlenderMatrix(self):
        mat = mathutils.Matrix.Identity(4)
        mat[0] = self.v[0:4]
        mat[1] = self.v[4:8]
        mat[2] = self.v[8:12]
        mat[3] = self.v[12:16]
        mat.transpose()
        return mat
    def ToLocalTransform(self):
        matrix = mathutils.Matrix([
            [self.v[0], self.v[1], self.v[2], self.v[12]],
            [self.v[4], self.v[5], self.v[6], self.v[13]],
            [self.v[8], self.v[9], self.v[10], self.v[14]],
            [self.v[3], self.v[7], self.v[11], self.v[15]]
        ])
        local_transform = StingrayLocalTransform()
        loc, rot, scale = matrix.decompose()
        rot = rot.to_matrix()
        local_transform.pos = loc
        local_transform.scale = scale
        local_transform.rot.x = rot[0]
        local_transform.rot.y = rot[1]
        local_transform.rot.z = rot[2]
        return local_transform

class StingrayMatrix3x3: # Matrix3x3: https://help.autodesk.com/cloudhelp/ENU/Stingray-SDK-Help/engine_c/plugin__api__types_8h.html#line_84
    def __init__(self):
        self.x = [1,0,0]
        self.y = [0,1,0]
        self.z = [0,0,1]
    def Serialize(self, f: MemoryStream):
        self.x = f.vec3_float(self.x)
        self.y = f.vec3_float(self.y)
        self.z = f.vec3_float(self.z)
        return self
    def ToQuaternion(self):
        T = self.x[0] + self.y[1] + self.z[2]
        M = max(T, self.x[0], self.y[1], self.z[2])
        qmax = 0.5 * sqrt(1-T + 2*M)
        if M == self.x[0]:
            qx = qmax
            qy = (self.x[1] + self.y[0]) / (4*qmax)
            qz = (self.x[2] + self.z[0]) / (4*qmax)
            qw = (self.z[1] - self.y[2]) / (4*qmax)
        elif M == self.y[1]:
            qx = (self.x[1] + self.y[0]) / (4*qmax)
            qy = qmax
            qz = (self.y[2] + self.z[1]) / (4*qmax)
            qw = (self.x[2] - self.z[0]) / (4*qmax)
        elif M == self.z[2]:
            qx = (self.x[2] + self.z[0]) / (4*qmax)
            qy = (self.y[2] + self.z[1]) / (4*qmax)
            qz = qmax
            qw = (self.x[2] - self.z[0]) / (4*qmax)
        else:
            qx = (self.z[1] - self.y[2]) / (4*qmax)
            qy = (self.x[2] - self.z[0]) / (4*qmax)
            qz = (self.y[0] + self.x[1]) / (4*qmax)
            qw = qmax
        return [qx, qy, qz, qw]
    
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
        self.TransformMatrices = []
        self.TransformEntries = []
        self.NameHashes = []
    def Serialize(self, f: MemoryStream):
        if f.IsReading():
            self.NumTransforms = f.uint32(self.NumTransforms)
            f.seek(f.tell()+12)
            self.Transforms = [StingrayLocalTransform().Serialize(f) for n in range(self.NumTransforms)]
            self.TransformMatrices = [StingrayMatrix4x4().Serialize(f) for n in range(self.NumTransforms)]
            self.TransformEntries = [StingrayLocalTransform().SerializeTransformEntry(f) for n in range(self.NumTransforms)]
            self.NameHashes = [f.uint32(n) for n in range(self.NumTransforms)]
        else:
            self.NumTransforms = f.uint32(self.NumTransforms)
            f.seek(f.tell()+12)
            self.Transforms = [t.Serialize(f) for t in self.Transforms]
            self.TransformMatrices = [t.Serialize(f) for t in self.TransformMatrices]
            self.TransformEntries = [t.SerializeTransformEntry(f) for t in self.TransformEntries]
            self.NameHashes = [f.uint32(h) for h in self.NameHashes]
        return self

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

class RawMaterialClass:
    DefaultMaterialName    = "StingrayDefaultMaterial"
    DefaultMaterialShortID = 155175220
    def __init__(self):
        self.MatID      = self.DefaultMaterialName
        self.ShortID    = self.DefaultMaterialShortID
        self.StartIndex = 0
        self.NumIndices = 0
        self.DEV_BoneInfoOverride = None

    def IDFromName(self, unit_id, name, index):
        if name.find(self.DefaultMaterialName) != -1:
            self.MatID   = self.DefaultMaterialName
            self.ShortID = self.DefaultMaterialShortID
        else:
            try:
                self.MatID   = int(name)
                try:
                    self.ShortID = Global_MaterialSlotNames[unit_id][self.MatID][index]
                except (KeyError, IndexError):
                    PrettyPrint(f"Unable to find material slot for material {name} with material count {index} for unit {unit_id}, using random material slot name")
                    self.ShortID = random.randint(1, 0xffffffff)
            except:
                raise Exception("Material name must be a number")

class BoneIndexException(Exception):
    pass
    
class LightList:
    
    def __init__(self):
        self.lights = []
        self.light_count = 0
        self.unk0 = [0, 0, 0]
        
    def Serialize(self, stream: MemoryStream):
        self.light_count = stream.uint32(self.light_count)
        self.unk0 = [stream.uint32(i) for i in self.unk0]
        if stream.IsReading():
            self.lights = [Light() for _ in range(self.light_count)]
        for light in self.lights:
            light.Serialize(stream)
    
class Light:
    
    OMNI = 0 # point in Blender
    SPOT = 1 # spot
    BOX = 2 # area?
    DIRECTIONAL = 3 # sun
    
    CAST_SHADOW = 0x1
    DISABLED = 0x2
    INDIRECT_LIGHTING = 0x4
    VOLUMETRIC_FOG = 0x10

    def __init__(self):
        self.name_hash = self.bone_index = self.falloff_start = self.falloff_end = self.start_angle = self.end_angle = self.unk0 = self.flags = self.light_type = 0
        self.intensity = self.falloff_exp = 1
        self.shadow_bias = 0.4
        self.unk1 = [0] * 5
        self.unk2 = bytearray(32)
        self.color = [0, 0, 0]
        
    def Serialize(self, stream: MemoryStream):
        self.name_hash = stream.uint32(self.name_hash)
        self.bone_index = stream.uint32(self.bone_index)
        self.color = [stream.float32(i) for i in self.color]
        self.intensity = stream.float32(self.intensity)
        self.falloff_start = stream.float32(self.falloff_start)
        self.falloff_end = stream.float32(self.falloff_end)
        self.falloff_exp = stream.float32(self.falloff_exp)
        self.start_angle = stream.float32(self.start_angle)
        self.end_angle = stream.float32(self.end_angle)
        self.unk0 = stream.float32(self.unk0)
        self.shadow_bias = stream.float32(self.shadow_bias)
        self.unk1 = [stream.float32(i) for i in self.unk1]
        self.flags = stream.uint8(self.flags)
        for _ in range(3):
            stream.uint8(0)
        self.light_type = stream.uint32(self.light_type)
        self.unk2 = stream.bytes(self.unk2, 32)

def sign(n):
    if n >= 0:
        return 1
    if n < 0:
        return -1

def octahedral_encode(x, y, z):
    l1_norm = abs(x) + abs(y) + abs(z)
    if l1_norm == 0: return 0, 0
    x /= l1_norm
    y /= l1_norm
    if z < 0:
        x, y = ((1-abs(y)) * sign(x)), ((1-abs(x)) * sign(y))
    return x, y

def octahedral_decode(x, y):
    z = 1 - abs(x) - abs(y)
    if z < 0:
        x, y = ((1-abs(y)) * sign(x)), ((1-abs(x)) * sign(y))
    return mathutils.Vector((x, y, z)).normalized().to_tuple()

def decode_packed_oct_norm(norm):
    r10 = norm & 0x3ff
    g10 = (norm >> 10) & 0x3ff
    return octahedral_decode(
        r10 * (2.0/1023.0) - 1,
        g10 * (2.0/1023.0) - 1
    )

def encode_packed_oct_norm(x, y, z):
    x, y = octahedral_encode(x, y, z)
    return int((x+1)*(1023.0/2.0)) | (int((y+1)*(1023.0/2.0)) << 10)

class SerializeFunctions:
    
    def SerializePositionComponent(gpu, mesh, component, vidx):
        mesh.VertexPositions[vidx] = component.SerializeComponent(gpu, mesh.VertexPositions[vidx])
    
    def SerializeNormalComponent(gpu, mesh, component, vidx):
        if gpu.IsReading():
            norm = component.SerializeComponent(gpu, mesh.VertexNormals[vidx])
            if not isinstance(norm, int):
                norm = list(mathutils.Vector((norm[0],norm[1],norm[2])).normalized())
                mesh.VertexNormals[vidx] = norm[:3]
            else:
                mesh.VertexNormals[vidx] = decode_packed_oct_norm(norm)
        else:
            norm = encode_packed_oct_norm(*mathutils.Vector(mesh.VertexNormals[vidx]).normalized().to_tuple())
            norm = component.SerializeComponent(gpu, norm)
    
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
            raise BoneIndexException(f"Vertex bone index out of range. Component index: {component.Index} vidx: {vidx}")
    
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
            value = f.vec4_uint8([0,0,0,0])
            value[0] = min(1, float(value[0]/255))
            value[1] = min(1, float(value[1]/255))
            value[2] = min(1, float(value[2]/255))
            value[3] = min(1, float(value[3]/255))
        else:
            r = min(255, int(value[0]*255))
            g = min(255, int(value[1]*255))
            b = min(255, int(value[2]*255))
            a = min(255, int(value[3]*255))
            value = f.vec4_uint8([r,g,b,a])
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

def AddMaterialToBlend_EMPTY(ID):
    try:
        bpy.data.materials[str(ID)]
    except:
        mat = bpy.data.materials.new(str(ID)); mat.name = str(ID)
        random.seed(ID)
        mat.diffuse_color = (random.random(), random.random(), random.random(), 1)

def duplicate(obj, data=True, actions=True, collection=None):
    obj_copy = obj.copy()
    if data:
        obj_copy.data = obj_copy.data.copy()
    if actions and obj_copy.animation_data:
        if obj_copy.animation_data.action:
            obj_copy.animation_data.action = obj_copy.animation_data.action.copy()
    bpy.context.collection.objects.link(obj_copy)
    return obj_copy

def CheckUVConflicts(mesh, uvlayer):
    conflicts = {}
    vert_uvs = {}
    texCoord = [[0,0] for vert in mesh.vertices]
    for face_idx, face in enumerate(mesh.polygons):
        for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
            data = (uvlayer.data[loop_idx].uv[0], uvlayer.data[loop_idx].uv[1]*-1 + 1)
            if vert_idx not in vert_uvs:
                vert_uvs[vert_idx] = {}
            if data not in vert_uvs[vert_idx]:
                vert_uvs[vert_idx][data] = []
            vert_uvs[vert_idx][data].append(face_idx)
    for vert_idx in vert_uvs.keys():
        if len(vert_uvs[vert_idx]) > 1:
            conflicts[vert_idx] = True
    if len(conflicts.keys()) > 0:
        return conflicts, vert_uvs
    else:
        return None, None

def PrepareMesh(og_object):
    object = duplicate(og_object)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = object
    mesh = object.data
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal()
    
    if bpy.context.scene.Hd2ToolPanelSettings.SplitUVIslands:
        # merge by distance
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles(use_unselected=False, use_sharp_edge_from_normals=True)

    for uv_layer in mesh.uv_layers:
        mesh.uv_layers.active = uv_layer
        try:
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
    bm.free()
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

def GetMeshData(og_object, Global_TocManager, Global_BoneNames):
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
    mat_count = {}
    for idx in range(len(object.material_slots)):
        try:
            mat_id = int(object.material_slots[idx].name)
        except:
            raise Exception("Material name must be a number")
        if mat_id not in mat_count:
            mat_count[mat_id] = -1
        mat_count[mat_id] += 1
        materials[idx].IDFromName(og_object['Z_ObjectID'], str(mat_id), mat_count[mat_id])

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
    #LoadNormalPalette()
    #normals = NormalsFromPalette(normals)
    # get uvs
    for uvlayer in object.data.uv_layers:
        #if len(uvs) >= 3:
        #    break
        texCoord = [[0,0] for vert in mesh.vertices]
        for face in object.data.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                texCoord[vert_idx] = [uvlayer.data[loop_idx].uv[0], uvlayer.data[loop_idx].uv[1]*-1 + 1]
        uvs.append(texCoord)

    entry_id = int(og_object["Z_ObjectID"])
    try:
        if og_object["Z_SwapID"]:
            entry_id = int(og_object["Z_SwapID"])
    except KeyError:
        pass
    stingray_mesh_entry = Global_TocManager.GetEntry(entry_id, int(UnitID), IgnorePatch=False, SearchAll=True)
    if stingray_mesh_entry:
        if not stingray_mesh_entry.IsLoaded: stingray_mesh_entry.Load(True, False)
        stingray_mesh_entry = stingray_mesh_entry.LoadedData
    else:
        raise Exception(f"Unable to get mesh entry {og_object['Z_ObjectID']}")
    bone_info = stingray_mesh_entry.BoneInfoArray
    transform_info = stingray_mesh_entry.TransformInfo
    light_list = stingray_mesh_entry.LightList
    lod_index = og_object["BoneInfoIndex"]
    bone_entry = Global_TocManager.GetEntry(stingray_mesh_entry.BonesRef, BoneID, IgnorePatch=False, SearchAll=True)
    modified_bone_entry = False
    modified_state_machine = False
    bone_names = []
    bone_data = None
    state_machine_data = None
    state_machine_entry = Global_TocManager.GetEntry(stingray_mesh_entry.StateMachineRef, StateMachineID, IgnorePatch=False, SearchAll=True)
    if bone_entry is None:
        PrettyPrint("This unit does not have any animated bone data, unable to edit bone animated state", "warn")
    else:
        if not Global_TocManager.IsInPatch(bone_entry):
            bone_entry = Global_TocManager.AddEntryToPatch(bone_entry.FileID, BoneID)
        if bone_entry:
            if not bone_entry.IsLoaded:
                bone_entry.Load()
            bone_data = bone_entry.LoadedData
    if state_machine_entry is None:
        PrettyPrint("This unit does not have any state machine data, unable to edit bone animated state", "warn")
    else:
        if not Global_TocManager.IsInPatch(state_machine_entry):
            state_machine_entry = Global_TocManager.AddEntryToPatch(state_machine_entry.FileID, StateMachineID)
        if state_machine_entry:
            if not state_machine_entry.IsLoaded:
                state_machine_entry.Load()
            state_machine_data = state_machine_entry.LoadedData

        
    # get armature object
    prev_obj = bpy.context.view_layer.objects.active
    prev_objs = bpy.context.selected_objects
    prev_mode = prev_obj.mode
    armature_obj = None
    for modifier in og_object.modifiers:
        if modifier.type == "ARMATURE":
            armature_obj = modifier.object
            break
    if armature_obj is not None:
        was_hidden = armature_obj.hide_get()
        state_machine = armature_obj.get("StateMachineID", None)
        armature_obj.hide_set(False)
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        # check if animated bones list has changed, and if it has, clear all modded animations for this armature
        # but keep them in the patch
        if bone_data:
            old_bones = sorted(bone_data.BoneHashes)
            new_bones = sorted([(int(bone.name) if bone.name.isdigit() else murmur32_hash(bone.name.encode("utf-8"))) for bone in armature_obj.data.edit_bones if bone.get('Animated')])
            if old_bones != new_bones:
                PrettyPrint("Changes made to animated bones, clearing saved animation data")
                if state_machine_data:
                    for animation in state_machine_data.animation_ids:
                        animation_data = Global_TocManager.GetEntry(animation, AnimationID, IgnorePatch=False, SearchAll=True)
                        if Global_TocManager.IsInPatch(animation_data):
                            Global_TocManager.RemoveEntryFromPatch(animation, AnimationID)
                        Global_TocManager.AddEntryToPatch(animation, AnimationID)
        
        for bone in armature_obj.data.edit_bones:
            try:
                name_hash = int(bone.name)
            except ValueError:
                name_hash = murmur32_hash(bone.name.encode("utf-8"))
            try:
                transform_index = transform_info.NameHashes.index(name_hash)
            except ValueError:
                # bone doesn't exist, add bone
                transform_info.NameHashes.append(name_hash)
                transform_info.TransformMatrices.append(None)
                transform_info.Transforms.append(None)
                l = StingrayLocalTransform()
                l.Incriment = 1
                l.ParentBone = 0
                transform_info.TransformEntries.append(l)
                transform_info.NumTransforms += 1
                transform_index = len(transform_info.NameHashes) - 1
            
            # set animated
            try:
                animated = bone['Animated']
                if animated and name_hash not in bone_data.BoneHashes:
                    bone_data.BoneHashes.append(name_hash)
                    bone_data.Names.append(bone.name)
                    bone_data.NumNames += 1
                    modified_bone_entry = True
                    modified_state_machine = True
                    for blend_mask in state_machine_data.blend_masks:
                        blend_mask.bone_count += 1
                        blend_mask.bone_weights.append(0.0)
                    if state_machine_data:
                        for animation in state_machine_data.animation_ids:
                            animation_data = Global_TocManager.GetEntry(animation, AnimationID, IgnorePatch=False, SearchAll=True)
                            if not animation_data.IsLoaded:
                                animation_data.Load(False, False)
                            animation_data.LoadedData.add_bone(bone)
                            Global_TocManager.Save(animation, AnimationID)
                if not animated and name_hash in bone_data.BoneHashes:
                    list_index = bone_data.BoneHashes.index(name_hash)
                    bone_data.BoneHashes.pop(list_index)
                    bone_data.Names.pop(list_index)
                    bone_data.NumNames -= 1
                    modified_bone_entry = True
                    modified_state_machine = True
                    for blend_mask in state_machine_data.blend_masks:
                        try:
                            blend_mask.bone_weights.pop(list_index)
                            blend_mask.bone_count -= 1
                        except IndexError: # happens when removing a custom animated bone
                            pass
                    if state_machine_data:
                        for animation in state_machine_data.animation_ids:
                            animation_data = Global_TocManager.GetEntry(animation, AnimationID, IgnorePatch=False, SearchAll=True)
                            if not animation_data.IsLoaded:
                                animation_data.Load(False, False)
                            try:
                                animation_data.LoadedData.remove_bone(list_index)
                            except IndexError: # happens when removing a custom animated bone
                                pass
                            Global_TocManager.Save(animation, AnimationID)
                    else:
                        raise Exception("No state machine property on armature, unable to automatically remove bone data from animations; please set a valid StateMachineID property.")
            except (KeyError, AttributeError) as e:
                print(e)
                
            # set ragdoll
            '''
            try:
                bone_index = bone_data.BoneHashes.index(name_hash)
                modified_state_machine = True
                print(f"Setting jiggle bone for {bone.name}")
                state_machine_data.remove_ragdoll(bone_index)
                ragdoll = bone['Jiggle']
                print(ragdoll)
                weight = bone["Weight"]
                gravity = bone["Gravity"]
                param3 = bone["Param 3"]
                param4 = bone["Param 4"]
                param5 = bone["Param 5"]
                param6 = bone["Param 6"]
                param7 = bone["Param 7"]
                param8 = bone["Param 8"]
                param9 = bone["Param 9"]
                params = [weight, gravity, param3, param4, param5, param6, param7, param8, param9]
                if ragdoll:
                    state_machine_data.set_ragdoll(bone_index, params)
            except (KeyError, AttributeError) as e:
                pass
            except ValueError as e:
                pass
            '''
            
            # set bone matrix
            loc, rot, scale = bone.matrix.decompose()
            if transform_info.TransformMatrices[transform_index]:
                scale = transform_info.TransformMatrices[transform_index].ToLocalTransform().scale
            else:
                scale = [1, 1, 1]
            m = mathutils.Matrix.LocRotScale(loc, rot, mathutils.Vector(scale))
            m.transpose()
            transform_matrix = StingrayMatrix4x4()
            transform_matrix.v = [
                m[0][0], m[0][1], m[0][2], m[0][3],
                m[1][0], m[1][1], m[1][2], m[1][3],
                m[2][0], m[2][1], m[2][2], m[2][3],
                m[3][0], m[3][1], m[3][2], m[3][3]
            ]
            
            # set bone local transform
            transform_info.TransformMatrices[transform_index] = transform_matrix
            if bone.parent:
                parent_matrix = bone.parent.matrix
                local_transform_matrix = parent_matrix.inverted() @ bone.matrix
                translation, rotation, _ = local_transform_matrix.decompose()
                rotation = rotation.to_matrix()
                transform_local = StingrayLocalTransform()
                transform_local.rot.x = [rotation[0][0], rotation[1][0], rotation[2][0]]
                transform_local.rot.y = [rotation[0][1], rotation[1][1], rotation[2][1]]
                transform_local.rot.z = [rotation[0][2], rotation[1][2], rotation[2][2]]
                transform_local.pos = translation
                transform_local.scale = scale
                transform_info.Transforms[transform_index] = transform_local
            else:
                transform_local = StingrayLocalTransform()
                transform_info.Transforms[transform_index] = transform_local
                
            # set bone parent
            if bone.parent:
                try:
                    parent_name_hash = int(bone.parent.name)
                except ValueError:
                    parent_name_hash = murmur32_hash(bone.parent.name.encode("utf-8"))
                try:
                    parent_transform_index = transform_info.NameHashes.index(parent_name_hash)
                    transform_info.TransformEntries[transform_index].ParentBone = parent_transform_index
                except ValueError:
                    PrettyPrint(f"Failed to parent bone: {bone.name}.", 'warn')
                    
        armature_obj.hide_set(was_hidden)
        for obj in prev_objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = prev_obj
        bpy.ops.object.mode_set(mode=prev_mode)
        
    if modified_bone_entry and bone_entry:
        bone_entry.Save()
        
    if modified_state_machine and state_machine_entry:
        state_machine_entry.Save()
    
    # get lights
    if armature_obj is not None:
        bpy.ops.object.mode_set(mode='EDIT')
        for blender_light in [child for child in armature_obj.children if child.type == "LIGHT"]:
            blend_light_data = blender_light.data
            light_name_hash = 0
            try:
                light_name_hash = int(blender_light.name.split(".")[0])
            except ValueError:
                light_name_hash = murmur32_hash(blender_light.name.split(".")[0].encode())
            if not blender_light.parent or blender_light.parent_type != "BONE":
                PrettyPrint("Light has no parent bone, skipping...")
                continue
            light_bone_index = -1
            for i, bone in enumerate(armature_obj.data.edit_bones):
                if bone.name == blender_light.parent_bone:
                    try:
                        bone_name_hash = int(bone.name)
                    except:
                        bone_name_hash = murmur32_hash(bone.name.encode())
                    light_bone_index = transform_info.NameHashes.index(bone_name_hash)
                    break
            if light_bone_index == -1:
                PrettyPrint("Failed to find bone")
                continue
            target_light = None
            for light in light_list.lights:
                if light.name_hash == light_name_hash:
                    target_light = light
                    break
            new_light = True if not target_light else False
            if new_light:
                light_list.light_count += 1
                target_light = Light()
                target_light.name_hash = light_name_hash
            target_light.bone_index = light_bone_index
            if isinstance(blend_light_data, bpy.types.SpotLight):
                target_light.end_angle = blend_light_data.spot_size
                target_light.light_type = Light.SPOT
                target_light.falloff_end = blend_light_data.cutoff_distance
            elif isinstance(blend_light_data, bpy.types.PointLight):
                target_light.light_type = Light.OMNI
                target_light.falloff_end = blend_light_data.cutoff_distance
            elif isinstance(blend_light_data, bpy.types.AreaLight):
                target_light.light_type = Light.BOX
                target_light.falloff_start = -(blend_light_data.size/2)   # -X
                target_light.falloff_end = blend_light_data.size/2        # +X
                target_light.falloff_exp = 0                              # -Y
                target_light.start_angle = -blend_light_data.size_y/2     # -Z
                target_light.end_angle = blend_light_data.cutoff_distance # +Y
                target_light.unk0 = blend_light_data.size_y/2             # +Z
            elif isinstance(blend_light_data, bpy.types.SunLight):
                target_light.light_type = Light.DIRECTIONAL
                target_light.end_angle = math.pi
            color = blend_light_data.color
            intensity = blend_light_data.energy
            target_light.flags = target_light.flags & 0b11101110
            if blend_light_data.use_shadow:
                target_light.flags |= Light.CAST_SHADOW
            try:
                if blend_light_data['Volumetric']:
                    target_light.flags |= Light.VOLUMETRIC_FOG
            except Exception as e:
                print(e)
                    
            target_light.color = [color.r * intensity, color.g*intensity, color.b*intensity]
            if new_light:
                light_list.lights.append(target_light)
        bpy.ops.object.mode_set(mode=prev_mode)  
    
    # get weights
    vert_idx = 0
    numInfluences = 4                
    if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
        if len(object.vertex_groups) > 0:
            for g in object.vertex_groups:
                bone_names.append(g.name)
            remap_info = [bone_names for _ in range(len(object.material_slots))]
            bone_info[lod_index].SetRemap(remap_info, transform_info)
        
        vertex_to_material_index = [5000 for _ in range(len(mesh.vertices))]
        for polygon in mesh.polygons:
            for vertex in polygon.vertices:
                vertex_to_material_index[vertex] = polygon.material_index
    
    if len(object.vertex_groups) > 0:
        for vert_idx, vertex in enumerate(mesh.vertices):
            for group_idx, group in enumerate(vertex.groups):
                # limit influences
                if group_idx >= numInfluences:
                    break
                if group.weight > 0.001:
                    vertex_group        = object.vertex_groups[group.group]
                    vertex_group_name   = vertex_group.name
                    
                    #
                    # CHANGE THIS TO SUPPORT THE NEW BONE NAMES
                    # HOW TO ACCESS transform_info OF STINGRAY MESH??
                    if bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
                        parts               = vertex_group_name.split("_")
                        HDGroupIndex        = int(parts[0])
                        HDBoneIndex         = int(parts[1])
                    else:
                        material_idx = vertex_to_material_index[vert_idx]
                        try:
                            name_hash = int(vertex_group_name)
                        except ValueError:
                            name_hash = murmur32_hash(vertex_group_name.encode("utf-8"))
                        HDGroupIndex = 0
                        try:
                            real_index = transform_info.NameHashes.index(name_hash)
                        except ValueError:
                            existing_names = []
                            for i, h in enumerate(transform_info.NameHashes):
                                try:
                                    if i in bone_info[lod_index].RealIndices:
                                        existing_names.append(Global_BoneNames[h])
                                except KeyError:
                                    existing_names.append(str(h))
                                except IndexError:
                                    pass
                            if object:
                                PrettyPrint(f"Deleting object early and exiting weight painting mode...", 'error')
                                bpy.ops.object.mode_set(mode='OBJECT')
                                bpy.data.objects.remove(object, do_unlink=True)
                            raise Exception(f"\n\nVertex Group: {vertex_group_name} is not a valid vertex group for the model.\nIf you are using legacy weight names, make sure you enable the option in the settings.\n\nValid vertex group names: {existing_names}")
                        try:
                            HDBoneIndex = bone_info[lod_index].GetRemappedIndex(real_index, material_idx)
                        except (ValueError, IndexError): # bone index not in remap because the bone is not in the LOD bone data
                            HDBoneIndex = 0
                            
                    # get real index from remapped index -> hashIndex = bone_info[mesh.LodIndex].GetRealIndex(bone_index); boneHash = transform_info.NameHashes[hashIndex]
                    # want to get remapped index from bone name
                    # hash = ...
                    # real_index = transform_info.NameHashes.index(hash)
                    # remap = bone_info[mesh.LodIndex].GetRemappedIndex(real_index)
                    if HDGroupIndex+1 > len(boneIndices):
                        dif = HDGroupIndex+1 - len(boneIndices)
                        boneIndices.extend([[[0,0,0,0] for n in range(len(mesh.vertices))]]*dif)
                    boneIndices[HDGroupIndex][vert_idx][group_idx] = HDBoneIndex
                    weights[vert_idx][group_idx] = group.weight
        if boneIndices == []:
            weights = []
    else:
        boneIndices = []
        weights     = []
    
    # set bone matrices in bone index mappings
    # matrices in bone_info are the inverted joint matrices (for some reason)
    # and also relative to the mesh transform
    if lod_index != -1:
        mesh_info_index = og_object["MeshInfoIndex"]
        mesh_info = stingray_mesh_entry.MeshInfoArray[mesh_info_index]
        origin_transform_matrix = transform_info.TransformMatrices[mesh_info.TransformIndex].ToBlenderMatrix().inverted()
        for i, transform_index in enumerate(bone_info[lod_index].RealIndices):
            bone_matrix = transform_info.TransformMatrices[transform_index]
            m = (origin_transform_matrix @ bone_matrix.ToBlenderMatrix()).inverted().transposed()
            transform_matrix = StingrayMatrix4x4()
            transform_matrix.v = [
                m[0][0], m[0][1], m[0][2], m[0][3],
                m[1][0], m[1][1], m[1][2], m[1][3],
                m[2][0], m[2][1], m[2][2], m[2][3],
                m[3][0], m[3][1], m[3][2], m[3][3]
            ]
            bone_info[lod_index].Bones[i] = transform_matrix

    #bpy.ops.object.mode_set(mode='OBJECT')
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

def GetObjectsMeshData(Global_TocManager, Global_BoneNames):
    objects = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')
    data = {}
    for object in objects:
        if object.type != 'MESH':
            continue
        ID = object["Z_ObjectID"]
        try:
            SwapID = object["Z_SwapID"]
            if SwapID and SwapID.isnumeric():
                ID = SwapID
        except KeyError:
            pass
        MeshData = GetMeshData(object, Global_TocManager, Global_BoneNames)
        try:
            data[ID][MeshData.MeshInfoIndex] = MeshData
        except:
            data[ID] = {MeshData.MeshInfoIndex: MeshData}
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
            if murmur32_hash(bone_name.encode()) == mesh.MeshID:
                name = bone_name

    return name

def CreateModel(stingray_unit, id, Global_BoneNames, bones_entry, state_machine_entry):
    model, customization_info, bone_names, transform_info, bone_info, lights = stingray_unit.RawMeshes, stingray_unit.CustomizationInfo, stingray_unit.BoneNames, stingray_unit.TransformInfo, stingray_unit.BoneInfoArray, stingray_unit.LightList
    imported_lights = False
    if len(model) < 1: return
    # Make collection
    old_collection = bpy.context.collection
    if bpy.context.scene.Hd2ToolPanelSettings.MakeCollections:
        new_collection = bpy.data.collections.new(NameFromMesh(model[0], id, customization_info, bone_names, False))
        old_collection.children.link(new_collection)
    else:
        new_collection = old_collection
    # Make Meshes
    for mesh_count, mesh in enumerate(model):
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
        translation, rotation, scale = mesh.DEV_Transform.decompose()
        new_object.scale = scale
        new_object.location = translation
        new_object.rotation_mode = 'QUATERNION'
        new_object.rotation_quaternion = rotation
        #local_transform = mesh.DEV_Transform
        #new_object.scale = local_transform.scale
        #new_object.location = local_transform.pos
        #new_object.rotation_mode = 'QUATERNION'
        #new_object.rotation_quaternion = mathutils.Matrix([local_transform.rot.x, local_transform.rot.y, local_transform.rot.z]).to_quaternion()

        # set object properties
        new_object["MeshInfoIndex"] = mesh.MeshInfoIndex
        new_object["BoneInfoIndex"] = mesh.LodIndex
        new_object["Z_ObjectID"] = str(id)
        new_object["Z_SwapID"] = ""
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
        available_bones = []
        for i, h in enumerate(transform_info.NameHashes):
            try:
                if i in bone_info[mesh.LodIndex].RealIndices:
                    available_bones.append(Global_BoneNames.get(h, str(h)))
            except IndexError:
                pass
        vertex_to_material_index = [5000]*len(mesh.VertexPositions)
        for mat_idx, mat in enumerate(mesh.Materials):
            for face in mesh.Indices[mat.StartIndex//3:(mat.StartIndex//3+mat.NumIndices//3)]:
                for vert_idx in face:
                    vertex_to_material_index[vert_idx] = mat_idx
        for vertex_idx in range(len(mesh.VertexWeights)):
            weights      = mesh.VertexWeights[vertex_idx]
            index_groups = [Indices[vertex_idx] for Indices in mesh.VertexBoneIndices]
            for group_index, indices in enumerate(index_groups):
                if bpy.context.scene.Hd2ToolPanelSettings.ImportGroup0 and group_index != 0:
                    continue
                if type(weights) != list:
                    weights = [weights]
                for weight_idx in range(len(weights)):
                    weight_value = weights[weight_idx]
                    bone_index   = indices[weight_idx]
                    if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
                        try:
                            hashIndex = bone_info[mesh.LodIndex].GetRealIndex(bone_index, vertex_to_material_index[vertex_idx])
                        except:
                            continue
                        boneHash = transform_info.NameHashes[hashIndex]
                        group_name = Global_BoneNames.get(boneHash, str(boneHash))
                    else:
                        group_name = str(group_index) + "_" + str(bone_index)
                    if group_name not in created_groups:
                        created_groups.append(group_name)
                        try:
                            available_bones.remove(group_name)
                        except ValueError:
                            pass
                        new_vertex_group = new_object.vertex_groups.new(name=str(group_name))
                    vertex_group_data = [vertex_idx]
                    new_object.vertex_groups[str(group_name)].add(vertex_group_data, weight_value, 'ADD')
        if not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
            for bone in available_bones:
                new_vertex_group = new_object.vertex_groups.new(name=str(bone))
                
        # -- || ADD BONES || -- #
        skeletonObj = None
        armature = None
        if bpy.context.scene.Hd2ToolPanelSettings.ImportArmature and not bpy.context.scene.Hd2ToolPanelSettings.LegacyWeightNames:
            if len(bpy.context.selected_objects) > 0:
                skeletonObj = bpy.context.selected_objects[0]
            if skeletonObj and skeletonObj.type == 'ARMATURE':
                armature = skeletonObj.data
            if armature != None and (bpy.context.scene.Hd2ToolPanelSettings.MergeArmatures or armature.name.startswith(str(id))):
                PrettyPrint(f"Merging to previous skeleton: {skeletonObj.name}")
            else:
                PrettyPrint(f"Creating New Skeleton")
                armature = bpy.data.armatures.new(f"{id}_skeleton")
                armature.display_type = "OCTAHEDRAL"
                armature.show_names = True
                skeletonObj = bpy.data.objects.new(f"{id}_rig", armature)
                skeletonObj['BonesID'] = str(stingray_unit.BonesRef)
                skeletonObj['StateMachineID'] = str(stingray_unit.StateMachineRef)
                skeletonObj.show_in_front = True
                
            if bpy.context.scene.Hd2ToolPanelSettings.MakeCollections:
                if 'skeletons' not in bpy.data.collections:
                    collection = bpy.data.collections.new("skeletons")
                    bpy.context.scene.collection.children.link(collection)
                else:
                    collection = bpy.data.collections['skeletons']
            else:
                collection = bpy.context.collection

            try:
                collection.objects.link(skeletonObj)
            except Exception as e:
                PrettyPrint(f"{e}", 'warn')

            #bpy.context.active_object = skeletonObj
            bpy.context.view_layer.objects.active = skeletonObj
            bpy.ops.object.mode_set(mode='EDIT')
            bones = None
            boneParents = None
            boneTransforms = {}
            boneMatrices = {}
            doPoseBone = {}
            if mesh.LodIndex in [-1, 0]:
                bones = [None] * transform_info.NumTransforms
                boneParents = [0] * transform_info.NumTransforms
                for i, transform in enumerate(transform_info.TransformEntries):
                    boneParent = transform.ParentBone
                    boneHash = transform_info.NameHashes[i]
                    if boneHash in Global_BoneNames: # name of bone
                        boneName = Global_BoneNames[boneHash]
                    else:
                        boneName = str(boneHash)
                    animated = False
                    ragdoll = False
                    ragdoll_params = []
                    if bones_entry and boneName in bones_entry.Names:
                        animated = True
                        bone_index = bones_entry.Names.index(boneName)
                        for r in state_machine_entry.ragdolls:
                            if r.bone_index == bone_index:
                                ragdoll = True
                                ragdoll_params = r.params
                                break
                    try:
                        b = int(boneName)
                        if bones_entry and b in bones_entry.BoneHashes:
                            animated = True
                    except ValueError:
                        pass
                    newBone = armature.edit_bones.get(boneName)
                    if newBone is None:
                        newBone = armature.edit_bones.new(boneName)
                        newBone.tail = 0, 0.05, 0
                        if bones_entry: newBone['Animated'] = animated
                        '''
                        if bones_entry:
                            newBone['Jiggle'] = ragdoll
                            if ragdoll:
                                newBone['Weight'] = ragdoll_params[0]
                                newBone['Gravity'] = ragdoll_params[1]
                                newBone['Param 3'] = ragdoll_params[2]
                                newBone['Param 4'] = ragdoll_params[3]
                                newBone['Param 5'] = ragdoll_params[4]
                                newBone['Param 6'] = ragdoll_params[5]
                                newBone['Param 7'] = ragdoll_params[6]
                                newBone['Param 8'] = ragdoll_params[7]
                                newBone['Param 9'] = ragdoll_params[8]
                        '''
                        doPoseBone[newBone.name] = True
                    else:
                        doPoseBone[newBone.name] = False
                    bones[i] = newBone
                    boneParents[i] = boneParent
                    boneTransforms[newBone.name] = transform_info.Transforms[i]
                    boneMatrices[newBone.name] = transform_info.TransformMatrices[i]
            else:
                b_info = bone_info[mesh.LodIndex]
                bones = [None] * b_info.NumBones
                boneParents = [0] * b_info.NumBones
                for i, bone in enumerate(b_info.Bones): # this is not every bone in the transform_info
                    boneIndex = b_info.RealIndices[i] # index of bone in transform info
                    boneParent = transform_info.TransformEntries[boneIndex].ParentBone # index of parent bone in transform info
                    # index of parent bone in b_info.Bones?
                    if boneParent in b_info.RealIndices:
                        boneParentIndex = b_info.RealIndices.index(boneParent)
                    else:
                        boneParentIndex = -1
                    boneHash = transform_info.NameHashes[boneIndex]
                    if boneHash in Global_BoneNames: # name of bone
                        boneName = Global_BoneNames[boneHash]
                    else:
                        boneName = str(boneHash)
                    animated = False
                    if bones_entry and boneName in bones_entry.Names:
                        animated = True
                    try:
                        b = int(boneName)
                        if bones_entry and b in bones_entry.BoneHashes:
                            animated = True
                    except ValueError:
                        pass
                    newBone = armature.edit_bones.get(boneName)
                    if newBone is None:
                        newBone = armature.edit_bones.new(boneName)
                        newBone.tail = 0, 0.05, 0
                        if bones_entry: newBone['Animated'] = animated
                        doPoseBone[newBone.name] = True
                    else:
                        doPoseBone[newBone.name] = False
                    bones[i] = newBone
                    boneTransforms[newBone.name] = transform_info.Transforms[boneIndex]
                    boneMatrices[newBone.name] = transform_info.TransformMatrices[boneIndex]
                    boneParents[i] = boneParentIndex
                    
            # parent all bones
            for i, bone in enumerate(bones):
                if boneParents[i] > -1:
                    bone.parent = bones[boneParents[i]]
            
            # pose all bones   
            bpy.context.view_layer.objects.active = skeletonObj
            
            for i, bone in enumerate(armature.edit_bones):
                try:
                    if not doPoseBone[bone.name]: continue
                    a = boneMatrices[bone.name]
                    mat = mathutils.Matrix.Identity(4)
                    mat[0] = a.v[0:4]
                    mat[1] = a.v[4:8]
                    mat[2] = a.v[8:12]
                    mat[3] = a.v[12:16]
                    mat.transpose()
                    bone.matrix = mat
                except Exception as e:
                    PrettyPrint(f"Failed setting bone matricies for: {e}. This may be intended", 'warn')
                
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # assign armature modifier to the mesh object
            modifier = new_object.modifiers.get("ARMATURE")
            if (modifier == None):
                modifier = new_object.modifiers.new("Armature", "ARMATURE")
                modifier.object = skeletonObj

            if bpy.context.scene.Hd2ToolPanelSettings.ParentArmature:
                new_object.parent = skeletonObj
            
            # select the armature at the end so we can chain import when merging
            for obj in bpy.context.selected_objects:
                obj.select_set(False)
            skeletonObj.select_set(True)
            
            # create empty animation data if it does not exist
            if not skeletonObj.animation_data:
              skeletonObj.animation_data_create()
        
        
        if skeletonObj is not None and not imported_lights:
            imported_lights = True
            current_mode = bpy.context.mode
            bpy.ops.object.mode_set(mode='EDIT')
            for light in lights.lights:
                blend_light = None
                if light.light_type == Light.OMNI:
                    light_type = "POINT"
                    blend_light = bpy.data.lights.new(name = str(light.name_hash), type=light_type)
                    blend_light.color = mathutils.Color(mathutils.Vector(light.color).normalized().to_tuple())
                    blend_light.use_custom_distance = True
                    blend_light.cutoff_distance = light.falloff_end
                    #blend_light.exposure = light.falloff_exp
                    blend_light.energy = sqrt(sum([component**2 for component in light.color]))
                elif light.light_type == Light.SPOT:
                    light_type = "SPOT"
                    blend_light = bpy.data.lights.new(name = str(light.name_hash), type=light_type)
                    blend_light.color = mathutils.Color(mathutils.Vector(light.color).normalized().to_tuple())
                    blend_light.use_custom_distance = True
                    blend_light.cutoff_distance = light.falloff_end
                    #blend_light.exposure = light.falloff_exp
                    blend_light.energy = sqrt(sum([component**2 for component in light.color]))
                    blend_light.spot_size = light.end_angle
                    blend_light.show_cone = True
                elif light.light_type == Light.BOX:
                    light_type = "AREA"
                    blend_light = bpy.data.lights.new(name = str(light.name_hash), type=light_type)
                    blend_light.color = mathutils.Color(mathutils.Vector(light.color).normalized().to_tuple())
                    blend_light.use_custom_distance = True
                    blend_light.cutoff_distance = light.falloff_end
                    #blend_light.exposure = light.falloff_exp
                    blend_light.energy = sqrt(sum([component**2 for component in light.color]))
                    blend_light.shape = "RECTANGLE"
                    blend_light.size = 1
                    blend_light.size_y = 1
                elif light.light_type == Light.DIRECTIONAL:
                    light_type = "SUN"
                    blend_light = bpy.data.lights.new(name = str(light.name_hash), type=light_type)
                    blend_light.color = mathutils.Color(mathutils.Vector(light.color).normalized().to_tuple())
                    blend_light.use_custom_distance = True
                    blend_light.cutoff_distance = light.falloff_end
                    #blend_light.exposure = light.falloff_exp
                    blend_light.energy = sqrt(sum([component**2 for component in light.color]))
                else:
                    print("UNKNOWN LIGHT TYPE")
                    print(light.light_type)
                    continue
                if light.flags & Light.CAST_SHADOW:
                    blend_light.use_shadow = True
                else:
                    blend_light.use_shadow = False
                if light.flags & Light.VOLUMETRIC_FOG:
                    blend_light['Volumetric'] = True
                else:
                    blend_light['Volumetric'] = False
                blend_light.use_custom_distance = True
                light_object = bpy.data.objects.new(name = str(light.name_hash), object_data = blend_light)
                light_object.lock_rotation = (True, True, True)
                light_object.lock_location = (True, True, True)
                light_object.lock_scale = (True, True, True)
                bpy.context.collection.objects.link(light_object)
                rotation_matrix = mathutils.Matrix.Rotation(1.57079632679, 4, 'X')
                if armature:
                    for index, bone in enumerate(armature.edit_bones):
                        try:
                            bone_name_hash = int(bone.name)
                        except:
                            bone_name_hash = murmur32_hash(bone.name.encode())
                        if transform_info.NameHashes.index(bone_name_hash) == light.bone_index:
                            light_object.parent = skeletonObj
                            light_object.parent_bone = bone.name
                            light_object.parent_type = "BONE"
                            light_object.matrix_parent_inverse = light_object.matrix_parent_inverse.inverted() @ rotation_matrix
                            break
            bpy.ops.object.mode_set(mode=current_mode)
            
        
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
        bm.free()
