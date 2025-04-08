@echo off
echo Creating executable for PyInstaller...

:: Install PyInstaller if it isnt present.
pip install pyinstaller

:: Texture Analyzer tools
pyinstaller --noconfirm --onefile --console --add-data "texture_analyzer.py;." "texture_manager_gui.py"

:: Reslotter tools
pyinstaller --noconfirm --onefile --console --add-data "dir_info_with_files_trimmed.json;." --add-data "reslotter.py;." "reslotterGUI.py"

:: Moveset optimizer tools
pyinstaller --noconfirm --onefile --console --add-data "moveset_optimizer.py;." "moveset_optimizer_gui.py" --hidden-import PIL --hidden-import numpy

echo Process complete. The executables are in the "dist" folder.