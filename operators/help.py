import webbrowser
from bpy.types import Operator

# pyright: reportInvalidTypeForm=false

class HelpOperator(Operator):
    bl_label  = "Help"
    bl_idname = "helldiver2.help"
    bl_description = "Link to Modding Discord"

    def execute(self, context):
        url = "https://discord.gg/helldiversmodding"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

class ArchiveSpreadsheetOperator(Operator):
    bl_label  = "Archive Spreadsheet"
    bl_idname = "helldiver2.archive_spreadsheet"
    bl_description = "Opens Spreadsheet with Indentified Archives"

    def execute(self, context):
        url = "https://docs.google.com/spreadsheets/d/1oQys_OI5DWou4GeRE3mW56j7BIi4M7KftBIPAl1ULFw"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}

class GithubOperator(Operator):
    bl_label  = "Github"
    bl_idname = "helldiver2.github"
    bl_description = "Opens The Github Page"

    def execute(self, context):
        url = "https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}
    
class LatestReleaseOperator(Operator):
    bl_label  = "Update Helldivers 2 SDK"
    bl_idname = "helldiver2.latest_release"
    bl_description = "Opens The Github Page to the latest release"

    def execute(self, context):
        url = "https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/releases/latest"
        webbrowser.open(url, new=0, autoraise=True)
        return{'FINISHED'}
