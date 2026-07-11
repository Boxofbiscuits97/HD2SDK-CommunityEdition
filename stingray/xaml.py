from ..utils.logger import PrettyPrint
from ..utils.memoryStream import MemoryStream

class StingrayXAML:
    def __init__(self):
        self.length   = 0
        self.xamlData = b""

    def Serialize(self, f: MemoryStream):
        PrettyPrint("Serializing XAML")

        if f.IsReading():
            self.length = f.uint32(self.length)
            f.seek(16)
            self.xamlData = f.bytes(self.xamlData, self.length)

        if f.IsWriting():
            f.uint32(len(self.xamlData))
            f.seek(16)
            f.bytes(self.xamlData)
