import bpy

from bpy.types import Operator
from __init__ import PrettyPrint

# pyright: reportInvalidTypeForm=false

stored_custom_properties = {}

class CopyCustomPropertyOperator(Operator):
    bl_label = "Copy HD2 Properties"
    bl_idname = "helldiver2.copy_custom_properties"
    bl_description = "Copies Custom Property Data for Helldivers 2 Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties
        
        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}
        PrettyPrint(selectedObjects)

        obj = context.active_object
        stored_custom_properties.clear()
        for key, value in obj.items():
            if key not in obj.bl_rna.properties:  # Skip built-in properties
                stored_custom_properties[key] = value

        self.report({'INFO'}, f"Copied {len(stored_custom_properties)} custom properties")
        return {'FINISHED'}

class PasteCustomPropertyOperator(Operator):
    bl_label = "Paste HD2 Properties"
    bl_idname = "helldiver2.paste_custom_properties"
    bl_description = "Pastes Custom Property Data for Helldivers 2 Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global stored_custom_properties

        selectedObjects = context.selected_objects
        if len(selectedObjects) == 0:
            self.report({'WARNING'}, "No active object selected")
            return {'CANCELLED'}

        obj = context.active_object
        if not stored_custom_properties:
            self.report({'WARNING'}, "No custom properties to paste")
            return {'CANCELLED'}

        for key, value in stored_custom_properties.items():
            obj[key] = value

        for area in bpy.context.screen.areas:
            area.tag_redraw()

        self.report({'INFO'}, f"Pasted {len(stored_custom_properties)} custom properties")
        return {'FINISHED'}
