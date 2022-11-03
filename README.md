# ReslotterGUI
**Version 2**

![r](https://i.imgur.com/2lWOEEu.png)

A GUI tool for reslotting mods. Requires python 3.9+. This will reslot anything under the folders `fighter`,`sound`,`ui`, and `effects` (if applicable)

You'll need to download a "Hashes_all.txt" file from [here](https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all) and place it here.

Courtesy of CoolSonicKirby and WuBoy, this will also generate the proper config for you to use! Once the reslotter is finished, it should be ready to be added directly to your switch. If you need more slots, you can manually type in the dropdown box the slot you need (ie `+c21`), or you can edit the `reslotterGUI.py` script at line 18. It should be a variable called `root.maxSlots`, which is defaulted at 11.

Original reslotter written by [Blujay](https://github.com/blu-dev) and maintained by [Jozz](https://github.com/jozz024/ssbu-skin-reslotter)

## Installation

You may run this program's .py file if you have python installed. Otherwise, I've provided a `.exe` version, though the `.py` version will always be the most up-to-date version.

### .py: 
Download via the green code button located on the repository (https://github.com/CSharpM7/reslotter) Run `reslotterGUI.py`, not `reslotter.py`.
### .exe:
(Currently one version behind)
Go to the releases tab and download the exe. Place that exe in it's own folder. Then download the required `Hashes_all.txt` file

## Usage

You can run the `.py` or `.exe` folder using `reslotterGUI.py/exe [mod folder]`. The mod folder argument is optional. You can also drag and drop your mod folder ontop of the application.

Select the root of your mod's folder. You'll be presented with the GUI at the top of this README. It will populate the list with all the alts in that mod. Copy to New Folder will create a new folder with the new alts in the title (Shiny Blue DK (c03)). Exclude Other Alts is for packs with multiple alts in it. Leave it on to only have the changed alts in the new folder. Leave it unchecked to bring all alts into the new folder, changed or not. 

### Changing Slots
Navigate to which skin corresponds to the source of your mod (if you have Shinny Blue DK on the 3rd alt, it should be `c02`). Under the dropdown menu, select its new destination (ie `c03` for the fourth, blue alt).  Hit Change Slots, and the relevant files/folders will be changed, as well as a new `config.json` will be added.
### Setting New Max Slots for UI
You will need to have an editted `ui_chara_db.prc` in order to see additional slots. New Max Slots will create a `.prcxml` which is used to increase the number of slots available in the Character Select Screen after you hit "Change Slots" or "Reconfig". You'll want to set this to the highest slot number in your modpack+1 (if I have Shiny Blue DK on `c10`, I would set the max slots to 11) It is recommended that you only have one of these files per fighter.
### Generating Configs
Similar to [LazyConfig](https://github.com/CSharpM7/SharpSmashSuite/tree/main/LazyConfig), this will create a `config.json` file in your mod folder without changing any of the files, useful for when you are creating a mod that uses additional slots, or if you accidentally deleted the `config.json` file. Click on "Reconfig" to use this option.

## Known Issues
- Only one fighter at a time can be reslotted, so if you have Marth and Mario in a mod pack, you can only reslot Marth **OR** Mario
 - Aegis (Pyra and Mythra), Ice Climbers (Popo and Nana), and Pokemon Trainer (Trainer and their Pokemon) will all be reslotted together. So if you have a Pyra and Mythra skin on c00, they'll both migrate to c08 or whichever slot you are targeting
- Not all fighter's one-slotted effects work
- Not all fighter's `New Max Slots` option has been tested

## Missing Hashes
If a fighter is reslotted to (8n+c) where c is the missing hash (for this example, c is c02 so 8n+c would be 10, 18, 26, etc), these files will be missing. You'll have to edit the `hashes_all.txt` file and add them here, or grab the latest Hashes.txt
- `fighter/eflame/motion/body/c02/c04attackhi4.nuanmb` (Pyra Upsmash)