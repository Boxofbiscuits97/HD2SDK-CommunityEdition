from bpy.types import Operator
from bpy.props import StringProperty
from __init__ import ParticleID, PrettyPrint, Global_TocManager
from stingray.archives.tocmanager import IDsFromString

# pyright: reportInvalidTypeForm=false

class SaveStingrayParticleOperator(Operator):
    bl_label  = "Save Particle"
    bl_idname = "helldiver2.particle_save"
    bl_description = "Saves Particle"
    bl_options = {'REGISTER', 'UNDO'} 

    object_id: StringProperty()
    def execute(self, context):
        mode = context.mode
        if mode != 'OBJECT':
            self.report({'ERROR'}, f"You are Not in OBJECT Mode. Current Mode: {mode}")
            return {'CANCELLED'}
        wasSaved = Global_TocManager.Save(int(self.object_id), ParticleID)

        # we can handle below later when we put a particle object into the blender scene

        # if not wasSaved:
        #         for object in bpy.data.objects:
        #             try:
        #                 ID = object["Z_ObjectID"]
        #                 self.report({'ERROR'}, f"Archive for entry being saved is not loaded. Object: {object.name} ID: {ID}")
        #                 return{'CANCELLED'}
        #             except:
        #                 self.report({'ERROR'}, f"Failed to find object with custom property ID. Object: {object.name}")
        #                 return{'CANCELLED'}
        # self.report({'INFO'}, f"Saved Mesh Object ID: {self.object_id}")
        return{'FINISHED'}
    
class ImportStingrayParticleOperator(Operator):
    bl_label = "Import Particle"
    bl_idname = "helldiver2.archive_particle_import"
    bl_description = "Loads Particles into Blender Scene"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        Errors = []
        for EntryID in EntriesIDs:
            if len(EntriesIDs) == 1:
                Global_TocManager.Load(EntryID, ParticleID)
            else:
                try:
                    Global_TocManager.Load(EntryID, ParticleID)
                except Exception as error:
                    Errors.append([EntryID, error])

        if len(Errors) > 0:
            PrettyPrint("\nThese errors occurred while attempting to load particles...", "error")
            idx = 0
            for error in Errors:
                PrettyPrint(f"  Error {idx}: for particle {error[0]}", "error")
                PrettyPrint(f"    {error[1]}\n", "error")
                idx += 1
            raise Exception("One or more particles failed to load")
        return{'FINISHED'}