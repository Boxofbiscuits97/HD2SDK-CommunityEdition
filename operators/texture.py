import os
import subprocess
import tempfile
import bpy

from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty
from __init__ import Global_backslash, Global_texconvpath, PrettyPrint, Global_TocManager, TexID
from bpy_extras.io_utils import ImportHelper, ExportHelper

from errorchecking import PatchesNotLoaded
from memoryStream import MemoryStream
from stingray.archives.tocmanager import EntriesFromString, IDsFromString
from stingray.texture import BlendImageToStingrayTexture

# pyright: reportInvalidTypeForm=false

class SaveTextureFromBlendImageOperator(Operator):
    bl_label = "Save Texture"
    bl_idname = "helldiver2.texture_saveblendimage"
    bl_description = "Saves Texture"

    object_id: StringProperty()
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        Entries = EntriesFromString(self.object_id, TexID)
        for Entry in Entries:
            if Entry != None:
                if not Entry.IsLoaded: Entry.Load()
                try:
                    BlendImageToStingrayTexture(bpy.data.images[str(self.object_id)], Entry.LoadedData)
                except:
                    PrettyPrint("No blend texture was found for saving, using original", "warn"); pass
            Global_TocManager.Save(Entry.FileID, TexID)
        return{'FINISHED'}

# import texture from archive button
class ImportTextureOperator(Operator):
    bl_label = "Import Texture"
    bl_idname = "helldiver2.texture_import"
    bl_description = "Loads Texture into Blender Project"

    object_id: StringProperty()
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Global_TocManager.Load(int(EntryID), TexID)
        return{'FINISHED'}

