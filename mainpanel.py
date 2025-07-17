import bpy

from pathlib import Path
from bpy.types import Panel
from __init__ import AnimationID, BoneID, Global_gamepath, Global_searchpath, MaterialID, MeshID, ParticleID, PhysicsID, PrettyPrint, StateMachineID, StringID, TexID, WwiseBankID, WwiseDepID, WwiseMetaDataID, WwiseStreamID, bl_info, Global_TocManager, Global_Foldouts
from displaydata import GetDisplayData
from stingray.hashing import GetArchiveNameFromID, GetFriendlyNameFromID, GetTypeNameFromID, hex_to_decimal
from stingray.material import TextureTypeLookup


class HellDivers2ToolsPanel(Panel):
    bl_label = f"Helldivers 2 SDK: Community Edition v{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
    bl_idname = "SF_PT_Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Modding"

    def draw_material_editor(self, Entry, layout, row):
        if Entry.IsLoaded:
            mat = Entry.LoadedData
            if mat.DEV_ShowEditor:
                for i, t in enumerate(mat.TexIDs):
                    row = layout.row(); row.separator(factor=2.0)
                    ddsPath = mat.DEV_DDSPaths[i]
                    if ddsPath != None: filepath = Path(ddsPath)
                    label = filepath.name if ddsPath != None else str(t)
                    if Entry.MaterialTemplate != None:
                        label = TextureTypeLookup[Entry.MaterialTemplate][i] + ": " + label
                    row.operator("helldiver2.material_texture_entry", icon='FILE_IMAGE', text=label, emboss=False).object_id = str(t)
                    # props = row.operator("helldiver2.material_settex", icon='FILEBROWSER', text="")
                    # props.object_id = str(Entry.FileID)
                    # props.tex_idx = i
                for i, variable in enumerate(mat.ShaderVariables):
                    row = layout.row(); row.separator(factor=2.0)
                    split = row.split(factor=0.5)
                    row = split.column()
                    row.alignment = 'RIGHT'
                    name = variable.ID
                    if variable.name != "": name = variable.name
                    row.label(text=f"{variable.klassName}: {name}", icon='OPTIONS')
                    row = split.column()
                    row.alignment = 'LEFT'
                    sections = len(variable.values)
                    if sections == 3: sections = 4 # add an extra for the color picker
                    row = row.split(factor=1/sections)
                    for j, value in enumerate(variable.values):
                        ShaderVariable = row.operator("helldiver2.material_shader_variable", text=str(round(value, 2)))
                        ShaderVariable.value = value
                        ShaderVariable.object_id = str(Entry.FileID)
                        ShaderVariable.variable_index = i
                        ShaderVariable.value_index = j
                    if len(variable.values) == 3:
                        ColorPicker = row.operator("helldiver2.material_shader_variable_color", text="", icon='EYEDROPPER')
                        ColorPicker.object_id = str(Entry.FileID)
                        ColorPicker.variable_index = i

    def draw_entry_buttons(self, box, row, Entry, PatchOnly):
        if Entry.TypeID == MeshID:
            row.operator("helldiver2.archive_mesh_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.archive_mesh_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
        elif Entry.TypeID == TexID:
            row.operator("helldiver2.texture_saveblendimage", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.texture_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
        elif Entry.TypeID == MaterialID:
            row.operator("helldiver2.material_save", icon='FILE_BLEND', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_import", icon='IMPORT', text="").object_id = str(Entry.FileID)
            row.operator("helldiver2.material_showeditor", icon='MOD_LINEART', text="").object_id = str(Entry.FileID)
            self.draw_material_editor(Entry, box, row)
        #elif Entry.TypeID == ParticleID:
            #row.operator("helldiver2.particle_save", icon='FILE_BLEND', text = "").object_id = str(Entry.FileID)
            #row.operator("helldiver2.archive_particle_import", icon='IMPORT', text = "").object_id = str(Entry.FileID)
        if Global_TocManager.IsInPatch(Entry):
            props = row.operator("helldiver2.archive_removefrompatch", icon='FAKE_USER_ON', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        else:
            props = row.operator("helldiver2.archive_addtopatch", icon='FAKE_USER_OFF', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if Entry.IsModified:
            props = row.operator("helldiver2.archive_undo_mod", icon='TRASH', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)
        if PatchOnly:
            props = row.operator("helldiver2.archive_removefrompatch", icon='X', text="")
            props.object_id     = str(Entry.FileID)
            props.object_typeid = str(Entry.TypeID)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        row = layout.row()
        global OnCorrectBlenderVersion
        if not OnCorrectBlenderVersion:
            row.label(text="Using Incorrect Blender Version!")
            row = layout.row()
            row.label(text="Please Use Blender 4.0.X to 4.3.X")
            return
        
        if bpy.app.version[1] > 0:
            row.label(text="Warning! Soft Supported Blender Version. Issues may Occur.", icon='ERROR')


        row = layout.row()
        row.alignment = 'CENTER'
        global Global_addonUpToDate
        global Global_latestAddonVersion

        if Global_addonUpToDate == None:
            row.label(text="Addon Failed to Check latest Version")
        elif not Global_addonUpToDate:
            row.label(text="Addon is Outdated!")
            row.label(text=f"Latest Version: {Global_latestAddonVersion}")
            row = layout.row()
            row.alignment = 'CENTER'
            row.scale_y = 2
            row.operator("helldiver2.latest_release", icon = 'URL')
            row.separator()

        # Draw Settings, Documentation and Spreadsheet
        mainbox = layout.box()
        row = mainbox.row()
        row.prop(scene.Hd2ToolPanelSettings, "MenuExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.MenuExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text="Settings")
        row.label(icon="SETTINGS")
        
        if scene.Hd2ToolPanelSettings.MenuExpanded:
            row = mainbox.grid_flow(columns=2)
            row = mainbox.row(); row.separator(); row.label(text="Display Types"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ShowExtras")
            row.prop(scene.Hd2ToolPanelSettings, "FriendlyNames")
            row = mainbox.row(); row.separator(); row.label(text="Import Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "ImportMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "ImportLods")
            row.prop(scene.Hd2ToolPanelSettings, "ImportGroup0")
            row.prop(scene.Hd2ToolPanelSettings, "MakeCollections")
            row.prop(scene.Hd2ToolPanelSettings, "ImportCulling")
            row.prop(scene.Hd2ToolPanelSettings, "ImportStatic")
            row.prop(scene.Hd2ToolPanelSettings, "RemoveGoreMeshes")
            row = mainbox.row(); row.separator(); row.label(text="Export Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "Force3UVs")
            row.prop(scene.Hd2ToolPanelSettings, "Force1Group")
            row.prop(scene.Hd2ToolPanelSettings, "AutoLods")
            row = mainbox.row(); row.separator(); row.label(text="Other Options"); box = row.box(); row = box.grid_flow(columns=1)
            row.prop(scene.Hd2ToolPanelSettings, "SaveNonSDKMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "SaveUnsavedOnWrite")
            row.prop(scene.Hd2ToolPanelSettings, "AutoSaveMeshMaterials")
            row.prop(scene.Hd2ToolPanelSettings, "PatchBaseArchiveOnly")
            #row.prop(scene.Hd2ToolPanelSettings, "LegacyWeightNames")

            #Custom Searching tools
            row = mainbox.row(); row.separator(); row.label(text="Special Tools"); box = row.box(); row = box.grid_flow(columns=1)
            # Draw Bulk Loader Extras
            row.prop(scene.Hd2ToolPanelSettings, "EnableTools")
            if scene.Hd2ToolPanelSettings.EnableTools:
                row = mainbox.row(); box = row.box(); row = box.grid_flow(columns=1)
                #row.label()
                row.label(text="WARNING! Developer Tools, Please Know What You Are Doing!")
                row.prop(scene.Hd2ToolPanelSettings, "UnloadEmptyArchives")
                row.prop(scene.Hd2ToolPanelSettings, "UnloadPatches")
                row.prop(scene.Hd2ToolPanelSettings, "LoadFoundArchives")
                #row.prop(scene.Hd2ToolPanelSettings, "DeleteOnLoadArchive")
                col = box.grid_flow(columns=2)
                col.operator("helldiver2.bulk_load", icon= 'IMPORT', text="Bulk Load")
                col.operator("helldiver2.search_by_entry", icon= 'VIEWZOOM')
                #row = box.grid_flow(columns=1)
                #row.operator("helldiver2.meshfixtool", icon='MODIFIER')
                search = mainbox.row()
                search.label(text=Global_searchpath)
                search.operator("helldiver2.change_searchpath", icon='FILEBROWSER')
                mainbox.separator()
            row = mainbox.row()
            row.label(text=Global_gamepath)
            row.operator("helldiver2.change_filepath", icon='FILEBROWSER')
            mainbox.separator()

        global Global_gamepathIsValid
        if not Global_gamepathIsValid:
            row = layout.row()
            row.label(text="Current Selected game filepath is not valid!")
            row = layout.row()
            row.label(text="Please select your game directory in the settings!")
            return

        # Draw Archive Import/Export Buttons
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.help", icon='HELP', text="Discord")
        row.operator("helldiver2.archive_spreadsheet", icon='INFO', text="Archive IDs")
        row.operator("helldiver2.github", icon='URL', text= "")
        row = layout.row(); row = layout.row()
        row.operator("helldiver2.archive_import_default", icon= 'SOLO_ON', text="")
        row.operator("helldiver2.search_archives", icon= 'VIEWZOOM')
        row.operator("helldiver2.archive_unloadall", icon= 'FILE_REFRESH', text="")
        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "LoadedArchives", text="Archives")
        if scene.Hd2ToolPanelSettings.EnableTools:
            row.scale_x = 0.33
            ArchiveNum = "0/0"
            if Global_TocManager.ActiveArchive != None:
                Archiveindex = Global_TocManager.LoadedArchives.index(Global_TocManager.ActiveArchive) + 1
                Archiveslength = len(Global_TocManager.LoadedArchives)
                ArchiveNum = f"{Archiveindex}/{Archiveslength}"
            row.operator("helldiver2.next_archive", icon= 'RIGHTARROW', text=ArchiveNum)
            row.scale_x = 1
        row.operator("helldiver2.archive_import", icon= 'FILEBROWSER', text= "").is_patch = False
        row = layout.row()
        if len(Global_TocManager.LoadedArchives) > 0:
            Global_TocManager.SetActiveByName(scene.Hd2ToolPanelSettings.LoadedArchives)


        # Draw Patch Stuff
        row = layout.row(); row = layout.row()

        row.operator("helldiver2.archive_createpatch", icon= 'COLLECTION_NEW', text="New Patch")
        row.operator("helldiver2.archive_export", icon= 'DISC', text="Write Patch")
        row.operator("helldiver2.export_patch", icon= 'EXPORT')
        row.operator("helldiver2.patches_unloadall", icon= 'FILE_REFRESH', text="")

        row = layout.row()
        row.prop(scene.Hd2ToolPanelSettings, "Patches", text="Patches")
        if len(Global_TocManager.Patches) > 0:
            Global_TocManager.SetActivePatchByName(scene.Hd2ToolPanelSettings.Patches)
        row.operator("helldiver2.rename_patch", icon='GREASEPENCIL', text="")
        row.operator("helldiver2.archive_import", icon= 'FILEBROWSER', text="").is_patch = True

        # Draw Archive Contents
        row = layout.row(); row = layout.row()
        title = "No Archive Loaded"
        if Global_TocManager.ActiveArchive != None:
            ArchiveID = Global_TocManager.ActiveArchive.Name
            name = GetArchiveNameFromID(ArchiveID)
            title = f"{name}    ID: {ArchiveID}"
        if Global_TocManager.ActivePatch != None and scene.Hd2ToolPanelSettings.PatchOnly:
            name = Global_TocManager.ActivePatch.Name
            title = f"Patch: {name}    File: {Global_TocManager.ActivePatch.Name}"
        row.prop(scene.Hd2ToolPanelSettings, "ContentsExpanded",
            icon="DOWNARROW_HLT" if scene.Hd2ToolPanelSettings.ContentsExpanded else "RIGHTARROW",
            icon_only=True, emboss=False, text=title)
        row.prop(scene.Hd2ToolPanelSettings, "PatchOnly", text="")
        row.operator("helldiver2.copy_archive_id", icon='COPY_ID', text="")
        row.operator("helldiver2.archive_object_dump_import_by_id", icon='PACKAGE', text="")


        # Get Display Data
        DisplayData = GetDisplayData()
        DisplayTocEntries = DisplayData[0]
        DisplayTocTypes   = DisplayData[1]

        # Draw Contents
        NewFriendlyNames = []
        NewFriendlyIDs = []
        if scene.Hd2ToolPanelSettings.ContentsExpanded:
            if len(DisplayTocEntries) == 0: return

            # Draw Search Bar
            row = layout.row(); row = layout.row()
            row.prop(scene.Hd2ToolPanelSettings, "SearchField", icon='VIEWZOOM', text="")

            DrawChain = []
            for Type in DisplayTocTypes:
                # check if there is any entry of this type that matches search field
                # TODO: should probably make a better way to do this
                bFound = False
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    if Entry.TypeID == Type.TypeID:
                        searchTerm = str(scene.Hd2ToolPanelSettings.SearchField)
                        if searchTerm.startswith("0x"):
                            searchTerm = str(hex_to_decimal(searchTerm))
                        if str(Entry.FileID).find(searchTerm) != -1:
                            bFound = True
                if not bFound: continue

                # Get Type Icon
                type_icon = 'FILE'
                show = None
                showExtras = scene.Hd2ToolPanelSettings.ShowExtras
                EntryNum = 0
                global Global_Foldouts
                if Type.TypeID == MeshID:
                    type_icon = 'FILE_3D'
                elif Type.TypeID == TexID:
                    type_icon = 'FILE_IMAGE'
                elif Type.TypeID == MaterialID:
                    type_icon = 'MATERIAL' 
                elif Type.TypeID == ParticleID: 
                    type_icon = 'PARTICLES'
                elif showExtras:
                    if Type.TypeID == BoneID: type_icon = 'BONE_DATA'
                    elif Type.TypeID == WwiseBankID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseDepID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseStreamID:  type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == WwiseMetaDataID: type_icon = 'OUTLINER_DATA_SPEAKER'
                    elif Type.TypeID == AnimationID: type_icon = 'ARMATURE_DATA'
                    elif Type.TypeID == StateMachineID: type_icon = 'DRIVER'
                    elif Type.TypeID == StringID: type_icon = 'WORDWRAP_ON'
                    elif Type.TypeID == PhysicsID: type_icon = 'PHYSICS'
                else:
                    continue
                
                for section in Global_Foldouts:
                    if section[0] == str(Type.TypeID):
                        show = section[1]
                        break
                if show == None:
                    fold = False
                    if Type.TypeID == MaterialID or Type.TypeID == TexID or Type.TypeID == MeshID: fold = True
                    foldout = [str(Type.TypeID), fold]
                    Global_Foldouts.append(foldout)
                    PrettyPrint(f"Adding Foldout ID: {foldout}")
                    

                fold_icon = "DOWNARROW_HLT" if show else "RIGHTARROW"

                # Draw Type Header
                box = layout.box(); row = box.row()
                typeName = GetTypeNameFromID(Type.TypeID)
                split = row.split()
                
                sub = split.row(align=True)
                sub.operator("helldiver2.collapse_section", text=f"{typeName}: {str(Type.TypeID)}", icon=fold_icon, emboss=False).type = str(Type.TypeID)

                # Skip drawling entries if section hidden
                if not show: 
                    sub.label(icon=type_icon)
                    continue
                
                #sub.operator("helldiver2.import_type", icon='IMPORT', text="").object_typeid = str(Type.TypeID)
                sub.operator("helldiver2.select_type", icon='RESTRICT_SELECT_OFF', text="").object_typeid = str(Type.TypeID)
                # Draw Add Material Button
                
                if typeName == "material": sub.operator("helldiver2.material_add", icon='FILE_NEW', text="")

                # Draw Archive Entries
                col = box.column()
                for EntryInfo in DisplayTocEntries:
                    Entry = EntryInfo[0]
                    PatchOnly = EntryInfo[1]
                    # Exclude entries that should not be drawn
                    if Entry.TypeID != Type.TypeID: continue
                    searchTerm = str(scene.Hd2ToolPanelSettings.SearchField)
                    if searchTerm.startswith("0x"):
                        searchTerm = str(hex_to_decimal(searchTerm))
                    if str(Entry.FileID).find(searchTerm) == -1: continue
                    # Deal with friendly names
                    FriendlyName = str(Entry.FileID)
                    if scene.Hd2ToolPanelSettings.FriendlyNames:
                        if len(Global_TocManager.SavedFriendlyNameIDs) > len(DrawChain) and Global_TocManager.SavedFriendlyNameIDs[len(DrawChain)] == Entry.FileID:
                            FriendlyName = Global_TocManager.SavedFriendlyNames[len(DrawChain)]
                        else:
                            try:
                                FriendlyName = Global_TocManager.SavedFriendlyNames[Global_TocManager.SavedFriendlyNameIDs.index(Entry.FileID)]
                                NewFriendlyNames.append(FriendlyName)
                                NewFriendlyIDs.append(Entry.FileID)
                            except:
                                FriendlyName = GetFriendlyNameFromID(Entry.FileID)
                                NewFriendlyNames.append(FriendlyName)
                                NewFriendlyIDs.append(Entry.FileID)


                    # Draw Entry
                    PatchEntry = Global_TocManager.GetEntry(int(Entry.FileID), int(Entry.TypeID))
                    PatchEntry.DEV_DrawIndex = len(DrawChain)
                    
                    previous_type_icon = type_icon
                    if PatchEntry.MaterialTemplate != None:
                        type_icon = "NODE_MATERIAL"

                    row = col.row(align=True); row.separator()
                    props = row.operator("helldiver2.archive_entry", icon=type_icon, text=FriendlyName, emboss=PatchEntry.IsSelected, depress=PatchEntry.IsSelected)
                    type_icon = previous_type_icon
                    props.object_id     = str(Entry.FileID)
                    props.object_typeid = str(Entry.TypeID)
                    # Draw Entry Buttons
                    self.draw_entry_buttons(col, row, PatchEntry, PatchOnly)
                    # Update Draw Chain
                    DrawChain.append(PatchEntry)
            Global_TocManager.DrawChain = DrawChain
        if scene.Hd2ToolPanelSettings.FriendlyNames:  
            Global_TocManager.SavedFriendlyNames = NewFriendlyNames
            Global_TocManager.SavedFriendlyNameIDs = NewFriendlyIDs