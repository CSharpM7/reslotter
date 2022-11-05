# [ReslotterGUI](https://github.com/CSharpM7/reslotter)
**Version 2.5**

![r](https://i.imgur.com/NWFBCcQ.png)

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

Select the root of your mod's folder. You'll be presented with the GUI at the top of this README. You can also hover over most of the labels for additional tool tips. It will populate the list with all the alts in that mod. Copy to New Folder will create a new folder with the new alts in the title (Shiny Blue DK (c03)). Exclude Blank Targets is for packs with multiple alts in it. Leave it on to only have the changed alts in the new folder. Leave it unchecked to bring all alts into the new folder, changed or not. 

### Changing Slots
Navigate to which skin corresponds to the source of your mod (if you have Shinny Blue DK on the 3rd alt, it should be `c02`). Under the dropdown menu, select its new destination (ie `c03` for the fourth, blue alt).  Hit Change Slots, and the relevant files/folders will be changed, as well as a new `config.json` will be added.

### Adding New Slots
When you set the new slot to anything beyond `c07` (denoted with a + prefix), you are adding slots to the game! This is a slightly more involved process than just changing base slots, so you will need to go to File->Slot Addition Guide to understand how this process works. 

"Share From" is the slot that the mod is based on. For example, a Robin mod on slot `c05` would set Share From to `c00` as both are male alts. A Sephiroth mod on slot `c07` should use `c06` for the shirtless variant. This program will do its best to set this to the optimal slot for each fighter, but you can manually set it if you want to.

### Setting New Max Slots for the Character Select Screen
New Max Slots will create a `ui_chara_db.prcxml` file in `ui/param/database` which is used to increase the number of slots available in the Character Select Screen after you hit "Change Slots" or "Reconfig". `ui_chara_db.prc` is the file used to control how many slots can be selected on the character select screen, while the .`prcxml` version patches the file in game. You'll want to set this to the highest slot number in your modpack+1 (if I have Shiny Blue DK on `c10`, I would set the max slots to 11) It is recommended that you only have one of these files per fighter.

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

