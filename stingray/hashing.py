import ctypes
import datetime
import random as r

from __init__ import Global_TypeHashes, Global_NameHashes, Global_ArchiveHashes, Global_TocManager, Global_filehashpath, Global_friendlynamespath, Global_CPPHelper, PrettyPrint
from memoryStream import MemoryStream


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

def RandomHash16():
    global Global_previousRandomHash
    hash = Global_previousRandomHash
    while hash == Global_previousRandomHash:
        r.seed(datetime.datetime.now().timestamp())
        hash = r.randint(1, 0xffffffffffffffff)
    Global_previousRandomHash = hash
    PrettyPrint(f"Generated hash: {hash}")
    return hash

def hex_to_decimal(hex_string):
    try:
        decimal_value = int(hex_string, 16)
        return decimal_value
    except ValueError:
        print(f"Invalid hexadecimal string: {hex_string}")