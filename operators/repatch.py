from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty

from errorchecking import ArchivesNotLoaded
from repatch import RepatchMeshes

# pyright: reportInvalidTypeForm=false

class MeshFixOperator(Operator, ImportHelper):
    bl_label = "Fix Meshes"
    bl_idname = "helldiver2.meshfixtool"
    bl_description = "Auto-fixes meshes in the currently loaded patch. Warning, this may take some time."

    directory: StringProperty(
        name="Directory",
        description="Choose a directory",
        subtype='DIR_PATH'
    )
    
    filter_folder: BoolProperty(
        default=True,
        options={'HIDDEN'}
    )
    
    use_filter_folder = True
    def execute(self, context):   
        if ArchivesNotLoaded(self):
            return {'CANCELLED'}
        path = self.directory
        output = RepatchMeshes(self, path)
        if output == {'CANCELLED'}: return {'CANCELLED'}
        
        return{'FINISHED'}
    