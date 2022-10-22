# ReslotterGUI

![r](https://i.imgur.com/Esyp5Jo.png)

A GUI tool for reslotting mods. Requires python 3.9+. This will reslot anything under the folders `fighter`,`sound`,`ui`, and `effects` (if applicable )

You'll need to download a "Hashes_all.txt" file from https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all, and place it here.

If you are using additional slots, you'll want to forego the config.json generated here, and use CSK's site (https://coolsonickirby.com/arc/dir-info-with-files.html)

Original reslotter written by Blujay (https://github.com/blu-dev) and maintained by Jozz (https://github.com/jozz024/ssbu-skin-reslotter)

## Installation

You may run this program's .py file if you have python installed. Otherwise, I've provided a .exe version. The .py version will always be the most up-to-date version.

### .py: 
Download via the green code button located on the repository (https://github.com/CSharpM7/reslotter) Run `reslotterGUI.py`, not `reslotter.py.
### .exe:
Go to the releases tab and download the exe. Place that exe in it's own folder. Then download the required `Hashes_all.txt` file

## Usage

Select the root of your mod's folder. You'll be presented with the GUI at the top of this README. Navigate to which skin corresponds to the source of your mod (if you have Shinny Blue DK on the 3rd alt, it should be c02). Under the dropdown menu, select its new destination (ie c03 for the fourth, blue alt). It is recommended that you keep "Place Files in New Directory", but if you leave it unchecked, it will place Shiny Blue DK (c03) in the same folder as the original, c02. Exclude Other Alts is usually for packs with multiple colors in it. Leave it on to only have the changed alts in the new folder. Leave it unchecked to bring all alts into the new folder, changed or not.
