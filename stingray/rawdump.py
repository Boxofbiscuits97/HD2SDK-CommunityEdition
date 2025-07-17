from memoryStream import MemoryStream


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
