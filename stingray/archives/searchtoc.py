from pathlib import Path
import struct


class SearchToc:
    def __init__(self):
        self.TocEntries = {}
        self.fileIDs = []
        self.Path = ""
        self.Name = ""

    def HasEntry(self, file_id, type_id):
        file_id = int(file_id)
        type_id = int(type_id)
        try:
            return file_id in self.TocEntries[type_id]
        except KeyError:
            return False

    def FromFile(self, path):
        self.UpdatePath(path)
        bin_data = b""
        file = open(path, 'r+b')
        bin_data = file.read(12)
        magic, numTypes, numFiles = struct.unpack("<III", bin_data)
        if magic != 4026531857:
            file.close()
            return False

        offset = 60 + (numTypes << 5)
        bin_data = file.read(offset + 80 * numFiles)
        file.close()
        for _ in range(numFiles):
            file_id, type_id = struct.unpack_from("<QQ", bin_data, offset=offset)
            self.fileIDs.append(int(file_id))
            try:
                self.TocEntries[type_id].append(file_id)
            except KeyError:
                self.TocEntries[type_id] = [file_id]
            offset += 80
        return True

    def UpdatePath(self, path):
        self.Path = path
        self.Name = Path(path).name
        