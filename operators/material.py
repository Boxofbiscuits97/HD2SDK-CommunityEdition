import os
import bpy

from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, IntProperty
from __init__ import Global_materialpath, MaterialID, PrettyPrint, Global_TocManager
from errorchecking import PatchesNotLoaded
from stingray.archives.tocentry import TocEntry
from stingray.archives.tocmanager import IDsFromString
from stingray.hashing import RandomHash16
from stingray.material import Global_Materials
from bpy_extras.io_utils import ImportHelper

# pyright: reportInvalidTypeForm=false

class SaveMaterialOperator(Operator):
    bl_label = "Save Material"
    bl_idname = "helldiver2.material_save"
    bl_description = "Saves Material"

    object_id: StringProperty()
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Save(int(EntryID), MaterialID)
        return{'FINISHED'}

class ImportMaterialOperator(Operator):
    bl_label = "Import Material"
    bl_idname = "helldiver2.material_import"
    bl_description = "Loads Materials into Blender Project"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), MaterialID)
        return{'FINISHED'}

class AddMaterialOperator(Operator):
    bl_label = "Add Material"
    bl_idname = "helldiver2.material_add"
    bl_description = "Adds a New Material to Current Active Patch"

    global Global_Materials
    selected_material: EnumProperty(items=Global_Materials, name="Template", default=0)

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        
        CreateModdedMaterial(self.selected_material)

        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
class SetMaterialTemplateOperator(Operator):
    bl_label = "Set Template"
    bl_idname = "helldiver2.material_set_template"
    bl_description = "Sets the material to a modded material template"
    
    global Global_Materials
    selected_material: EnumProperty(items=Global_Materials, name="Template", default=0)

    entry_id: StringProperty()

    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        
        PrettyPrint(f"Found: {self.entry_id}")
            
        Entry = Global_TocManager.GetEntry(int(self.entry_id), MaterialID)
        if not Entry:
            raise Exception(f"Could not find entry at ID: {self.entry_id}")

        Entry.MaterialTemplate = self.selected_material
        Entry.Load(True)
        
        PrettyPrint(f"Finished Set Template: {self.selected_material}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def CreateModdedMaterial(template, ID=None):
    path = f"{Global_materialpath}\\{template}.material"
    if not os.path.exists(path):
        raise Exception(f"Selected material template: {template} does not exist")

    Entry = TocEntry()
    if ID == None:
        Entry.FileID = RandomHash16()
        PrettyPrint(f"File ID is now: {Entry.FileID}")
    else:
        Entry.FileID = ID
        PrettyPrint(f"Found pre-existing file ID: {ID}")

    Entry.TypeID = MaterialID
    Entry.MaterialTemplate = template
    Entry.IsCreated = True
    with open(path, 'r+b') as f:
        data = f.read()
    Entry.TocData_OLD   = data
    Entry.TocData       = data

    Global_TocManager.AddNewEntryToPatch(Entry)
        
    EntriesIDs = IDsFromString(str(Entry.FileID))
    for EntryID in EntriesIDs:
        Global_TocManager.Load(int(EntryID), MaterialID)

class ShowMaterialEditorOperator(Operator):
    bl_label = "Show Material Editor"
    bl_idname = "helldiver2.material_showeditor"
    bl_description = "Show List of Textures in Material"

    object_id: StringProperty()
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if not Entry.IsLoaded: Entry.Load(False, False)
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                mat.DEV_ShowEditor = False
            else:
                mat.DEV_ShowEditor = True
        return{'FINISHED'}

class SetMaterialTexture(Operator, ImportHelper):
    bl_label = "Set Material Texture"
    bl_idname = "helldiver2.material_settex"

    filename_ext = ".dds"

    filter_glob: StringProperty(default="*.dds", options={'HIDDEN'})

    object_id: StringProperty(options={"HIDDEN"})
    tex_idx: IntProperty(options={"HIDDEN"})

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), MaterialID)
        if Entry != None:
            if Entry.IsLoaded:
                Entry.LoadedData.DEV_DDSPaths[self.tex_idx] = self.filepath
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()
        
        return{'FINISHED'}

class MaterialTextureEntryOperator(Operator):
    bl_label  = "Texture Entry"
    bl_idname = "helldiver2.material_texture_entry"

    object_id: StringProperty()
    object_typeid: StringProperty()
    def execute(self, context):
        return{'FINISHED'}

    def invoke(self, context, event):
        return {'FINISHED'}
    
class MaterialShaderVariableEntryOperator(Operator):
    bl_label = "Shader Variable"
    bl_idname = "helldiver2.material_shader_variable"
    bl_description = "Material Shader Variable"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    value_index: bpy.props.IntProperty()
    value: bpy.props.FloatProperty(
        name="Variable Value",
        description="Enter a floating point number"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "value")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            Entry.LoadedData.ShaderVariables[self.variable_index].values[self.value_index] = self.value
            PrettyPrint(f"Set value to: {self.value} at variable: {self.variable_index} value: {self.value_index} for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class MaterialShaderVariableColorEntryOperator(Operator):
    bl_label = "Color Picker"
    bl_idname = "helldiver2.material_shader_variable_color"
    bl_description = "Material Shader Variable Color"

    object_id: StringProperty()
    variable_index: bpy.props.IntProperty()
    color: bpy.props.FloatVectorProperty(
                name=f"Color",
                subtype="COLOR",
                size=3,
                min=0.0,
                max=1.0,
                default=(1.0, 1.0, 1.0)
            )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "color")

    def execute(self, context):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                Entry.LoadedData.ShaderVariables[self.variable_index].values[idx] = self.color[idx]
            PrettyPrint(f"Set color to: {self.color}for material ID: {self.object_id}")
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return {'FINISHED'}
    
    def invoke(self, context, event):
        Entry = Global_TocManager.GetEntry(self.object_id, MaterialID)
        if Entry:
            for idx in range(3):
                self.color[idx] = Entry.LoadedData.ShaderVariables[self.variable_index].values[idx]
        else:
            self.report({'ERROR'}, f"Could not find entry for ID: {self.object_id}")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)
