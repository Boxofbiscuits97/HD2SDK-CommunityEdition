from bpy.types import Operator
from bpy.props import StringProperty
from __init__ import Global_gamepath, Global_ArchiveHashes

# pyright: reportInvalidTypeForm=false

class SearchArchivesOperator(Operator):
    bl_label = "Search Found Archives"
    bl_idname = "helldiver2.search_archives"
    bl_description = "Search from Found Archives"

    SearchField : StringProperty(name="SearchField", default="")
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "SearchField", icon='VIEWZOOM')
        # Update displayed archives
        if self.PrevSearch != self.SearchField:
            self.PrevSearch = self.SearchField

            self.ArchivesToDisplay = []
            for Entry in Global_ArchiveHashes:
                if Entry[1].lower().find(self.SearchField.lower()) != -1:
                    self.ArchivesToDisplay.append([Entry[0], Entry[1]])
    
        if self.SearchField != "" and len(self.ArchivesToDisplay) == 0:
            row = layout.row(); row.label(text="No Archive IDs Found")
            row = layout.row(); row.label(text="Know an ID that's Not Here?")
            row = layout.row(); row.label(text="Make an issue on the github.")
            row = layout.row(); row.label(text="Archive ID and In Game Name")
            row = layout.row(); row.operator("helldiver2.github", icon= 'URL')

        else:
            for Archive in self.ArchivesToDisplay:
                row = layout.row()
                row.label(text=Archive[1], icon='GROUP')
                row.operator("helldiver2.archives_import", icon= 'FILE_NEW', text="").paths_str = Global_gamepath + str(Archive[0])

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        self.PrevSearch = "NONE"
        self.ArchivesToDisplay = []

        wm = context.window_manager
        return wm.invoke_props_dialog(self)
