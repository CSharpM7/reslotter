# [ReslotterGUI](https://github.com/CSharpM7/reslotter)
**Version 4.0**

![r](https://i.imgur.com/NWFBCcQ.png)

A GUI tool for reslotting mods. Requires python 3.9+. This will reslot anything under the folders `fighter`,`sound`,`ui`, and `effects` (if applicable)

You'll need to download a 

Courtesy of CoolSonicKirby and WuBoy, this will also generate the proper config for you to use! Once the reslotter is finished, it should be ready to be added directly to your switch. If you need more slots, you can manually type in the dropdown box the slot you need (ie `+c21`), or you can edit the `reslotterGUI.py` script at line 18. It should be a variable called `root.maxSlots`, which is defaulted at 11.

Original reslotter written by [Blujay](https://github.com/blu-dev) and maintained by [Jozz](https://github.com/jozz024/ssbu-skin-reslotter)

## Prerequisites
(You dont have to have Python installed, simply go to the releases tab for the exes. If you do have Python installed, you will need 3.9+)
- `Hashes_all.txt` from [here](https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all). Download and place it in the ResoltterGUI Directory.
- (For Mod Developers) `ultimate_tex_cli.exe` by @ScanMountGoat . Latest can be found [here](https://github.com/ScanMountGoat/ultimate_tex/releases/latest). Download and place it in the ResoltterGUI Directory.

## Installation

You may run this program's .py file if you have python installed. Otherwise, I've provided a `.exe` version in the [releases tab](https://github.com/CSharpM7/reslotter/releases/latest), though the `.py` version will always be the most up-to-date version.

## Usage

You can run the `.py` or `.exe` folder using `reslotterGUI.py/exe [mod folder]`. The mod folder argument is optional. You can also drag and drop your mod folder ontop of the application.

Select the root of your mod's folder. You'll be presented with the GUI at the top of this README. You can also hover over most of the labels for additional tool tips. It will populate the list with all the alts in that mod. Copy to New Folder will create a new folder with the new alts in the title (Shiny Blue DK (c03)). Exclude Blank Targets is for packs with multiple alts in it. Leave it on to only have the changed alts in the new folder. Leave it unchecked to bring all alts into the new folder, changed or not. 

### Changing Slots
Navigate to which skin corresponds to the source of your mod (if you have Shinny Blue DK on the 3rd alt, it should be `c02`). Under the dropdown menu, select its new destination (ie `c03` for the fourth, blue alt).  Hit Change Slots, and the relevant files/folders will be changed, as well as a new `config.json` will be added.

### Adding New Slots
Before you do this, read [this tutorial](https://docs.google.com/document/d/15N_I2_sTfGjWhy7NiBnw6gW0t8mYeRfsXBAfYshhNR4/edit?usp=drivesdk) by Blaze and [this tutorial](https://docs.google.com/document/d/1JQHDcpozZYNbO2IAzgG7GrBWC5OJc1_xfXmMw55pGhM/edit?usp=drivesdk) by WuBoy.

When you set the new slot to anything beyond `c07` (denoted with a + prefix), you are adding slots to the game! This is a slightly more involved process than just changing base slots, so you will need to go to File->Slot Addition Guide to understand how this process works. 

"Share From" is the slot that the mod is based on. For example, a Robin mod on slot `c05` would set Share From to `c00` as both are male alts. A Sephiroth mod on slot `c07` should use `c06` for the shirtless variant. This program will do its best to set this to the optimal slot for each fighter, but you can manually set it if you want to.

### Setting New Max Slots for the Character Select Screen
New Max Slots will create a `ui_chara_db.prcxml` file in `ui/param/database` which is used to increase the number of slots available in the Character Select Screen after you hit "Change Slots" or "Reconfig". `ui_chara_db.prc` is the file used to control how many slots can be selected on the character select screen, while the .`prcxml` version patches the file in game ([please read this if you are confused about prc and prcxmls files](https://github.com/Raytwo/ARCropolis/wiki/Param-Patching)). You'll want to set this to the highest slot number in your modpack+1 (if I have Shiny Blue DK on `c10`, I would set the max slots to 11) **It is recommended that you only have one of these files per fighter. So make sure your Shiny Blue DK and Shiny Pink DK both don't have a `ui_chara_db.prcxml`**

### Generating Configs
Similar to [LazyConfig](https://github.com/CSharpM7/SharpSmashSuite/tree/main/LazyConfig), this will create a `config.json` file in your mod folder without changing any of the files, useful for when you are creating a mod that uses additional slots, or if you accidentally deleted the `config.json` file. Click on "Rewrite Config" or "Create Config" to create a `config.json` without reslotting anything

### Generating Configs For All
If you have an extremely large mod pack, this tool **might** be able to help! This is still experimental, but if you select "all" from the fighter dropdown list, and hit Rewrite/Create Config, it'll go through every fighter and all their alts and create one big config for that folder.

## Known Issues
- Only one fighter at a time can be reslotted, so if you have Marth and Mario in a mod pack, you can only reslot Marth **OR** Mario
 - Aegis (Pyra and Mythra), Ice Climbers (Popo and Nana), and Pokemon Trainer (Trainer and their Pokemon) will all be reslotted together. So if you have a Pyra and Mythra skin on c00, they'll both migrate to c08 or whichever slot you are targeting
- Added slots mostly work, but for the ones that don't: try hitting rewrite config on the reslotted folder, or using the [original website](https://coolsonickirby.com/arc/dir-info-with-files.html) to regenerate a config
- Not all fighter's one-slotted effects work
- Not all fighter's `New Max Slots` option have been tested

# @CrusherD2's additional tools

> [!WARNING]  
> The following tools are intended for mod developers only, if you're just using this to change the slot of mods that you have downloaded, turn around for here be dragons for ye.

These tools help optimize mod folders and configs for moveset modders.
## Moveset Optimizer
![Moveset](https://github.com/user-attachments/assets/f7339bac-b28e-4e29-9cef-259da0a48589)

A powerful utility that identifies duplicate files between character slots, moves them to a junk folder, and updates your mod's config.json to maintain proper functionality while reducing file size.

### Basic Usage

1. **Launch the Tool**: Run `moveset_optimizer_improved.py [mod_directory]`
2. **Wait for Analysis**: The tool will scan all slots and identify duplicate files
3. **Review Results**: Check the output to see how many files were moved to the junk folder

### Command Line Options

```
python moveset_optimizer_improved.py [mod_directory] [options]

Options:
  --fighter FIGHTER     Fighter name (optional, will be auto-detected)
  --main-slot SLOT      Main slot to use as reference (optional)
  --compare-slot SLOT   Specific slot to compare with the main
  --simulate            Simulate optimization without making changes
  --debug               Show detailed debug messages
  --list-slots          Show available slots in the mod
```

### Key Features

- **Automatic Detection**: Identifies fighter and available slots
- **Smart Comparison**: Finds duplicate files between slots, including:
  - Model files (.numdlb, .numshb)
  - Motion files (.nuanmb)
  - Textures (.nutexb) - with image comparison
  - Sound files (.nus3audio, .nus3bank)
- **Junk Folder**: Moves duplicate files to a junk folder rather than deleting them
- **Config Update**: Automatically updates config.json with proper share-to-added mappings
- **Camera Support**: Handles camera files and directory structures
- **Custom Directory Support**: Detects and handles custom directories like model/mewtwomb

## Texture Manager
![TextureManager1](https://github.com/user-attachments/assets/8412f6d8-001b-4a41-8b3f-6dd8c620717e)

A comprehensive tool that combines NUMATB analysis and texture optimization:
- **NUMATB Analyzer**: Analyzes and converts material files (.numatb) to readable JSON format
- **Texture Optimizer**: Identifies unused textures and optimizes texture usage across slots
- Features:
  - Converts NUMATB files to readable JSON format
  - Analyzes texture references in materials
  - Identifies unused textures
  - Moves unused textures to a junk folder
  - Maintains proper file references

### Basic Usage

1. **Launch the Tool**: Run `texture_manager_gui.py`
2. **Select Your Mod**: Use the "Browse" button to locate your mod folder
3. **Choose Fighter and Alt**: Select the fighter and alt slot to analyze
4. **Analyze Materials**: Use the NUMATB Analyzer tab to convert and analyze material files
5. **Optimize Textures**: Use the Texture Optimizer tab to identify and remove unused textures

### Key Features

- **NUMATB Analysis**:
  - Converts material files to readable JSON
  - Shows texture references and usage
  - Provides detailed analysis of material properties

- **Texture Optimization**:
  - Identifies unused textures
  - Shows texture usage statistics
  - Safely moves unused textures to junk folder
  - Maintains proper references in materials

## Nutexb Compare
![Compare](https://github.com/user-attachments/assets/e27e9889-8feb-4482-bb1e-64d1286aa9ee)

A tool that compares two different alts (ie c00 and c01) to find any differences between their texture files (nutexb)

### Basic Usage

1. **Launch the Tool**: Run `nutexb_compare_dir.py`
2. **Select Your Mod**: Use the "Browse" button to locate your mod folder, then click "Load Alts"
3. **Choose Alts**: Select the left and right alternate costumes to compare
4. **Compare Textures**: Hit Compare Textures to find any differences between the two.

## Recommended Workflow

For the best results, use these tools in the following order:

1. **Texture Manager First**
   - Analyze your mod's materials (NUMATB files) to understand texture usage
   - Identify and remove unused textures
   - Clean up texture references before reslotting
   - Why first? This ensures you're not carrying unused textures through the reslotting process

2. **ReslotterGUI Second**
   - After cleaning textures, reslot your character to desired slots
   - Add additional slots if needed
   - Configure slot sharing
   - Why second? Clean textures mean faster reslotting and less chance of issues

3. **Moveset Optimizer Last**
   - After reslotting, optimize the mod structure
   - Remove duplicate files across slots
   - Update config.json for proper file sharing
   - Why last? This ensures you're optimizing the final slot configuration
     
## Best Practices

1. **Always Back Up**: Create a backup of your mod before using these tools
2. **Use Simulation Mode**: Test changes first with the simulation option
3. **Check the Junk Folder**: Review files in the junk folder before deleting them
4. **Verify In-Game**: Test your mod in-game after making changes

## Troubleshooting

- **Missing Files**: If files are missing after optimization, check the junk folder
- **Loading Issues**: Ensure config.json has proper share-to-added entries
- **Reslotting Errors**: For complex mods with multiple fighters, process one fighter at a time

## Advanced Use Cases

- **Multiple Fighters**: Process each fighter separately for best results
- **Custom Directories**: Both tools support custom directory structures
- **Camera Folders**: Camera files are properly handled in the expected structure
- **Sound Files**: Special handling for sound files maintains proper references
