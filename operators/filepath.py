import bpy

from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from config import UpdateConfig
from __init__ import PrettyPrint

# pyright: reportInvalidTypeForm=false

class ChangeFilepathOperator(Operator, ImportHelper):
    bl_label = "Change Filepath"
    bl_idname = "helldiver2.change_filepath"
    bl_description = "Change the game's data folder directory"
    #filename_ext = "."
    use_filter_folder = True

    filter_glob: StringProperty(options={'HIDDEN'}, default='')

    def __init__(self):
        global Global_gamepath
        self.filepath = bpy.path.abspath(Global_gamepath)
        
    def execute(self, context):
        global Global_gamepath
        global Global_gamepathIsValid
        filepath = self.filepath
        steamapps = "steamapps"
        if steamapps in filepath:
            filepath = f"{filepath.partition(steamapps)[0]}steamapps\common\Helldivers 2\data\ "[:-1]
        else:
            self.report({'ERROR'}, f"Could not find steamapps folder in filepath: {filepath}")
            return{'CANCELLED'}
        Global_gamepath = filepath
        UpdateConfig()
        PrettyPrint(f"Changed Game File Path: {Global_gamepath}")
        Global_gamepathIsValid = True
        return{'FINISHED'}
    
class ChangeSearchpathOperator(Operator, ImportHelper):
    bl_label = "Change Searchpath"
    bl_idname = "helldiver2.change_searchpath"
    bl_description = "Change the output directory for searching by entry ID"
    use_filter_folder = True

    filter_glob: StringProperty(options={'HIDDEN'}, default='')

    def __init__(self):
        global Global_searchpath
        self.filepath = bpy.path.abspath(Global_searchpath)
        
    def execute(self, context):
        global Global_searchpath
        Global_searchpath = self.filepath
        UpdateConfig()
        PrettyPrint(f"Changed Game Search Path: {Global_searchpath}")
        return{'FINISHED'}