from bpy.types import Menu
from __init__ import Global_SectionHeader, Global_TocManager, MaterialID, MeshID, ParticleID, TexID
from stingray.hashing import GetFriendlyNameFromID

# pyright: reportInvalidTypeForm=false

class WM_MT_button_context(Menu):
    bl_label = "Entry Context Menu"

    def draw_entry_buttons(self, row, Entry):
        if not Entry.IsSelected:
            Global_TocManager.SelectEntries([Entry])

        # Combine entry strings to be passed to operators
        FileIDStr = ""
        TypeIDStr = ""
        for SelectedEntry in Global_TocManager.SelectedEntries:
            FileIDStr += str(SelectedEntry.FileID)+","
            TypeIDStr += str(SelectedEntry.TypeID)+","
        # Get common class
        AreAllMeshes    = True
        AreAllTextures  = True
        AreAllMaterials = True
        AreAllParticles = True
        SingleEntry = True
        NumSelected = len(Global_TocManager.SelectedEntries)
        if len(Global_TocManager.SelectedEntries) > 1:
            SingleEntry = False
        for SelectedEntry in Global_TocManager.SelectedEntries:
            if SelectedEntry.TypeID == MeshID:
                AreAllTextures = False
                AreAllMaterials = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == TexID:
                AreAllMeshes = False
                AreAllMaterials = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == MaterialID:
                AreAllTextures = False
                AreAllMeshes = False
                AreAllParticles = False
            elif SelectedEntry.TypeID == ParticleID:
                AreAllTextures = False
                AreAllMeshes = False
                AreAllMaterials = False
            else:
                AreAllMeshes = False
                AreAllTextures = False
                AreAllMaterials = False
                AreAllParticles = False
        
        RemoveFromPatchName = "Remove From Patch" if SingleEntry else f"Remove {NumSelected} From Patch"
        AddToPatchName = "Add To Patch" if SingleEntry else f"Add {NumSelected} To Patch"
        ImportMeshName = "Import Mesh" if SingleEntry else f"Import {NumSelected} Meshes"
        ImportTextureName = "Import Texture" if SingleEntry else f"Import {NumSelected} Textures"
        ImportMaterialName = "Import Material" if SingleEntry else f"Import {NumSelected} Materials"
        ImportParticleName = "Import Particle" if SingleEntry else f"Import {NumSelected} Particles"
        DumpObjectName = "Export Object Dump" if SingleEntry else f"Export {NumSelected} Object Dumps"
        ImportDumpObjectName = "Import Object Dump" if SingleEntry else f"Import {NumSelected} Object Dumps"
        SaveTextureName = "Save Blender Texture" if SingleEntry else f"Save Blender {NumSelected} Textures"
        SaveMaterialName = "Save Material" if SingleEntry else f"Save {NumSelected} Materials"
        SaveParticleName = "Save Particle" if SingleEntry else f"Save {NumSelected} Particles"
        UndoName = "Undo Modifications" if SingleEntry else f"Undo {NumSelected} Modifications"
        CopyName = "Copy Entry" if SingleEntry else f"Copy {NumSelected} Entries"
        
        # Draw seperator
        row.separator()
        row.label(text=Global_SectionHeader)

        # Draw copy button
        row.separator()
        props = row.operator("helldiver2.archive_copy", icon='COPYDOWN', text=CopyName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        if len(Global_TocManager.CopyBuffer) != 0:
            row.operator("helldiver2.archive_paste", icon='PASTEDOWN', text="Paste "+str(len(Global_TocManager.CopyBuffer))+" Entries")
            row.operator("helldiver2.archive_clearclipboard", icon='TRASH', text="Clear Clipboard")
        if SingleEntry:
            props = row.operator("helldiver2.archive_duplicate", icon='DUPLICATE', text="Duplicate Entry")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text=RemoveFromPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='PLUS', text=AddToPatchName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        # Draw import buttons
        # TODO: Add generic import buttons
        row.separator()
        if AreAllMeshes:
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text=ImportMeshName).object_id = FileIDStr
        elif AreAllTextures:
            row.operator("helldiver2.texture_import", icon='IMPORT', text=ImportTextureName).object_id = FileIDStr
        elif AreAllMaterials:
            row.operator("helldiver2.material_import", icon='IMPORT', text=ImportMaterialName).object_id = FileIDStr
        #elif AreAllParticles:
            #row.operator("helldiver2.archive_particle_import", icon='IMPORT', text=ImportParticleName).object_id = FileIDStr
        # Draw export buttons
        row.separator()

        props = row.operator("helldiver2.archive_object_dump_import", icon='PACKAGE', text=ImportDumpObjectName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        props = row.operator("helldiver2.archive_object_dump_export", icon='PACKAGE', text=DumpObjectName)
        props.object_id     = FileIDStr
        props.object_typeid = TypeIDStr
        # Draw dump import button
        # if AreAllMaterials and SingleEntry: row.operator("helldiver2.archive_object_dump_import", icon="IMPORT", text="Import Raw Dump").object_id = FileIDStr
        # Draw save buttons
        row.separator()
        if AreAllMeshes:
            if SingleEntry:
                row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="Save Mesh").object_id = str(Entry.FileID)
            else:
              row.operator("helldiver2.archive_mesh_batchsave", icon='FILE_BLEND', text=f"Save {NumSelected} Meshes")
        elif AreAllTextures:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text=SaveTextureName).object_id = FileIDStr
            row.separator()
            row.operator("helldiver2.texture_savefromdds", icon='FILE_IMAGE', text=f"Import {NumSelected} DDS Textures").object_id = FileIDStr
            row.operator("helldiver2.texture_savefrompng", icon='FILE_IMAGE', text=f"Import {NumSelected} PNG Textures").object_id = FileIDStr
            row.separator()
            row.operator("helldiver2.texture_batchexport", icon='OUTLINER_OB_IMAGE', text=f"Export {NumSelected} DDS Textures").object_id = FileIDStr
            row.operator("helldiver2.texture_batchexport_png", icon='OUTLINER_OB_IMAGE', text=f"Export {NumSelected} PNG Textures").object_id = FileIDStr
        elif AreAllMaterials:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text=SaveMaterialName).object_id = FileIDStr
            if SingleEntry:
                row.operator("helldiver2.material_set_template", icon='MATSHADERBALL').entry_id = str(Entry.FileID)
                if Entry.LoadedData != None:
                    row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Parent Material Entry ID").text = str(Entry.LoadedData.ParentMaterialID)
        #elif AreAllParticles:
            #row.operator("helldiver2.particle_save", icon='FILE_BLEND', text=SaveParticleName).object_id = FileIDStr
        # Draw copy ID buttons
        if SingleEntry:
            row.separator()
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry ID").text = str(Entry.FileID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry Hex ID").text = str(hex(Entry.FileID))
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Type ID").text  = str(Entry.TypeID)
            row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Friendly Name").text  = GetFriendlyNameFromID(Entry.FileID)
            if Global_TocManager.IsInPatch(Entry):
                props = row.operator("helldiver2.archive_entryrename", icon='TEXT', text="Rename")
                props.object_id     = str(Entry.FileID)
                props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            row.separator()
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text=UndoName)
            props.object_id     = FileIDStr
            props.object_typeid = TypeIDStr

        if SingleEntry:
            row.operator("helldiver2.archive_setfriendlyname", icon='WORDWRAP_ON', text="Set Friendly Name").object_id = str(Entry.FileID)
            
    def draw_material_editor_context_buttons(self, layout, FileID):
        row = layout
        row.separator()
        row.label(text=Global_SectionHeader)
        row.separator()
        row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry ID").text = str(FileID)
        row.operator("helldiver2.copytest", icon='COPY_ID', text="Copy Entry Hex ID").text = str(hex(int(FileID)))
    
    def draw(self, context):
        value = getattr(context, "button_operator", None)
        menuName = type(value).__name__
        if menuName == "HELLDIVER2_OT_archive_entry":
            layout = self.layout
            FileID = getattr(value, "object_id")
            TypeID = getattr(value, "object_typeid")
            self.draw_entry_buttons(layout, Global_TocManager.GetEntry(int(FileID), int(TypeID)))
        elif menuName == "HELLDIVER2_OT_material_texture_entry":
            layout = self.layout
            FileID = getattr(value, "object_id")
            self.draw_material_editor_context_buttons(layout, FileID)


def CustomPropertyContext(self, context):
    layout = self.layout
    layout.separator()
    layout.label(text=Global_SectionHeader)
    layout.separator()
    layout.operator("helldiver2.copy_hex_id", icon='COPY_ID')
    layout.operator("helldiver2.copy_decimal_id", icon='COPY_ID')
    layout.separator()
    layout.operator("helldiver2.copy_custom_properties", icon= 'COPYDOWN')
    layout.operator("helldiver2.paste_custom_properties", icon= 'PASTEDOWN')
    layout.operator("helldiver2.archive_mesh_batchsave", icon= 'FILE_BLEND')
            