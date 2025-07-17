from memoryStream import MemoryStream
from __init__ import PrettyPrint


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
