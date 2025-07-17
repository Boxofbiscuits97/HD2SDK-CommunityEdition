bl_info = {
    "name": "Helldivers 2 SDK: Community Edition",
    "version": (3, 0, 0),
    "blender": (4, 0, 0),
    "category": "Import-Export",
}

# pyright: reportInvalidTypeForm=false

#region Imports

# System
import configparser
import ctypes, os
import requests
import json

# Blender
import bpy
from bpy.props import PointerProperty
from bpy.types import Scene

from contextmenu import CustomPropertyContext, WM_MT_button_context
from mainpanel import HellDivers2ToolsPanel

from operators.archive import *
from operators.copyID import *
from operators.dump import *
from operators.entry import *
from operators.filepath import *
from operators.hd2properties import *
from operators.help import *
from operators.material import *
from operators.mesh import *
from operators.particle import *
from operators.patch import *
from operators.repatch import *
from operators.search import *
from operators.texture import *
from operators.tools import *

from settings import Hd2ToolPanelSettings
from stingray.archives.tocmanager import TocManager
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
Global_gamepathIsValid   = False
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

#endregion

#region Functions: Logging

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

#endregion

#region Functions: Initialization

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

#endregion

#region Config

def InitializeConfig():
    global Global_gamepath, Global_searchpath, Global_configpath, Global_gamepathIsValid
    if os.path.exists(Global_configpath):
        config = configparser.ConfigParser()
        config.read(Global_configpath, encoding='utf-8')
        try:
            Global_gamepath = config['DEFAULT']['filepath']
            Global_searchpath = config['DEFAULT']['searchpath']
        except:
            UpdateConfig()
        if os.path.exists(Global_gamepath):
            PrettyPrint(f"Loaded Data Folder: {Global_gamepath}")
            Global_gamepathIsValid = True
        else:
            PrettyPrint(f"Game path: {Global_gamepath} is not a valid directory", 'ERROR')
            Global_gamepathIsValid = False

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
    ImportDumpByIDOperator,
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
