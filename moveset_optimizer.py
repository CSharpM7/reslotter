import os
import re
import sys
import json
import shutil
import argparse
import glob
import traceback
import tempfile
import subprocess
import uuid
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
try:
    import numpy as np
    from PIL import Image, ImageChops, ImageDraw
    NUTEXB_COMPARISON_AVAILABLE = True
except ImportError:
    NUTEXB_COMPARISON_AVAILABLE = False


class MovesetOptimizer:
    """Moveset optimizer that identifies and moves duplicate files to junk"""
    
    def __init__(self, mod_directory: str, fighter_name: str = None, main_slot: str = None, simulation: bool = False):
        """
        Initializes the moveset optimizer
        
        Args:
            mod_directory: Path to the mod directory
            fighter_name: Fighter name (optional, will be auto-detected)
            main_slot: Main slot to use as reference (optional, will be auto-detected)
            simulation: If True, simulates operations without making real changes
        """
        self.mod_directory = mod_directory
        self.simulation = simulation
        self.fighter_name = fighter_name
        self.user_main_slot = main_slot
        self.main_slot = None
        self.junk_dir = os.path.join(mod_directory, "junk")
        
        # Auto-detect fighter if not specified
        if self.fighter_name is None:
            self.fighter_name = self._detect_fighter_name()
        
        if not self.fighter_name:
            raise ValueError("Could not detect fighter in the mod directory")
            
        # Create junk directory if it doesn't exist and we're not in simulation mode
        if not simulation and not os.path.exists(self.junk_dir):
            os.makedirs(self.junk_dir)
        
    def _detect_fighter_name(self) -> str:
        """
        Detects the fighter name from the mod directory
        
        Returns:
            Fighter name or None if it cannot be detected
        """
        fighter_dir = os.path.join(self.mod_directory, "fighter")
        print(f"Looking for fighters in: {fighter_dir}")
        
        if not os.path.exists(fighter_dir):
            print(f"Fighter directory does not exist in {self.mod_directory}")
            return None
            
        # Look for subdirectories in fighter/
        fighter_dirs = [d for d in os.listdir(fighter_dir) 
                       if os.path.isdir(os.path.join(fighter_dir, d))]
        
        print(f"Fighters found: {fighter_dirs}")
        
        if not fighter_dirs:
            print(f"No subdirectories found in {fighter_dir}")
            return None
            
        # If there's more than one fighter, use the first one
        # This could be improved in the future
        fighter_name = fighter_dirs[0]
        print(f"Using fighter: {fighter_name}")
        return fighter_name
        
    def detect_slots(self) -> List[str]:
        """
        Detects all available slots for the fighter
        
        Returns:
            List of slots (c00, c01, etc.)
        """
        slots = set()
        fighter_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name)
        print(f"Looking for slots in: {fighter_dir}")
        
        # Check various subdirectories where we can find slots
        for subdir in ["model/body", "motion", "animcmd"]:
            full_subdir = os.path.join(fighter_dir, subdir)
            print(f"Checking subdirectory: {full_subdir}")
            if os.path.exists(full_subdir):
                # Look for directories that match the cXX pattern
                items = os.listdir(full_subdir)
                print(f"Items found in {full_subdir}: {items}")
                for item in items:
                    if os.path.isdir(os.path.join(full_subdir, item)) and re.match(r'c\d+', item):
                        print(f"Found slot: {item}")
                        slots.add(item)
            else:
                print(f"Subdirectory does not exist: {full_subdir}")
        
        result = sorted(list(slots))
        print(f"Detected slots: {result}")
        return result

    def determine_main_slot(self, slots: List[str]) -> str:
        """
        Determines which is the main slot
        
        Args:
            slots: List of available slots
            
        Returns:
            The main slot (e.g.: c00)
        """
        # If the user specified a main slot, use it if it exists
        if self.user_main_slot and self.user_main_slot in slots:
            print(f"Using main slot specified by user: {self.user_main_slot}")
            return self.user_main_slot
            
        if not slots:
            return None
            
        # Usually, the main slot is the first one (c00 or c01)
        main_candidates = ["c00", "c01"]
        
        for candidate in main_candidates:
            if candidate in slots:
                return candidate
                
        # If we don't find the usual candidates, use the lowest number
        return min(slots, key=lambda x: int(x[1:]))
    
    def get_camera_files_in_slot(self, fighter: str, slot: str) -> List[str]:
        """
        Gets all camera files for a specific slot
        Camera files are in camera/fighter/[fighter]/[slot]/ directory structure
        
        Args:
            fighter: Fighter name
            slot: Slot identifier (e.g.: c00, c01)
            
        Returns:
            List of camera file paths relative to the mod directory
        """
        files = []
        camera_dir = os.path.join(self.mod_directory, "camera", "fighter", fighter, slot)
        
        if os.path.exists(camera_dir):
            print(f"Searching camera directory: {camera_dir}")
            for root, _, filenames in os.walk(camera_dir):
                for filename in filenames:
                    # Skip .marker files from comparison
                    if filename.endswith('.marker'):
                        print(f"Skipping .marker file: {filename}")
                        continue
                        
                    # Get relative path to mod directory
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, self.mod_directory)
                    print(f"Camera file found: {rel_path}")
                    files.append(rel_path)
        else:
            print(f"Camera directory does not exist: {camera_dir}")
            
        print(f"Total camera files found for {slot}: {len(files)}")
        return files

    def get_all_files_in_slot(self, fighter: str, slot: str) -> List[str]:
        """
        Gets all file paths for a specific slot
        
        Args:
            fighter: Fighter name
            slot: Slot identifier (e.g.: c00, c01)
            
        Returns:
            List of file paths relative to the mod directory
        """
        files = []
        fighter_dir = os.path.join(self.mod_directory, "fighter", fighter)
        print(f"Looking for files for {fighter} in slot {slot}")
        print(f"Base directory: {fighter_dir}")
        
        # Detect custom directories in motion folder
        custom_motion_dirs = []
        motion_dir = os.path.join(fighter_dir, "motion")
        if os.path.exists(motion_dir):
            for item in os.listdir(motion_dir):
                item_path = os.path.join(motion_dir, item)
                if os.path.isdir(item_path) and item not in ["body", "weapon"]:
                    custom_motion_dirs.append(f"motion/{item}")
                    print(f"Detected custom directory: motion/{item}")
        
        # Detect custom directories in model folder
        custom_model_dirs = []
        model_dir = os.path.join(fighter_dir, "model")
        if os.path.exists(model_dir):
            for item in os.listdir(model_dir):
                item_path = os.path.join(model_dir, item)
                if os.path.isdir(item_path) and item not in ["body", "weapon"]:
                    custom_model_dirs.append(f"model/{item}")
                    print(f"Detected custom directory: model/{item}")
        
        # Expanded list of common subdirectories in movesets
        subdirs = [
            "motion",                # Motion files
            "motion/body",           # Body movements
            "motion/weapon",         # Weapon movements
            "animcmd",               # Animation commands
            "animcmd/body",          # Body animation commands
            "animcmd/weapon",        # Weapon animation commands
            "effect",                # Visual effects
            "model/body",            # Body models
            "model/weapon",          # Weapon models
            "sound",                 # Sound effects
            "game",                  # Game parameters
            "camera",                # Camera settings
            "expression",            # Facial expressions
            "stprm"                  # Other parameters 
        ]
        
        # Add custom directories to the list
        subdirs.extend(custom_motion_dirs)
        subdirs.extend(custom_model_dirs)
        
        # Search in all subdirectories
        for subdir in subdirs:
            search_dir = os.path.join(fighter_dir, subdir, slot)
            print(f"Searching in: {search_dir}")
            if os.path.exists(search_dir):
                print(f"Directory exists: {search_dir}")
                for root, _, filenames in os.walk(search_dir):
                    for filename in filenames:
                        # Skip .marker files from comparison
                        if filename.endswith('.marker'):
                            print(f"Skipping .marker file: {filename}")
                            continue
                            
                        # Get relative path to mod directory
                        full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(full_path, self.mod_directory)
                        print(f"File found: {rel_path}")
                        files.append(rel_path)
            else:
                print(f"Directory does not exist: {search_dir}")
        
        # Also search in subdirectories that don't use slots directly
        # but may have files specific to the slot
        additional_dirs = [
            "param",                 # General parameters
            "script",                # Scripts
            "ui"                     # UI elements
        ]
        
        for subdir in additional_dirs:
            search_dir = os.path.join(fighter_dir, subdir)
            if os.path.exists(search_dir):
                for root, _, filenames in os.walk(search_dir):
                    for filename in filenames:
                        # Skip .marker files from comparison
                        if filename.endswith('.marker'):
                            continue
                            
                        # Search for files containing the slot name
                        if slot in filename:
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, self.mod_directory)
                            print(f"Additional file found: {rel_path}")
                            files.append(rel_path)
        
        # Search in sound/bank directories for fighter-specific audio files
        # This includes se_fighter_cXX.nus3audio and se_fighter_cXX.nus3bank files
        sound_patterns = [
            f"sound/bank/fighter/se_{fighter}_{slot}",       # Sound effects
            f"sound/bank/fighter_voice/vc_{fighter}_{slot}"  # Voice clips
        ]
        
        for pattern in sound_patterns:
            base_path = os.path.join(self.mod_directory, os.path.dirname(pattern))
            if os.path.exists(base_path):
                print(f"Searching for sound files in: {base_path}")
                file_prefix = os.path.basename(pattern)
                
                for root, _, filenames in os.walk(base_path):
                    for filename in filenames:
                        # Check if the file matches our pattern (se_fighter_cXX or vc_fighter_cXX)
                        if filename.startswith(file_prefix):
                            full_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(full_path, self.mod_directory)
                            print(f"Sound file found: {rel_path}")
                            files.append(rel_path)
        
        # Get camera files (camera/fighter/[fighter]/[slot]/)
        camera_files = self.get_camera_files_in_slot(fighter, slot)
        files.extend(camera_files)
        
        print(f"Total files found for {slot}: {len(files)}")
        return files
    
    def are_files_identical(self, file1: str, file2: str) -> bool:
        """
        Compares two files binary to determine if they are identical
        
        Args:
            file1: Path to the first file
            file2: Path to the second file
            
        Returns:
            True if the files are identical, False otherwise
        """
        # Check if both files exist
        if not os.path.exists(file1) or not os.path.exists(file2):
            return False
            
        # Check if sizes are different (quick)
        if os.path.getsize(file1) != os.path.getsize(file2):
            return False
            
        # Compare byte by byte (may be slow for large files)
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            # Read and compare in blocks for efficiency
            while True:
                b1 = f1.read(8192)  # 8KB chunks
                b2 = f2.read(8192)
                
                if b1 != b2:
                    return False
                
                if not b1:  # EOF
                    return True
    
    def load_config(self) -> Dict:
        """
        Loads the config.json file from the mod
        
        Returns:
            Dictionary with the mod configuration or an empty dictionary if it doesn't exist
        """
        config_path = os.path.join(self.mod_directory, "config.json")
        backup_path = config_path + ".bak"
        
        if not os.path.exists(config_path):
            print(f"config.json file not found in {self.mod_directory}")
            return {}
            
        try:
            # Try to load the main file
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Verify it's a dictionary
            if not isinstance(config, dict):
                print(f"Warning: config.json does not contain a valid dictionary")
                return {}
                
            return config
                
        except json.JSONDecodeError as e:
            print(f"Error decoding config.json: {e}")
            # Try to load from backup if it exists
            if os.path.exists(backup_path):
                try:
                    print(f"Trying to load from backup {backup_path}")
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    if isinstance(config, dict):
                        print(f"Config loaded successfully from backup")
                        return config
                    else:
                        print(f"Backup does not contain a valid dictionary")
                except Exception as e2:
                    print(f"Error loading backup: {e2}")
            
            # If everything fails, create a new config.json file with basic structure
            print(f"Creating a new config.json file with basic structure")
            new_config = {"share-to-added": {}}
            return new_config
            
        except UnicodeDecodeError as e:
            print(f"Encoding error reading config.json: {e}")
            print(f"Trying to read with different encodings...")
            
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'ISO-8859-1']:
                try:
                    with open(config_path, 'r', encoding=encoding) as f:
                        config = json.load(f)
                    print(f"File loaded successfully using encoding {encoding}")
                    return config if isinstance(config, dict) else {}
                except Exception:
                    continue
                    
            print(f"Could not read file with any encoding")
            return {}
            
        except Exception as e:
            print(f"Error loading config.json: {e}")
            return {}
    
    def save_config(self, config: Dict) -> bool:
        """
        Saves the config.json file from the mod
        
        Args:
            config: Dictionary with the mod configuration
            
        Returns:
            True if saved successfully, False otherwise
        """
        config_path = os.path.join(self.mod_directory, "config.json")
        backup_path = config_path + ".bak"
        
        if self.simulation:
            print(f"Simulation mode: No real file will be saved in {config_path}")
            return True
            
        print(f"Saving config.json in {config_path}")
        try:
            # Ensure config is serializable
            if not isinstance(config, dict):
                print(f"Warning: Configuration is not a valid dictionary, empty dictionary will be used")
                config = {}
                
            # Create a backup before modifying the file
            if os.path.exists(config_path):
                try:
                    shutil.copy2(config_path, backup_path)
                    print(f"Backup created in {backup_path}")
                except Exception as e:
                    print(f"Could not create backup: {e}")
            
            # Write the new configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            print(f"Config.json saved successfully in {config_path}")
            return True
        except Exception as e:
            print(f"Error saving config.json: {e}")
            # Try to restore backup if it exists
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, config_path)
                    print(f"Backup restored from {backup_path}")
                except Exception as e2:
                    print(f"Could not restore backup: {e2}")
            return False
    
    def update_share_to_added(self, main_slot: str, duplicate_files_by_slot: Dict[str, List[str]]) -> bool:
        """
        Updates the share-to-added section of config.json
        
        Args:
            main_slot: Main slot to use as reference
            duplicate_files_by_slot: Dictionary with duplicate files by slot
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            print(f"Updating share-to-added in config.json...")
            
            # Read current config or create a new one
            config_path = os.path.join(self.mod_directory, "config.json")
            config = {}
            
            # Try to load existing config
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            config = json.loads(content)
                except Exception as e:
                    print(f"Error reading config.json, creating a new one: {e}")
                    config = {}
            
            # Ensure config is a dictionary
            if not isinstance(config, dict):
                config = {}
                
            # Ensure share-to-added exists
            if "share-to-added" not in config:
                config["share-to-added"] = {}
            
            # For each slot with duplicate files
            for slot, files in duplicate_files_by_slot.items():
                for file_path in files:
                    # Convert paths to Unix format (with /)
                    file_path = file_path.replace('\\', '/')
                    
                    # Determine how to handle different file types
                    is_sound_file = False
                    is_camera_file = False
                    main_file_path = ""
                    
                    # Special handling for sound files (se_fighter_cXX.nus3audio, etc.)
                    sound_patterns = [
                        f"/se_{self.fighter_name}_{slot}",
                        f"/vc_{self.fighter_name}_{slot}"
                    ]
                    
                    for pattern in sound_patterns:
                        if pattern in file_path:
                            is_sound_file = True
                            # Replace the slot in the filename
                            main_file_path = file_path.replace(f"_{slot}", f"_{main_slot}")
                            break
                            
                    # Special handling for camera files (camera/fighter/fighter_name/slot)
                    camera_pattern = f"camera/fighter/{self.fighter_name}/{slot}/"
                    if camera_pattern in file_path:
                        is_camera_file = True
                        # Replace the slot in the camera path
                        main_file_path = file_path.replace(f"/{slot}/", f"/{main_slot}/")
                    
                    # If not a sound or camera file, handle with the standard slot pattern
                    if not is_sound_file and not is_camera_file:
                        # Construct file path in main slot
                        slot_pattern = f"/{slot}/"
                        main_pattern = f"/{main_slot}/"
                        
                        if slot_pattern in file_path:
                            main_file_path = file_path.replace(slot_pattern, main_pattern)
                        else:
                            # Try with more general regex format
                            main_file_path = re.sub(r'/c\d+/', f'/{main_slot}/', file_path)
                    
                    print(f"Duplicate file: {file_path}")
                    print(f"Main file: {main_file_path}")
                    
                    # Add to share-to-added
                    if main_file_path in config["share-to-added"]:
                        # If it exists, add to existing list
                        if not isinstance(config["share-to-added"][main_file_path], list):
                            config["share-to-added"][main_file_path] = []
                        
                        if file_path not in config["share-to-added"][main_file_path]:
                            config["share-to-added"][main_file_path].append(file_path)
                            print(f"Added {file_path} to existing list")
                    else:
                        # Create new entry
                        config["share-to-added"][main_file_path] = [file_path]
                        print(f"Created new entry for {main_file_path}")
            
            # Save current config
            if self.simulation:
                print("Simulation mode: no file will be saved")
                return True
                
            # Write config file
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                print(f"Config.json updated successfully in {config_path}")
                return True
            except Exception as e:
                print(f"Error saving config.json: {e}")
                return False
                
        except Exception as e:
            print(f"General error in update_share_to_added: {e}")
            return False
    
    def analyze_mod(self) -> Dict[str, List[str]]:
        """
        Analyzes the mod to find duplicates between slots
        Compares the first slot with all others
        
        Returns:
            Dictionary with duplicate files by slot
        """
        slots = self.detect_slots()
        if not slots:
            print(f"No slots found for fighter {self.fighter_name}")
            return {}
            
        # Determine main slot
        if self.user_main_slot and self.user_main_slot in slots:
            self.main_slot = self.user_main_slot
        else:
            # Use first slot as main
            self.main_slot = slots[0]
            
        print(f"Using {self.main_slot} as main slot for {self.fighter_name}")
        
        # Get all files from main slot
        main_slot_files = self.get_all_files_in_slot(self.fighter_name, self.main_slot)
        
        # Analyze each alternative slot
        result = {}
        for slot in [s for s in slots if s != self.main_slot]:
            print(f"\nComparing {self.main_slot} with {slot} (full analysis)...")
            
            duplicates = self.compare_specific_slots(self.main_slot, slot)
            
            if duplicates:
                result[slot] = duplicates
                print(f"Found {len(duplicates)} duplicate files in {slot}")
            else:
                print(f"No duplicate files found between {self.main_slot} and {slot}")
        
        # Show summary
        total_duplicates = sum(len(files) for files in result.values())
        if total_duplicates > 0:
            print(f"\nSummary: {total_duplicates} duplicate files found in total")
            # Show number of duplicates by slot
            for slot, files in result.items():
                print(f"  Slot {slot}: {len(files)} duplicate files")
        else:
            print("\nNo duplicate files found in any slot")
            
        return result
        
    def optimize_mod(self) -> Dict[str, List[str]]:
        """
        Optimizes the mod moving duplicate files to the junk folder
        and updating the config.json
        
        Returns:
            Dictionary with optimized files by slot
        """
        duplicates = self.analyze_mod()
        
        if not duplicates:
            print("No duplicate files found to optimize")
            return {}
            
        result = {}
        # Track affected directories for later cleanup
        affected_directories = set()
        # Track affected camera directories
        affected_camera_directories = set()
        
        for slot, files in duplicates.items():
            # Filter .marker files (additional safety)
            filtered_files = [file for file in files if not file.endswith('.marker')]
            if len(filtered_files) < len(files):
                skipped = len(files) - len(filtered_files)
                print(f"{skipped} .marker files have been excluded from optimization for {slot}")
                files = filtered_files
                
            moved_files = []
            for file_path in files:
                full_path = os.path.join(self.mod_directory, file_path)
                
                # Track the directory for later cleanup
                affected_directories.add(os.path.dirname(full_path))
                
                # Track camera directories separately
                camera_pattern = f"camera/fighter/{self.fighter_name}/{slot}"
                if camera_pattern in file_path:
                    camera_dir = os.path.join(self.mod_directory, f"camera/fighter/{self.fighter_name}/{slot}")
                    affected_camera_directories.add(camera_dir)
                
                # Create path in junk directory
                junk_path = os.path.join(self.junk_dir, file_path)
                junk_dir = os.path.dirname(junk_path)
                
                if not self.simulation:
                    # Create destination directory if it doesn't exist
                    if not os.path.exists(junk_dir):
                        os.makedirs(junk_dir)
                    
                    # Move file
                    try:
                        shutil.move(full_path, junk_path)
                        moved_files.append(file_path)
                    except Exception as e:
                        print(f"Error moving {file_path}: {e}")
                else:
                    # In simulation mode, we only register
                    moved_files.append(file_path)
            
            if moved_files:
                result[slot] = moved_files
        
        # Update config.json with moved files
        if result and not self.simulation:
            print("\nUpdating config.json with shared files...")
            if self.update_share_to_added(self.main_slot, result):
                print("config.json updated successfully with shared files")
            else:
                print("Error updating config.json")
                
        # Clean up empty directories
        if affected_directories:
            print("\nChecking for empty directories...")
            fighter_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name)
            if os.path.exists(fighter_dir):
                self.remove_empty_directories(fighter_dir)
        
        # Clean up empty camera directories
        if affected_camera_directories:
            print("\nChecking for empty camera directories...")
            for camera_dir in affected_camera_directories:
                if os.path.exists(camera_dir):
                    self.remove_empty_directories(camera_dir)
                    
                    # Also check if the fighter's camera directory is empty
                    fighter_camera_dir = os.path.dirname(camera_dir)
                    if os.path.exists(fighter_camera_dir):
                        self.remove_empty_directories(fighter_camera_dir)
                
        return result

    def compare_specific_slots(self, main_slot: str, compare_slot: str) -> List[str]:
        """
        Specifically compares two slots and finds duplicate files
        In WinMerge style: compares all files independently of their paths
        
        Args:
            main_slot: Main slot to use as reference
            compare_slot: Slot to compare with the main
            
        Returns:
            List of duplicate files in the compared slot
        """
        if main_slot == compare_slot:
            print(f"Error: No comparison can be made with the same slot ({main_slot})")
            return []
            
        print(f"Comparing {main_slot} with {compare_slot} (full analysis)...")
        
        # Get files from both slots
        main_slot_files = self.get_all_files_in_slot(self.fighter_name, main_slot)
        compare_slot_files = self.get_all_files_in_slot(self.fighter_name, compare_slot)
        
        print(f"Files in {main_slot}: {len(main_slot_files)}")
        print(f"Files in {compare_slot}: {len(compare_slot_files)}")
        
        # Find duplicates
        duplicates = []
        
        # Create dictionary by file size for faster comparisons
        print("Organizing files by size for optimization...")
        main_files_by_size = {}
        for main_file in main_slot_files:
            full_path = os.path.join(self.mod_directory, main_file)
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                if file_size not in main_files_by_size:
                    main_files_by_size[file_size] = []
                main_files_by_size[file_size].append(main_file)
        
        # Count the number of real comparisons that will be made
        print("Calculating the number of necessary comparisons...")
        real_comparisons = 0
        for compare_file in compare_slot_files:
            compare_full_path = os.path.join(self.mod_directory, compare_file)
            if not os.path.exists(compare_full_path):
                continue
                
            file_size = os.path.getsize(compare_full_path)
            if file_size in main_files_by_size:
                real_comparisons += len(main_files_by_size[file_size])
        
        print(f"Will perform {real_comparisons} comparisons (optimized by file size)")
        progress_step = max(1, real_comparisons // 20)  # Show progress every 5%
        
        # Now compare only files of the same size
        comparison_count = 0
        for compare_file in compare_slot_files:
            # Ignore .marker files as they should be in all slots
            if compare_file.endswith('.marker'):
                print(f"Ignoring .marker file: {compare_file}")
                continue
                
            compare_full_path = os.path.join(self.mod_directory, compare_file)
            
            if not os.path.exists(compare_full_path):
                continue
                
            file_size = os.path.getsize(compare_full_path)
            if file_size not in main_files_by_size:
                continue
                
            # Compare only with files of the same size
            for main_file in main_files_by_size[file_size]:
                comparison_count += 1
                if comparison_count % progress_step == 0:
                    progress_percent = (comparison_count / real_comparisons) * 100
                    print(f"Progress: {progress_percent:.1f}% ({comparison_count}/{real_comparisons})")
                
                main_full_path = os.path.join(self.mod_directory, main_file)
                
                # Construct equivalent path for comparison
                equivalent_path = False
                
                # Check different path separators
                if f"/{compare_slot}/" in compare_file and f"/{main_slot}/" in main_file:
                    equivalent_path = compare_file.replace(f"/{compare_slot}/", f"/{main_slot}/") == main_file
                elif f"\\{compare_slot}\\" in compare_file and f"\\{main_slot}\\" in main_file:
                    equivalent_path = compare_file.replace(f"\\{compare_slot}\\", f"\\{main_slot}\\") == main_file
                
                # Also check for sound files (se_fighter_cXX.nus3audio, etc.)
                sound_patterns = [
                    (f"se_{self.fighter_name}_{compare_slot}", f"se_{self.fighter_name}_{main_slot}"),
                    (f"vc_{self.fighter_name}_{compare_slot}", f"vc_{self.fighter_name}_{main_slot}")
                ]
                
                for compare_pattern, main_pattern in sound_patterns:
                    if compare_pattern in compare_file and main_pattern in main_file:
                        equivalent_path = compare_file.replace(compare_pattern, main_pattern) == main_file
                        if equivalent_path:
                            break
                
                # Consider duplicates only if not the same path (equivalent)
                if not equivalent_path and self.are_files_identical(main_full_path, compare_full_path):
                    duplicates.append(compare_file)
                    print(f"Duplicate found: {compare_file} (identical to {main_file})")
                    break  # Once we find that it's duplicate, we don't need to compare further
        
        # Also make traditional file equivalent comparison
        print("Performing traditional file equivalent comparison...")
        for compare_file in compare_slot_files:
            # Ignore .marker files as they should be in all slots
            if compare_file.endswith('.marker'):
                continue
                
            # Skip files that are already identified as duplicates
            if compare_file in duplicates:
                continue
                
            # Construct equivalent path in main slot
            main_equivalent = None
            
            # Check for sound files first (se_fighter_cXX.nus3audio, etc.)
            sound_patterns = [
                (f"se_{self.fighter_name}_{compare_slot}", f"se_{self.fighter_name}_{main_slot}"),
                (f"vc_{self.fighter_name}_{compare_slot}", f"vc_{self.fighter_name}_{main_slot}")
            ]
            
            for compare_pattern, main_pattern in sound_patterns:
                if compare_pattern in compare_file:
                    main_equivalent = compare_file.replace(compare_pattern, main_pattern)
                    break
            
            # If not a sound file, use standard path replacement
            if main_equivalent is None:
                # Check different path separators
                if f"/{compare_slot}/" in compare_file:
                    main_equivalent = compare_file.replace(f"/{compare_slot}/", f"/{main_slot}/")
                elif f"\\{compare_slot}\\" in compare_file:
                    main_equivalent = compare_file.replace(f"\\{compare_slot}\\", f"\\{main_slot}\\")
                else:
                    # If we don't find exact pattern, use regex for greater flexibility
                    main_equivalent = re.sub(r'[/\\]' + compare_slot + r'[/\\]', f'/{main_slot}/', compare_file)
            
            # Check if equivalent file exists in main slot files
            found = False
            for main_file in main_slot_files:
                if main_file == main_equivalent:
                    found = True
                    break
            
            # If equivalent file exists and not already in duplicates list
            if found and compare_file not in duplicates:
                compare_full_path = os.path.join(self.mod_directory, compare_file)
                main_full_path = os.path.join(self.mod_directory, main_equivalent)
                
                if self.are_files_identical(main_full_path, compare_full_path):
                    duplicates.append(compare_file)
                    print(f"Found equivalent duplicate: {compare_file} (equivalent to {main_equivalent})")
        
        print(f"Comparison finished. {len(duplicates)} duplicate files found in {compare_slot}")
        return duplicates
        
    def optimize_specific_slot(self, main_slot: str, compare_slot: str) -> List[str]:
        """
        Optimizes a specific slot moving duplicate files to junk
        and updating the config.json
        
        Args:
            main_slot: Main slot to use as reference
            compare_slot: Slot to optimize
            
        Returns:
            List of moved files to junk
        """
        # Check if both slots exist
        slots = self.detect_slots()
        if main_slot not in slots:
            raise ValueError(f"Main slot {main_slot} does not exist")
        if compare_slot not in slots:
            raise ValueError(f"Slot to compare {compare_slot} does not exist")
        
        # Find duplicates
        duplicates = self.compare_specific_slots(main_slot, compare_slot)
        
        if not duplicates:
            print(f"No duplicate files found between {main_slot} and {compare_slot}")
            return []
            
        # Filter .marker files from the duplicates list (additional safety)
        filtered_duplicates = [file for file in duplicates if not file.endswith('.marker')]
        if len(filtered_duplicates) < len(duplicates):
            skipped = len(duplicates) - len(filtered_duplicates)
            print(f"{skipped} .marker files have been excluded from optimization")
            duplicates = filtered_duplicates
        
        # Track affected directories for later cleanup
        affected_directories = set()
        # Track affected camera directories
        affected_camera_directories = set()
        
        # Move duplicates to junk
        moved_files = []
        for file_path in duplicates:
            full_path = os.path.join(self.mod_directory, file_path)
            
            # Track the directory for later cleanup
            affected_directories.add(os.path.dirname(full_path))
            
            # Track camera directories separately
            camera_pattern = f"camera/fighter/{self.fighter_name}/{compare_slot}"
            if camera_pattern in file_path:
                camera_dir = os.path.join(self.mod_directory, f"camera/fighter/{self.fighter_name}/{compare_slot}")
                affected_camera_directories.add(camera_dir)
            
            # Create path in junk directory
            junk_path = os.path.join(self.junk_dir, file_path)
            junk_dir = os.path.dirname(junk_path)
            
            if not self.simulation:
                # Create destination directory if it doesn't exist
                if not os.path.exists(junk_dir):
                    os.makedirs(junk_dir)
                
                # Move file
                try:
                    shutil.move(full_path, junk_path)
                    moved_files.append(file_path)
                except Exception as e:
                    print(f"Error moving {file_path}: {e}")
            else:
                # In simulation mode, we only register
                moved_files.append(file_path)
        
        # Update config.json with moved files
        if moved_files and not self.simulation:
            print("\nUpdating config.json with shared files...")
            duplicate_files_by_slot = {compare_slot: moved_files}
            if self.update_share_to_added(main_slot, duplicate_files_by_slot):
                print("config.json updated successfully with shared files")
            else:
                print("Error updating config.json")
        
        # Clean up empty directories
        if affected_directories:
            print("\nChecking for empty directories...")
            fighter_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name)
            if os.path.exists(fighter_dir):
                self.remove_empty_directories(fighter_dir)
        
        # Clean up empty camera directories
        if affected_camera_directories:
            print("\nChecking for empty camera directories...")
            for camera_dir in affected_camera_directories:
                if os.path.exists(camera_dir):
                    self.remove_empty_directories(camera_dir)
                    
                    # Also check if the fighter's camera directory is empty
                    fighter_camera_dir = os.path.dirname(camera_dir)
                    if os.path.exists(fighter_camera_dir):
                        self.remove_empty_directories(fighter_camera_dir)
                
        return moved_files

    def find_nutexb_files(self, directory: str) -> List[str]:
        """
        Find all NUTEXB files in a directory
        
        Args:
            directory: Directory to search in
            
        Returns:
            List of NUTEXB file paths
        """
        nutexb_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.nutexb'):
                    nutexb_files.append(os.path.join(root, file))
        return nutexb_files

    def nutexb_to_png(self, nutexb_path, output_dir=None):
        """Converts NUTEXB to PNG directly for visualization"""
        try:
            # If there is no output directory, use a temporary one
            if output_dir is None:
                output_dir = tempfile.mkdtemp()
            
            # Output filename with unique identifier to avoid collisions
            uid = str(uuid.uuid4())[:8]
            timestamp = int(time.time())
            base_name = f"{os.path.basename(nutexb_path).split('.')[0]}_{uid}_{timestamp}.png"
            output_path = os.path.join(output_dir, base_name)
            
            print(f"Processing {nutexb_path} -> {output_path}")
            
            # Method 1: Use the Ultimate Tex CLI tool if available
            try:
                # Check if ultimate_tex_cli is available
                result = subprocess.run(["ultimate_tex_cli", "--version"], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      text=True, shell=True)
                
                if "ultimate_tex_cli" in str(result.stdout) or "ultimate_tex_cli" in str(result.stderr):
                    print(f"Converting with Ultimate Tex CLI: {nutexb_path}")
                    cmd = f"ultimate_tex_cli \"{nutexb_path}\" \"{output_path}\""
                    result = subprocess.run(cmd, shell=True, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          text=True)
                    
                    print(f"Result: {result.stdout}")
                    print(f"Errors: {result.stderr}")
                    
                    if os.path.exists(output_path):
                        print(f"Texture successfully converted: {output_path}")
                        return output_path
            except Exception as tex_error:
                print(f"Ultimate Tex CLI not found or error using it: {tex_error}")
                print("Please download ultimate_tex_cli from: https://github.com/ScanMountGoat/ultimate-tex-cli/releases")
                print("Place ultimate_tex_cli.exe in the same folder as this program.")
            
            # Method 2: Direct reading of binary data
            try:
                # Open and read the NUTEXB file directly
                with open(nutexb_path, 'rb') as f:
                    data = f.read()
                
                # Verify if it's really a NUTEXB file
                if data[:4] not in [b'NUTX', b'nutx', b'NUTB', b'nutb']:
                    raise ValueError(f"The file {nutexb_path} does not appear to be a valid NUTEXB")
                
                # Try to extract texture dimensions (approximate location)
                width = height = 256  # Default values
                
                # Look in known positions for dimensions (offset 0x10-0x1C)
                # Values are little-endian
                for offset in range(0x10, 0x20, 4):
                    if offset + 8 < len(data):
                        possible_width = int.from_bytes(data[offset:offset+4], byteorder='little')
                        possible_height = int.from_bytes(data[offset+4:offset+8], byteorder='little')
                        
                        # Check if they are reasonable dimensions
                        if (16 <= possible_width <= 4096 and 
                            16 <= possible_height <= 4096):
                            # Dimensions are usually powers of 2
                            width = possible_width
                            height = possible_height
                            print(f"Dimensions detected in {nutexb_path}: {width}x{height}")
                            break
                
                # Look for the start of image data
                # Image data is usually after the header
                image_data_offset = None
                for offset in [0x80, 0x100, 0x180, 0x200, 0x280, 0x300]:
                    if offset + (width * height * 4) <= len(data):
                        # We try to verify if it seems to contain image data
                        # by looking for variance in color patterns
                        sample = data[offset:offset+width*height*4:16]  # Sampling the data
                        if len(set(sample)) > 32:  # If there is enough value variance
                            image_data_offset = offset
                            break
                
                if image_data_offset is not None:
                    print(f"Image data found in {nutexb_path} at offset: 0x{image_data_offset:X}")
                    
                    # Try different common formats in NUTEXB
                    try:
                        # Try RGBA (most common)
                        image_data = data[image_data_offset:image_data_offset + width * height * 4]
                        img = Image.frombuffer('RGBA', (width, height), image_data, 'raw', 'RGBA', 0, 1)
                        img.save(output_path)
                        print(f"Texture converted as RGBA: {output_path}")
                        return output_path
                    except Exception as e1:
                        print(f"Error converting as RGBA: {e1}")
                        
                        try:
                            # Try BGRA (also common)
                            image_data = data[image_data_offset:image_data_offset + width * height * 4]
                            # Convert BGRA to RGBA
                            array = np.frombuffer(image_data, dtype=np.uint8).reshape(height, width, 4)
                            array = array[:, :, [2, 1, 0, 3]]  # BGRA -> RGBA
                            img = Image.fromarray(array, 'RGBA')
                            img.save(output_path)
                            print(f"Texture converted as BGRA: {output_path}")
                            return output_path
                        except Exception as e2:
                            print(f"Error converting as BGRA: {e2}")
                
                # If we can't extract image data, create a pattern visualization
                print(f"Creating pattern visualization based on binary data for {nutexb_path}")
                pattern_img = Image.new('RGB', (width, height), color=(40, 40, 40))
                draw = ImageDraw.Draw(pattern_img)
                
                # Create a visual pattern from the binary data
                for y in range(0, height, 8):
                    for x in range(0, width, 8):
                        idx = (y * width + x) % len(data)
                        r = data[idx % len(data)]
                        g = data[(idx + 1) % len(data)]
                        b = data[(idx + 2) % len(data)]
                        draw.rectangle([(x, y), (x+7, y+7)], fill=(r, g, b))
                
                # Add information
                draw.text((10, 10), f"VISUALIZATION {nutexb_path}", fill=(255, 255, 255))
                draw.text((10, 30), f"File: {os.path.basename(nutexb_path)}", fill=(200, 200, 255))
                draw.text((10, 50), f"Dimensions: {width}x{height}", fill=(200, 255, 200))
                draw.text((10, 70), f"Header: {data[:4]}", fill=(255, 255, 155))
                
                pattern_img.save(output_path)
                print(f"Pattern visualization created: {output_path}")
                return output_path
                
            except Exception as binary_error:
                print(f"Error processing binary data: {binary_error}")
            
            # Fallback method: Create informative image
            info_img = Image.new('RGB', (512, 384), color=(40, 40, 40))
            draw = ImageDraw.Draw(info_img)
            
            # Title
            draw.text((20, 20), "NUTEXB TEXTURE VISUALIZATION", fill=(255, 255, 100))
            draw.text((20, 50), os.path.basename(nutexb_path), fill=(200, 200, 255))
            
            # Informative message
            draw.text((20, 90), "Could not interpret the texture", fill=(255, 100, 100))
            draw.text((20, 120), "Recommendations:", fill=(200, 255, 200))
            draw.text((20, 150), "1. Install ultimate_tex_cli for better visualization", fill=(255, 255, 255))
            draw.text((20, 170), "   (https://github.com/ScanMountGoat/ultimate_tex)", fill=(200, 200, 255))
            draw.text((20, 190), "2. Use Switch Toolbox for NUTEXB files", fill=(255, 255, 255))
            
            # File information
            try:
                file_size = os.path.getsize(nutexb_path)
                draw.text((20, 230), f"File size: {file_size} bytes", fill=(255, 255, 255))
                
                # Show the first bytes as diagnostics
                with open(nutexb_path, 'rb') as f:
                    header = f.read(32)
                header_bytes = " ".join([f"{b:02X}" for b in header[:16]])
                draw.text((20, 250), f"Header: {header_bytes}", fill=(200, 255, 200))
                
                # Attempt to show the format
                format_hint = "Unknown"
                if header[8:12] == b'\x01\x00\x00\x00':
                    format_hint = "Possible BC7"
                elif header[8:12] == b'\x16\x00\x00\x00':
                    format_hint = "Possible BC1"
                draw.text((20, 270), f"Suggested format: {format_hint}", fill=(255, 200, 100))
                
            except Exception as e:
                draw.text((20, 230), f"Error reading file: {str(e)}", fill=(255, 100, 100))
            
            info_img.save(output_path)
            print(f"Informative image created: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"General error: {str(e)}")
            
            # Last resort: create error image
            try:
                # Re-import PIL in case the exception occurred before
                from PIL import Image, ImageDraw
                
                error_img = Image.new('RGB', (512, 200), color=(60, 0, 0))
                draw = ImageDraw.Draw(error_img)
                
                # Error message
                draw.text((20, 20), "CONVERSION ERROR", fill=(255, 50, 50))
                draw.text((20, 50), os.path.basename(nutexb_path), fill=(200, 200, 255))
                draw.text((20, 80), f"Error: {str(e)}", fill=(255, 255, 255))
                
                # Output
                if output_dir is None:
                    output_dir = tempfile.mkdtemp()
                    
                base_name = f"error_{os.path.basename(nutexb_path).split('.')[0]}_{str(uuid.uuid4())[:6]}.png"
                output_path = os.path.join(output_dir, base_name)
                
                error_img.save(output_path)
                return output_path
            except Exception as inner_e:
                print(f"Critical error creating error image: {inner_e}")
                return None

    def are_nutexb_files_identical(self, file1: str, file2: str) -> bool:
        """
        Compares two NUTEXB files to check if they are identical
        Uses image comparison since binary comparison may fail for NUTEXB files
        
        Args:
            file1: Path to the first NUTEXB file
            file2: Path to the second NUTEXB file
            
        Returns:
            True if the files are visually identical, False otherwise
        """
        if not NUTEXB_COMPARISON_AVAILABLE:
            print("NUTEXB comparison not available: PIL and/or numpy not installed")
            return False
        
        try:
            # Create temporary directories for conversion
            temp_dir1 = tempfile.mkdtemp()
            temp_dir2 = tempfile.mkdtemp()
            
            try:
                # Convert NUTEXB to PNG for comparison
                png1_path = self.nutexb_to_png(file1, temp_dir1)
                png2_path = self.nutexb_to_png(file2, temp_dir2)
                
                if not png1_path or not png2_path:
                    return False
                
                # Load images for comparison
                img1 = Image.open(png1_path)
                img2 = Image.open(png2_path)
                
                # Ensure both images have the same size for comparison
                if img1.size != img2.size:
                    # Resize the smaller one to the size of the larger
                    width = max(img1.width, img2.width)
                    height = max(img1.height, img2.height)
                    
                    if img1.width < width or img1.height < height:
                        img1 = img1.resize((width, height), Image.LANCZOS)
                    
                    if img2.width < width or img2.height < height:
                        img2 = img2.resize((width, height), Image.LANCZOS)
                
                # Ensure both images are in the same mode
                if img1.mode != img2.mode:
                    if "A" in img1.mode or "A" in img2.mode:
                        if img1.mode != "RGBA":
                            img1 = img1.convert("RGBA")
                        if img2.mode != "RGBA":
                            img2 = img2.convert("RGBA")
                    else:
                        img1 = img1.convert("RGB")
                        img2 = img2.convert("RGB")
                
                # Calculate difference
                diff_img = ImageChops.difference(img1, img2)
                diff_array = np.array(diff_img)
                
                # Use extremely aggressive comparison
                # Any pixel with any difference at all is considered different
                if len(diff_array.shape) > 1 and diff_array.shape[2] > 1:
                    # For images with multiple channels
                    mask = np.sum(diff_array, axis=2) > 15  # Reduced from 30 to 1 - extremely sensitive to any difference
                else:
                    # For grayscale images
                    mask = diff_array > 15  # Reduced from 30 to 1
                
                # Calculate similarity percentage
                total_pixels = mask.size
                diff_pixels = np.sum(mask)
                
                # If any pixels are different, return False
                if diff_pixels > 0:
                    print(f"Files differ by {diff_pixels} pixels out of {total_pixels}")
                    return False
                
                # Only return True if the images are 100% identical
                return True
                
            finally:
                # Clean up temporary directories
                shutil.rmtree(temp_dir1, ignore_errors=True)
                shutil.rmtree(temp_dir2, ignore_errors=True)
                
        except Exception as e:
            print(f"Error comparing NUTEXB files: {e}")
            return False

    def compare_nutexb_files(self, main_slot: str, compare_slot: str) -> List[str]:
        """
        Compares NUTEXB files between two slots and finds identical textures
        
        Args:
            main_slot: Main slot to use as reference
            compare_slot: Slot to compare with the main
            
        Returns:
            List of duplicate NUTEXB files in the compared slot
        """
        if main_slot == compare_slot:
            print(f"Error: Cannot compare the same slot ({main_slot})")
            return []
        
        print(f"Comparing NUTEXB files between {main_slot} and {compare_slot}...")
        
        # Find all NUTEXB files
        main_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name, "model", "body", main_slot)
        compare_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name, "model", "body", compare_slot)
        
        if not os.path.exists(main_dir):
            print(f"Main slot directory does not exist: {main_dir}")
            return []
        
        if not os.path.exists(compare_dir):
            print(f"Compare slot directory does not exist: {compare_dir}")
            return []
        
        # Get all NUTEXB files
        main_files = self.find_nutexb_files(main_dir)
        compare_files = self.find_nutexb_files(compare_dir)
        
        print(f"Found {len(main_files)} NUTEXB files in {main_slot}")
        print(f"Found {len(compare_files)} NUTEXB files in {compare_slot}")
        
        # Find identical files
        duplicates = []
        
        # For each file in the secondary slot
        for compare_file in compare_files:
            # Try to find a matching file in the main slot
            compare_basename = os.path.basename(compare_file)
            
            # First check for file with the same name
            matching_file = None
            for main_file in main_files:
                if os.path.basename(main_file) == compare_basename:
                    matching_file = main_file
                    break
            
            # If no match by name, continue
            if not matching_file:
                continue
            
            # Compare the files
            if self.are_nutexb_files_identical(matching_file, compare_file):
                duplicates.append(compare_file)
                print(f"Duplicate found: {compare_file}")
        
        print(f"Found {len(duplicates)} duplicate NUTEXB files")
        return duplicates

    def optimize_nutexb_files(self, main_slot: str, compare_slot: str) -> List[str]:
        """
        Optimizes NUTEXB files by moving duplicates to the junk folder
        and updating config.json
        
        Args:
            main_slot: Main slot to use as reference
            compare_slot: Slot to optimize
            
        Returns:
            List of moved files
        """
        duplicates = self.compare_nutexb_files(main_slot, compare_slot)
        
        if not duplicates:
            print(f"No duplicate NUTEXB files found between {main_slot} and {compare_slot}")
            return []
        
        if self.simulation:
            print(f"Simulation mode: Would move {len(duplicates)} NUTEXB files to junk")
            return duplicates
        
        # Track affected directories for later cleanup
        affected_directories = set()
        
        # Move duplicates to junk
        moved_files = []
        for file_path in duplicates:
            # Track the directory for later cleanup
            affected_directories.add(os.path.dirname(file_path))
            
            # Create path in junk directory
            rel_path = os.path.relpath(file_path, self.mod_directory)
            junk_path = os.path.join(self.junk_dir, rel_path)
            junk_dir = os.path.dirname(junk_path)
            
            # Create destination directory if it doesn't exist
            if not os.path.exists(junk_dir):
                os.makedirs(junk_dir)
            
            # Move file
            try:
                shutil.move(file_path, junk_path)
                moved_files.append(rel_path)
                print(f"Moved: {rel_path}")
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
        
        # Update config.json
        if moved_files:
            # Create mapping for update_share_to_added
            duplicate_files_by_slot = {compare_slot: moved_files}
            self.update_share_to_added(main_slot, duplicate_files_by_slot)
        
        # Clean up empty directories
        if affected_directories:
            print("\nChecking for empty directories...")
            fighter_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name)
            if os.path.exists(fighter_dir):
                self.remove_empty_directories(fighter_dir)
        
        return moved_files

    def compare_all_nutexb_slots(self) -> Dict[str, List[str]]:
        """
        Compares NUTEXB files between the main slot and all other slots
        
        Returns:
            Dictionary with duplicate files by slot
        """
        slots = self.detect_slots()
        if not slots:
            print(f"No slots found for fighter {self.fighter_name}")
            return {}
        
        # Determine main slot
        main_slot = None
        if self.user_main_slot and self.user_main_slot in slots:
            main_slot = self.user_main_slot
        else:
            # Use first slot as main
            main_slot = slots[0]
        
        print(f"Using {main_slot} as main slot for {self.fighter_name}")
        
        # Analyze each alternative slot
        result = {}
        for slot in [s for s in slots if s != main_slot]:
            print(f"\nComparing NUTEXB files between {main_slot} and {slot}...")
            
            duplicates = self.compare_nutexb_files(main_slot, slot)
            
            if duplicates:
                result[slot] = duplicates
                print(f"Found {len(duplicates)} duplicate NUTEXB files in {slot}")
            else:
                print(f"No duplicate NUTEXB files found between {main_slot} and {slot}")
        
        # Show summary
        total_duplicates = sum(len(files) for files in result.values())
        if total_duplicates > 0:
            print(f"\nSummary: {total_duplicates} NUTEXB duplicate files found in total")
            # Show number of duplicates by slot
            for slot, files in result.items():
                print(f"  Slot {slot}: {len(files)} duplicate NUTEXB files")
        else:
            print("\nNo duplicate NUTEXB files found in any slot")
        
        return result

    def optimize_all_nutexb_slots(self) -> Dict[str, List[str]]:
        """
        Optimizes NUTEXB files for all slots compared to the main slot
        
        Returns:
            Dictionary with optimized files by slot
        """
        # Get duplicates from all slots
        duplicates = self.compare_all_nutexb_slots()
        
        if not duplicates:
            print("No duplicate NUTEXB files found to optimize")
            return {}
        
        # Determine main slot
        slots = self.detect_slots()
        main_slot = None
        if self.user_main_slot and self.user_main_slot in slots:
            main_slot = self.user_main_slot
        else:
            # Use first slot as main
            main_slot = slots[0]
        
        # In simulation mode, just return duplicates
        if self.simulation:
            print(f"Simulation mode: Would move {sum(len(files) for files in duplicates.values())} NUTEXB files to junk")
            return duplicates
        
        # Track affected directories for later cleanup
        affected_directories = set()
        
        # Otherwise, move files and update config
        result = {}
        for slot, files in duplicates.items():
            moved_files = []
            for file_path in files:
                # Track the directory for later cleanup
                affected_directories.add(os.path.dirname(file_path))
                
                # Create path in junk directory
                rel_path = os.path.relpath(file_path, self.mod_directory)
                junk_path = os.path.join(self.junk_dir, rel_path)
                junk_dir = os.path.dirname(junk_path)
                
                # Create destination directory if it doesn't exist
                if not os.path.exists(junk_dir):
                    os.makedirs(junk_dir)
                
                # Move file
                try:
                    shutil.move(file_path, junk_path)
                    moved_files.append(rel_path)
                    print(f"Moved: {rel_path}")
                except Exception as e:
                    print(f"Error moving {file_path}: {e}")
            
            if moved_files:
                result[slot] = moved_files
        
        # Update config.json with all moved files
        if result:
            print("\nUpdating config.json with shared NUTEXB files...")
            if self.update_share_to_added(main_slot, result):
                print("config.json updated successfully with shared NUTEXB files")
            else:
                print("Error updating config.json")
        
        # Clean up empty directories
        if affected_directories:
            print("\nChecking for empty directories...")
            fighter_dir = os.path.join(self.mod_directory, "fighter", self.fighter_name)
            if os.path.exists(fighter_dir):
                self.remove_empty_directories(fighter_dir)
        
        return result

    def remove_empty_directories(self, path: str):
        """
        Recursively remove empty directories starting from the given path
        
        Args:
            path: Path to check and potentially remove
        """
        if self.simulation:
            # In simulation mode, just report but don't delete
            is_empty = True
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    # Check if this subdirectory is empty
                    if not self.remove_empty_directories(item_path):
                        is_empty = False
                else:
                    # Has a file, not empty
                    is_empty = False
                    
            if is_empty:
                print(f"Simulation: Would remove empty directory: {path}")
            return is_empty
        else:
            try:
                # Real mode - actually delete empty directories
                is_empty = True
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        # Check if this subdirectory is empty
                        if not self.remove_empty_directories(item_path):
                            is_empty = False
                    else:
                        # Has a file, not empty
                        is_empty = False
                        
                if is_empty:
                    print(f"Removing empty directory: {path}")
                    os.rmdir(path)
                return is_empty
            except Exception as e:
                print(f"Error checking/removing directory {path}: {e}")
                return False


def main():
    parser = argparse.ArgumentParser(description="Moveset optimizer for Super Smash Bros. Ultimate mods")
    parser.add_argument("mod_directory", help="Directory of the mod to optimize")
    parser.add_argument("--fighter", help="Fighter name (optional, will be auto-detected)")
    parser.add_argument("--main-slot", help="Main slot to use as reference (optional)")
    parser.add_argument("--compare-slot", help="Specific slot to compare with the main")
    parser.add_argument("--simulate", action="store_true", help="Simulate optimization without making real changes")
    parser.add_argument("--debug", action="store_true", help="Activate debug messages")
    parser.add_argument("--list-slots", action="store_true", help="Show the slots available in the mod")
    
    args = parser.parse_args()
    print(f"Received arguments: {args}")
    
    try:
        print(f"Initializing optimizer with directory: {args.mod_directory}")
        optimizer = MovesetOptimizer(
            args.mod_directory, 
            fighter_name=args.fighter,
            main_slot=args.main_slot,
            simulation=args.simulate
        )
        
        # Show available slots
        if args.list_slots:
            slots = optimizer.detect_slots()
            if slots:
                fighter = optimizer.fighter_name
                print(f"Slots available for {fighter}:")
                for slot in slots:
                    print(f"  - {slot}")
            else:
                print("No slots available")
            return
        
        # Specific comparison between slots
        if args.main_slot and args.compare_slot:
            print(f"Comparing slots {args.main_slot} and {args.compare_slot}...")
            
            if args.simulate:
                print("Mode: Simulation (no real changes will be made)")
                duplicates = optimizer.compare_specific_slots(args.main_slot, args.compare_slot)
                
                if duplicates:
                    print(f"\nFound {len(duplicates)} duplicate files in {args.compare_slot}:")
                    if args.debug:
                        for file in duplicates:
                            print(f"  - {file}")
                    print(f"\nTotal: {len(duplicates)} duplicate files found")
                else:
                    print(f"No duplicate files found between {args.main_slot} and {args.compare_slot}")
            else:
                print("Optimizing...")
                moved_files = optimizer.optimize_specific_slot(args.main_slot, args.compare_slot)
                
                if moved_files:
                    print(f"\nMoved {len(moved_files)} duplicate files to 'junk':")
                    if args.debug:
                        for file in moved_files:
                            print(f"  - {file}")
                    print(f"\nTotal: {len(moved_files)} files moved to 'junk'")
                else:
                    print(f"No duplicate files found between {args.main_slot} and {args.compare_slot}")
            
            return
        
        # Analysis/optimization general
        if args.simulate:
            print(f"Simulating optimization for {args.mod_directory}...")
            duplicates = optimizer.analyze_mod()
            
            total_files = 0
            for slot, files in duplicates.items():
                print(f"  Slot {slot}: {len(files)} duplicate files")
                if args.debug:
                    for file in files:
                        print(f"    - {file}")
                total_files += len(files)
                
            print(f"Total: {total_files} duplicate files found")
            
        else:
            print(f"Optimizing mod in {args.mod_directory}...")
            result = optimizer.optimize_mod()
            
            total_files = 0
            for slot, files in result.items():
                print(f"  Slot {slot}: {len(files)} files moved to 'junk'")
                if args.debug:
                    for file in files:
                        print(f"    - {file}")
                total_files += len(files)
                
            print(f"Optimization completed. {total_files} files moved to 'junk'")
            
    except Exception as e:
        if args.debug:
            traceback.print_exc()
        else:
            print(f"Error: {str(e)}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 