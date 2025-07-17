from memoryStream import MemoryStream
from __init__ import PrettyPrint


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
