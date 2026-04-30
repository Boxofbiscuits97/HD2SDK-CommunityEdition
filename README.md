# Helldivers 2 SDK: Community Edition
A Blender addon facilitating the modding of textures, meshes and materials contained within Helldivers 2 archives.

## DISCLAIMER
> [!CAUTION]
> Helldivers 2 is a multiplayer game with anti-cheat measures. While the client-side cosmetic mods that this tool is capable of producing are unlikely to trigger those measures (and has yet to do so in over 40 hours of personal testing), modding of any sort is done entirely at the risk of the end-user and neither ToastedShoes, Kboy, Irastris, GitHub, Nexus Mods, or any other entity can be held responsible for damages that may result from utilizing this tool and/or mods produced with it. <ins>**You have been warned!**</ins>

## What's Different in Community Edition?
Community Edition aims to bring quality of life features to the Helldivers 2 Modding tools. There is much that has been improved with the tools and much that still needs to be. If you have any suggestions please [make an issue](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/issues). Here's what we have so far:

### Features
- **Listed Found Archives** so you don't manually have to select and load Archives by their IDs
- **Easy Naming and Exporting Patches** so that modding is as seamless as possible
- **Descriptions** for all actions in the tool
- **Default Archive Button** for the one that patches should be made from
- **Better Error Handling** for more detailed error messages for when things go wrong
- **Easier Data Copying** for transferring IDs to custom meshes when overriding game models
- **Bulk Scene Importing** for using a text file to import many archives at once
- And **Much More!**

#### [Check Out Our Trello Board!](https://trello.com/b/8RLH5nq6/helldivers-2-sdk-community-edition)
 

### What About the Original Tool?
The developers of the original version of the tool have stated that they are unlikely to update it. Therefore, this community version of it has been made to bring quality of life features and to fix issues with the base version of the tool.

## Installation
Download the [latest release build](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/releases) and install it into [Blender 4.0 to 4.3](https://www.blender.org/download/). 
- Windows is the only officially supported operating system.
- Linux has also been reported to work via Wine.
  - To use on linux without wine, extract the v0.4.1 linux build of [this texconv implementation](https://github.com/matyalatte/Texconv-Custom-DLL/releases/tag/v0.4.1) to the `deps` folder in the addon's zip before installing. 
    - Texconv builds later than v0.4.1 do not work.
    - This texconv build depends on libpng and libjpeg. Your distro probably already installed them.

## Usage
We've taken the time to write a tutorial focused on armor modding which should assist those already moderately familiar with mesh modding and Blender in general. Unfortunately we do not have the means to provide constant support to anyone new to either, but in the event anyone should write a more in-depth tutorial, create a video tutorial, etc, we would be happy to feature it here if it's brought to our attention.

## Documentation
To get a more curated list of specific guides, join the [Community Discord](https://discord.gg/ZwjPaZNwH7). But here's the wiki, the legacy guide, and ID archives.
- [HD2 Modding Wiki](https://boxofbiscuits97.github.io/HD2-Modding-Wiki/)
- [HD2 Legacy Modding Guide](https://docs.google.com/presentation/d/12SRK-LEdf_-m37FAFdKjXsjNidpBmzUeCm9-onlEFaM)
- [Archive IDs Spreadsheet](https://docs.google.com/spreadsheets/d/1oQys_OI5DWou4GeRE3mW56j7BIi4M7KftBIPAl1ULFw)

### Discords
- [Community Discord](https://discord.gg/ZwjPaZNwH7) for support with **Community Edition**
- [Toasted Discord](https://discord.gg/ftSZppf) for the original addon creators

## Development Setup
> [!NOTE]
> This is a tutorial about developing in [VSCode](https://code.visualstudio.com/). If you do not have VSCode, install it [Here](https://code.visualstudio.com/).

### Getting Started
1. Assure the **SDK is uninstalled**
2. Install [Python](https://www.python.org/downloads/) `3.11.9`[^1] or later.
[^1]: Minimum version used by blender 4.0-4.3, so this or anything newer will work
3. [Create a fork of the repository](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/fork)
4. Copy the link to your fork
5. Open VSCode and go to the Source Control Tab
6. Click clone repository and paste the link to your fork
7. Find your Blender Addons folder and choose that as the directory.
   - Example: `C:\Users\<USERNAME>\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons`
8. Open Blender and navigate to preferences and enable the addon
9. Now the project is setup and changes can be made and will reflect each time blender is restarted

### Recommendations for Development
- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) allows VSCode to work properly with Python
    1. Install from VSCode extion page
- [fake-bpy-module](https://github.com/nutti/fake-bpy-module) allows VSCode to properly display scripts hints for Blender Addon
    1. Install the pyton module with `pip install fake-bpy-module` or `pip install fake-bpy-module-latest`
- [Blender Development](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development) allows for hot reload by saving the a current file, and easier live debugging
    1. Install the addon and enable the setting extention setting `Reload addon in Blender when a document is saved`
    2. Open `__init__.py` and then open the command palette (ctrl+shipt+p) and run the command `Blender: Start`
    3. Select the Blender excutible when prompted
        - Example: `C:\Program Files\Blender Foundation\Blender 4.0\blender.exe`
    4. For future just open `__init__.py` and run `Blender: Run Script`
   
> [!NOTE]
> Depending on your specific enviroment, it might be nessisary to add write persmions to the `C:\Program Files\Blender Foundation\Blender 4.0\4.0\python` for the Users local group
    
- [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) allows for static type checking
    1. Install Pylance version `2023.12.1`
        - Blender doesn't fully adhere to the Python standard, and this was the last version that supports Blender's implementaion


### Hot reloading the blender addon
1. In blender go to `Edit > Preferences > Keymap`
2. Unfold the window section
3. Scroll down and `Add New`
4. Unfold the new bind
5. Change `none` to `script.reload`
6. Change the key to a preferred bind
7. Now pressing the bind reloads the addon

## Credits
- Toasted modding team for making the [original version](https://github.com/kboykboy2/io_scene_helldivers2)
- Boxofbiscuits97 for making this community version
