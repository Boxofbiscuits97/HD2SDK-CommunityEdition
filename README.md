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

## Usage
We've taken the time to write a tutorial focused on armor modding which should assist those already moderately familiar with mesh modding and Blender in general. Unfortunately we do not have the means to provide constant support to anyone new to either, but in the event anyone should write a more in-depth tutorial, create a video tutorial, etc, we would be happy to feature it here if it's brought to our attention.

## Documentation
- [Original Google Docs Tutorial](https://docs.google.com/document/d/1SF7iEekmxoDdf0EsJu1ww9u2Cr8vzHyn2ycZS7JlWl0)
- [Archive IDs Spreadsheet](https://docs.google.com/spreadsheets/d/1oQys_OI5DWou4GeRE3mW56j7BIi4M7KftBIPAl1ULFw)
- [Early Youtube Tutorial for Models](https://youtu.be/jdz-JeLvCY4)

### Discords
- [Community Discord](https://discord.gg/ZwjPaZNwH7) for support with **Community Edition**
- [Toasted Discord](https://discord.gg/ftSZppf) for the original addon creators

## Development Setup
> [!NOTE]
> This is a tutorial about developing in [VSCode](https://code.visualstudio.com/). If you do not have VSCode, install it [Here](https://code.visualstudio.com/).

1. Assure the **SDK is uninstalled**
2. [Create a fork of the repository](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition/fork)
3. Copy the link to your fork
5. Open VSCode and go to the Source Control Tab
6. Click clone repository and paste the link to your fork
7. Find your Blender Addons folder and choose that as the directory.
   - Example: `C:\Users\<USERNAME>\AppData\Roaming\Blender Foundation\Blender\4.0\scripts\addons`
9. Open Blender and navigate to preferences and enable the addon
10. Now the project is setup and changes can be made and will reflect each time blender is restarted

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