# export texture to file
class ExportTextureOperator(Operator, ExportHelper):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_export"
    bl_description = "Export Texture to a Desired File Location"
    filename_ext = ".dds"

    filter_glob: StringProperty(default='*.dds', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            data = Entry.Load(False, False)
            with open(self.filepath, 'w+b') as f:
                f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}
    
    def invoke(self, context, _event):
        if not self.filepath:
            blend_filepath = context.blend_data.filepath
            if not blend_filepath:
                blend_filepath = self.object_id
            else:
                blend_filepath = os.path.splitext(blend_filepath)[0]

            self.filepath = blend_filepath + self.filename_ext

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class ExportTexturePNGOperator(Operator, ExportHelper):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_export_png"
    bl_description = "Export Texture to a Desired File Location"
    filename_ext = ".png"

    filter_glob: StringProperty(default='*.png', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        Global_TocManager.Load(int(self.object_id), TexID)
        Entry = Global_TocManager.GetEntry(int(self.object_id), TexID)
        if Entry != None:
            tempdir = tempfile.gettempdir()
            for i in range(Entry.LoadedData.ArraySize):
                filename = self.filepath.split(Global_backslash)[-1]
                directory = self.filepath.replace(filename, "")
                filename = filename.replace(".png", "")
                layer = "" if Entry.LoadedData.ArraySize == 1 else f"_layer{i}"
                dds_path = f"{tempdir}\\{filename}{layer}.dds"
                with open(dds_path, 'w+b') as f:
                    if Entry.LoadedData.ArraySize == 1:
                        f.write(Entry.LoadedData.ToDDS())
                    else:
                        f.write(Entry.LoadedData.ToDDSArray()[i])
                subprocess.run([Global_texconvpath, "-y", "-o", directory, "-ft", "png", "-f", "R8G8B8A8_UNORM", "-sepalpha", "-alpha", dds_path])
                if os.path.isfile(dds_path):
                    self.report({'INFO'}, f"Saved PNG Texture to: {dds_path}")
                else:
                    self.report({'ERROR'}, f"Failed to Save Texture: {dds_path}")
        return{'FINISHED'}
    
    def invoke(self, context, event):
        blend_filepath = context.blend_data.filepath
        filename = f"{self.object_id}.png"
        self.filepath = blend_filepath + filename
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# batch export texture to file
class BatchExportTextureOperator(Operator):
    bl_label = "Export Textures"
    bl_idname = "helldiver2.texture_batchexport"
    bl_description = "Export Textures to a Desired File Location"
    filename_ext = ".dds"

    directory: StringProperty(name="Outdir Path",description="dds output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            Entry = Global_TocManager.GetEntry(EntryID, TexID)
            if Entry != None:
                data = Entry.Load(False, False)
                with open(self.directory + str(Entry.FileID)+".dds", 'w+b') as f:
                    f.write(Entry.LoadedData.ToDDS())
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class BatchExportTexturePNGOperator(Operator):
    bl_label = "Export Texture"
    bl_idname = "helldiver2.texture_batchexport_png"
    bl_description = "Export Textures to a Desired File Location"
    filename_ext = ".png"

    directory: StringProperty(name="Outdir Path",description="png output dir")
    filter_folder: BoolProperty(default=True,options={"HIDDEN"})

    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        EntriesIDs = IDsFromString(self.object_id)
        exportedfiles = 0
        for EntryID in EntriesIDs:
            Global_TocManager.Load(EntryID, TexID)
            Entry = Global_TocManager.GetEntry(EntryID, TexID)
            if Entry != None:
                tempdir = tempfile.gettempdir()
                dds_path = f"{tempdir}\\{EntryID}.dds"
                with open(dds_path, 'w+b') as f:
                    f.write(Entry.LoadedData.ToDDS())
                subprocess.run([Global_texconvpath, "-y", "-o", self.directory, "-ft", "png", "-f", "R8G8B8A8_UNORM", "-alpha", dds_path])
                filepath = f"{self.directory}\\{EntryID}.png"
                if os.path.isfile(filepath):
                    exportedfiles += 1
                else:
                    self.report({'ERROR'}, f"Failed to save texture as PNG: {filepath}")
        self.report({'INFO'}, f"Exported {exportedfiles} PNG Files To: {self.directory}")
        return{'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# import texture from archive button
class SaveTextureFromDDSOperator(Operator, ImportHelper):
    bl_label = "Import DDS"
    bl_idname = "helldiver2.texture_savefromdds"
    bl_description = "Override Current Texture with a Selected DDS File"

    filter_glob: StringProperty(default='*.dds', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            SaveImageDDS(self.filepath, EntryID)
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return{'FINISHED'}


class SaveTextureFromPNGOperator(Operator, ImportHelper):
    bl_label = "Import PNG"
    bl_idname = "helldiver2.texture_savefrompng"
    bl_description = "Override Current Texture with a Selected PNG File"

    filter_glob: StringProperty(default='*.png', options={'HIDDEN'})
    object_id: StringProperty(options={"HIDDEN"})
    def execute(self, context):
        if PatchesNotLoaded(self):
            return {'CANCELLED'}
        EntriesIDs = IDsFromString(self.object_id)
        for EntryID in EntriesIDs:
            SaveImagePNG(self.filepath, EntryID)
        
        # Redraw
        for area in context.screen.areas:
            if area.type == "VIEW_3D": area.tag_redraw()

        return{'FINISHED'}

def SaveImagePNG(filepath, object_id):
    Entry = Global_TocManager.GetEntry(int(object_id), TexID)
    if Entry != None:
        if len(filepath) > 1:
            # get texture data
            Entry.Load()
            StingrayTex = Entry.LoadedData
            tempdir = tempfile.gettempdir()
            PrettyPrint(filepath)
            PrettyPrint(StingrayTex.Format)
            subprocess.run([Global_texconvpath, "-y", "-o", tempdir, "-ft", "dds", "-dx10", "-f", StingrayTex.Format, "-sepalpha", "-alpha", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            nameIndex = filepath.rfind("\.".strip(".")) + 1
            fileName = filepath[nameIndex:].replace(".png", ".dds")
            dds_path = f"{tempdir}\\{fileName}"
            PrettyPrint(dds_path)
            if not os.path.exists(dds_path):
                raise Exception(f"Failed to convert to dds texture for: {dds_path}")
            with open(dds_path, 'r+b') as f:
                StingrayTex.FromDDS(f.read())
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture to entry
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)

            Global_TocManager.Save(int(object_id), TexID)

def SaveImageDDS(filepath, object_id):
    Entry = Global_TocManager.GetEntry(int(object_id), TexID)
    if Entry != None:
        if len(filepath) > 1:
            PrettyPrint(f"Saving image DDS: {filepath} to ID: {object_id}")
            # get texture data
            Entry.Load()
            StingrayTex = Entry.LoadedData
            with open(filepath, 'r+b') as f:
                StingrayTex.FromDDS(f.read())
            Toc = MemoryStream(IOMode="write")
            Gpu = MemoryStream(IOMode="write")
            Stream = MemoryStream(IOMode="write")
            StingrayTex.Serialize(Toc, Gpu, Stream)
            # add texture to entry
            Entry.SetData(Toc.Data, Gpu.Data, Stream.Data, False)

            Global_TocManager.Save(int(object_id), TexID)
