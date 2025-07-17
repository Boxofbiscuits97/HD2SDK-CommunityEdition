from bpy.props import EnumProperty, BoolProperty, StringProperty
from bpy.types import PropertyGroup
from stingray.hashing import GetArchiveNameFromID
from __init__ import Global_TocManager

# pyright: reportInvalidTypeForm=false

def LoadedArchives_callback(scene, context):
    return [(Archive.Name, GetArchiveNameFromID(Archive.Name) if GetArchiveNameFromID(Archive.Name) != "" else Archive.Name, Archive.Name) for Archive in Global_TocManager.LoadedArchives]

def Patches_callback(scene, context):
    return [(Archive.Name, Archive.Name, Archive.Name) for Archive in Global_TocManager.Patches]

class Hd2ToolPanelSettings(PropertyGroup):
    # Patches
    Patches   : EnumProperty(name="Patches", items=Patches_callback)
    PatchOnly : BoolProperty(name="Show Patch Entries Only", description = "Filter list to entries present in current patch", default = False)
    # Archive
    ContentsExpanded : BoolProperty(default = True)
    LoadedArchives   : EnumProperty(name="LoadedArchives", items=LoadedArchives_callback)
    # Settings
    MenuExpanded     : BoolProperty(default = False)

    ShowExtras       : BoolProperty(name="Extra Entry Types", description = "Shows all Extra entry types.", default = False)
    FriendlyNames    : BoolProperty(name="Show Friendly Names", description="Enable friendly names for entries if they have any. Disabling this option can greatly increase UI preformance if a patch has a large number of entries.", default = True)

    ImportMaterials  : BoolProperty(name="Import Materials", description = "Fully import materials by appending the textures utilized, otherwise create placeholders", default = True)
    ImportLods       : BoolProperty(name="Import LODs", description = "Import LODs", default = False)
    ImportGroup0     : BoolProperty(name="Import Group 0 Only", description = "Only import the first vertex group, ignore others", default = True)
    ImportCulling    : BoolProperty(name="Import Culling Bounds", description = "Import Culling Bodies", default = False)
    ImportStatic     : BoolProperty(name="Import Static Meshes", description = "Import Static Meshes", default = False)
    MakeCollections  : BoolProperty(name="Make Collections", description = "Make new collection when importing meshes", default = False)
    Force3UVs        : BoolProperty(name="Force 3 UV Sets", description = "Force at least 3 UV sets, some materials require this", default = True)
    Force1Group      : BoolProperty(name="Force 1 Group", description = "Force mesh to only have 1 vertex group", default = True)
    AutoLods         : BoolProperty(name="Auto LODs", description = "Automatically generate LOD entries based on LOD0, does not actually reduce the quality of the mesh", default = True)
    RemoveGoreMeshes : BoolProperty(name="Remove Gore Meshes", description = "Automatically delete all of the verticies with the gore material when loading a model", default = False)
    # Search
    SearchField      : StringProperty(default = "")

    # Tools
    EnableTools           : BoolProperty(name="Special Tools", description = "Enable advanced SDK Tools", default = False)
    UnloadEmptyArchives   : BoolProperty(name="Unload Empty Archives", description="Unload Archives that do not Contain any Textures, Materials, or Meshes", default = True)
    DeleteOnLoadArchive   : BoolProperty(name="Nuke Files on Archive Load", description="Delete all Textures, Materials, and Meshes in project when selecting a new archive", default = False)
    UnloadPatches         : BoolProperty(name="Unload Previous Patches", description="Unload Previous Patches when bulk loading")
    LoadFoundArchives     : BoolProperty(name="Load Found Archives", description="Load the archives found when search by entry ID", default=True)

    AutoSaveMeshMaterials : BoolProperty(name="Autosave Mesh Materials", description="Save unsaved material entries applied to meshes when the mesh is saved", default = True)
    SaveNonSDKMaterials   : BoolProperty(name="Save Non-SDK Materials", description="Toggle if non-SDK materials should be autosaved when saving a mesh", default = False)
    SaveUnsavedOnWrite    : BoolProperty(name="Save Unsaved on Write", description="Save all entries that are unsaved when writing a patch", default = True)
    PatchBaseArchiveOnly  : BoolProperty(name="Patch Base Archive Only", description="When enabled, it will allow patched to only be created if the base archive is selected. This is helpful for new users.", default = True)
    LegacyWeightNames     : BoolProperty(name="Legacy Weight Names", description="Brings back the old naming system for vertex groups using the X_Y schema", default = True)
    
    def get_settings_dict(self):
        dict = {}
        dict["MenuExpanded"] = self.MenuExpanded
        dict["ShowExtras"] = self.ShowExtras
        dict["Force3UVs"] = self.Force3UVs
        dict["Force1Group"] = self.Force1Group
        dict["AutoLods"] = self.AutoLods
        return dict
