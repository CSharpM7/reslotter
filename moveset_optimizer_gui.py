import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from typing import Optional, List, Dict, Any
import traceback
import webbrowser
import subprocess

# Import the movesets optimizer
from moveset_optimizer import MovesetOptimizer

def check_ultimate_tex_cli():
    """Check if ultimate_tex_cli is available and provide download link if not"""
    try:
        result = subprocess.run(["ultimate_tex_cli", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True, shell=True)
        
        if not ("ultimate_tex_cli" in str(result.stdout) or "ultimate_tex_cli" in str(result.stderr)):
            raise FileNotFoundError("ultimate_tex_cli not found")
            
    except Exception:
        response = messagebox.askquestion("Missing Dependency",
            "ultimate_tex_cli.exe was not found. This tool is required for texture conversion.\n\n"
            "Would you like to open the download page?\n\n"
            "After downloading, place ultimate_tex_cli.exe in the same folder as this program.",
            icon='warning')
            
        if response == 'yes':
            webbrowser.open('https://github.com/ScanMountGoat/ultimate_tex/releases')
        return False
    return True

class MovesetOptimizerGUI:
    def __init__(self, root):
        """
        Initializes the graphical interface for the movesets optimizer
        
        Args:
            root: Root of the tkinter interface
        """
        self.root = root
        self.root.title("Moveset Optimizer - Smash Ultimate")
        self.root.geometry("700x600")
        self.root.minsize(600, 500)
        
        # Set window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.quit_application)
        
        # Variables
        self.mod_path_var = tk.StringVar()
        self.fighter_name = tk.StringVar()
        self.main_slot = tk.StringVar()
        self.compare_slot = tk.StringVar()
        self.simulate_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.optimizer = None
        self.available_slots = []
        self.fitx_path_var = tk.StringVar()
        
        # Check for ultimate_tex_cli
        self.has_ultimate_tex_cli = self.check_ultimate_tex_cli()
        
        # Configure the interface
        self.setup_ui()
        
    def check_ultimate_tex_cli(self):
        """Check if ultimate_tex_cli.exe exists in the same directory as the program"""
        # Get the directory where the script is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ultimate_tex_cli_path = os.path.join(current_dir, "ultimate_tex_cli.exe")
        
        # Check if the file exists
        return os.path.exists(ultimate_tex_cli_path)

    def setup_ui(self):
        """Configures all interface elements"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create menubar
        self.menubar = tk.Menu(self.root)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Open Mod Folder", command=self.browse_directory)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Exit", command=self.quit_application)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        
        # Add Help menu
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label="Open README", command=self.open_readme)
        self.menubar.add_cascade(label="Help", menu=self.helpmenu)
        
        self.root.config(menu=self.menubar)
        
        # Directory section
        dir_frame = ttk.LabelFrame(main_frame, text="Mod Directory", padding="5")
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(dir_frame, textvariable=self.mod_path_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_frame, text="Detect Slots", command=self.detect_slots).pack(side=tk.LEFT, padx=5)
        
        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Fighter
        fighter_frame = ttk.Frame(options_frame)
        fighter_frame.pack(fill=tk.X, pady=2)
        ttk.Label(fighter_frame, text="Fighter:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(fighter_frame, textvariable=self.fighter_name).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(fighter_frame, text="(optional, will auto-detect)").pack(side=tk.LEFT, padx=5)
        
        # Main slot
        slot_frame = ttk.Frame(options_frame)
        slot_frame.pack(fill=tk.X, pady=2)
        ttk.Label(slot_frame, text="Main slot:").pack(side=tk.LEFT, padx=5)
        self.main_slot_combo = ttk.Combobox(slot_frame, textvariable=self.main_slot, width=10, state="readonly")
        self.main_slot_combo.pack(side=tk.LEFT, padx=5)
        
        # Comparison slot
        compare_frame = ttk.Frame(options_frame)
        compare_frame.pack(fill=tk.X, pady=2)
        ttk.Label(compare_frame, text="Compare slot:").pack(side=tk.LEFT, padx=5)
        self.compare_slot_combo = ttk.Combobox(compare_frame, textvariable=self.compare_slot, width=10, state="readonly")
        self.compare_slot_combo.pack(side=tk.LEFT, padx=5)
        
        # Simulation mode
        sim_frame = ttk.Frame(options_frame)
        sim_frame.pack(fill=tk.X, pady=2)
        ttk.Checkbutton(sim_frame, text="Simulation mode (don't make actual changes)", 
                         variable=self.simulate_var).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Compare Selected Slots", 
                   command=lambda: self.run_task(self.compare_selected_slots)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Optimize Selected Slot", 
                   command=lambda: self.run_task(self.optimize_selected_slot)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Analyze All", 
                   command=lambda: self.run_task(self.analyze_mod)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Optimize All", 
                   command=lambda: self.run_task(self.optimize_mod)).pack(side=tk.LEFT, padx=5)
        
        # NUTEXB Comparison section
        texture_frame = ttk.LabelFrame(main_frame, text="NUTEXB Textures", padding="5")
        texture_frame.pack(fill=tk.X, pady=5)
        
        # If ultimate_tex_cli is not available, add a notification label
        if not self.has_ultimate_tex_cli:
            req_frame = ttk.Frame(texture_frame)
            req_frame.pack(fill=tk.X, pady=(0, 5))
            
            ttk.Label(req_frame, text="Requires ", font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT)
            
            link_label = ttk.Label(req_frame, text="ultimate_tex_cli", 
                                 foreground="blue", cursor="hand2", font=("TkDefaultFont", 9, "bold"))
            link_label.pack(side=tk.LEFT)
            link_label.bind("<Button-1>", self.open_ultimate_tex_cli_download)

        nutexb_button_frame = ttk.Frame(texture_frame)
        nutexb_button_frame.pack(fill=tk.X, pady=2)
        
        # Create buttons with state based on ultimate_tex_cli availability
        button_state = "normal" if self.has_ultimate_tex_cli else "disabled"
        
        ttk.Button(nutexb_button_frame, text="Compare NUTEXB Files", 
                   command=lambda: self.run_task(self.compare_nutexb_slots),
                   state=button_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(nutexb_button_frame, text="Optimize NUTEXB Files", 
                   command=lambda: self.run_task(self.optimize_nutexb_slots),
                   state=button_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(nutexb_button_frame, text="Compare All NUTEXB", 
                   command=lambda: self.run_task(self.compare_all_nutexb_slots),
                   state=button_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(nutexb_button_frame, text="Optimize All NUTEXB", 
                   command=lambda: self.run_task(self.optimize_all_nutexb_slots),
                   state=button_state).pack(side=tk.LEFT, padx=5)
        
        # Results area
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.result_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, width=80, height=20)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def browse_directory(self):
        """Opens a dialog to select the mod directory"""
        directory = filedialog.askdirectory(title="Select mod directory")
        if directory:
            self.mod_path_var.set(directory)
            # Automatically detect slots when a directory is selected
            self.detect_slots()
    
    def detect_slots(self):
        """Detects available slots in the selected mod"""
        if not self.mod_path_var.get():
            messagebox.showerror("Error", "Please select a valid mod directory")
            return
            
        if not os.path.exists(self.mod_path_var.get()):
            messagebox.showerror("Error", f"The directory {self.mod_path_var.get()} does not exist")
            return
            
        try:
            # Create temporary optimizer to detect slots
            temp_optimizer = MovesetOptimizer(
                self.mod_path_var.get(),
                fighter_name=self.fighter_name.get() or None,
                simulation=True
            )
            
            # Get slots
            self.available_slots = temp_optimizer.detect_slots()
            
            if not self.available_slots:
                messagebox.showinfo("Information", "No slots found in the selected mod")
                return
                
            # Update comboboxes
            self.main_slot_combo['values'] = self.available_slots
            self.compare_slot_combo['values'] = self.available_slots
            
            # Select defaults
            if self.available_slots:
                self.main_slot.set(self.available_slots[0])
                if len(self.available_slots) > 1:
                    self.compare_slot.set(self.available_slots[1])
                    
            # Show information
            self.log(f"Slots detected for {temp_optimizer.fighter_name}:")
            for slot in self.available_slots:
                self.log(f"  - {slot}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error detecting slots: {str(e)}")
            
    def log(self, message: str):
        """
        Adds a message to the results area
        
        Args:
            message: Message to add
        """
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        self.result_text.update_idletasks()
        
    def clear_log(self):
        """Clears the results area"""
        self.result_text.delete(1.0, tk.END)
        
    def set_status(self, message: str):
        """
        Updates the status bar
        
        Args:
            message: Message to display
        """
        self.status_var.set(message)
        
    def run_task(self, task_func):
        """
        Executes a task in a separate thread
        
        Args:
            task_func: Function to execute
        """
        if self.is_running:
            messagebox.showwarning("Operation in progress", 
                                   "An operation is already in progress. Please wait for it to finish.")
            return
            
        # Validate directory
        if not self.mod_path_var.get():
            messagebox.showerror("Error", "Please select a valid mod directory")
            return
            
        if not os.path.exists(self.mod_path_var.get()):
            messagebox.showerror("Error", f"The directory {self.mod_path_var.get()} does not exist")
            return
            
        # Start thread
        self.is_running = True
        self.set_status("Running...")
        
        thread = threading.Thread(target=self._run_task_thread, args=(task_func,))
        thread.daemon = True
        thread.start()
        
    def _run_task_thread(self, task_func):
        """
        Internal function to execute the task in a thread
        
        Args:
            task_func: Function to execute
        """
        try:
            # Redirect stdout to the interface
            original_stdout = sys.stdout
            
            class StdoutRedirector:
                def __init__(self, text_widget):
                    self.text_widget = text_widget
                    
                def write(self, string):
                    self.text_widget.insert(tk.END, string)
                    self.text_widget.see(tk.END)
                    self.text_widget.update_idletasks()
                    
                def flush(self):
                    pass
                    
            sys.stdout = StdoutRedirector(self.result_text)
            
            # Clear log
            self.root.after(0, self.clear_log)
            
            # Create optimizer
            self.optimizer = MovesetOptimizer(
                self.mod_path_var.get(),
                fighter_name=self.fighter_name.get() or None,
                main_slot=self.main_slot.get() or None,
                simulation=self.simulate_var.get()
            )
            
            # Execute task
            task_func()
            
            # Update status
            self.root.after(0, lambda: self.set_status("Ready"))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.log(f"\n{error_msg}")
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.set_status("Error"))
            
        finally:
            # Restore stdout
            sys.stdout = original_stdout
            self.is_running = False
    
    def compare_selected_slots(self):
        """Compares the slots selected in the interface"""
        if not self.optimizer:
            return
            
        # Verify that slots have been selected
        main_slot = self.main_slot.get()
        compare_slot = self.compare_slot.get()
        
        if not main_slot or not compare_slot:
            self.log("Error: You must select slots to compare")
            return
            
        if main_slot == compare_slot:
            self.log("Error: Cannot compare a slot with itself")
            return
            
        self.log(f"Comparing slots: {main_slot} (main) with {compare_slot}")
        if self.simulate_var.get():
            self.log("Mode: Simulation (analysis only)\n")
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
        
        # Compare slots
        duplicates = self.optimizer.compare_specific_slots(main_slot, compare_slot)
        
        # Show results
        if not duplicates:
            self.log(f"\nNo duplicate files found between {main_slot} and {compare_slot}")
            return
            
        self.log(f"\nFound {len(duplicates)} duplicate files in {compare_slot}:")
        for file in duplicates[:10]:  # Show only the first 10 to avoid clutter
            self.log(f"  - {file}")
            
        if len(duplicates) > 10:
            self.log(f"  - ... and {len(duplicates) - 10} more files")
            
        self.log(f"\nTotal: {len(duplicates)} duplicate files found")
        
        if self.simulate_var.get():
            self.log("\nThis was just a simulation. To apply the changes, " 
                     "disable 'Simulation mode' and click 'Optimize Selected Slot'.")
    
    def compare_nutexb_slots(self):
        """Compares NUTEXB textures between selected slots"""
        if not self.optimizer:
            return
        
        # Verify that slots have been selected
        main_slot = self.main_slot.get()
        compare_slot = self.compare_slot.get()
        
        if not main_slot or not compare_slot:
            self.log("Error: You must select slots to compare")
            return
            
        if main_slot == compare_slot:
            self.log("Error: Cannot compare a slot with itself")
            return
            
        self.log(f"Comparing NUTEXB textures: {main_slot} (main) with {compare_slot}")
        if self.simulate_var.get():
            self.log("Mode: Simulation (analysis only)\n")
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
        
        # Compare NUTEXB files
        duplicates = self.optimizer.compare_nutexb_files(main_slot, compare_slot)
        
        # Show results
        if not duplicates:
            self.log(f"\nNo duplicate NUTEXB files found between {main_slot} and {compare_slot}")
            return
            
        self.log(f"\nFound {len(duplicates)} duplicate NUTEXB files in {compare_slot}:")
        # Show all files without truncation
        for file in duplicates:
            self.log(f"  - {os.path.basename(file)}")
            
        self.log(f"\nTotal: {len(duplicates)} duplicate NUTEXB files found")
        
        if self.simulate_var.get():
            self.log("\nThis was just a simulation. To apply the changes, " 
                     "disable 'Simulation mode' and click 'Optimize NUTEXB Files'.")
    
    def optimize_nutexb_slots(self):
        """Optimizes NUTEXB textures between selected slots"""
        if not self.optimizer:
            return
        
        # Verify that slots have been selected
        main_slot = self.main_slot.get()
        compare_slot = self.compare_slot.get()
        
        if not main_slot or not compare_slot:
            self.log("Error: You must select slots to compare")
            return
            
        if main_slot == compare_slot:
            self.log("Error: Cannot compare a slot with itself")
            return
            
        self.log(f"Optimizing NUTEXB textures: {compare_slot} comparing with {main_slot} (main)")
        
        if self.simulate_var.get():
            self.log("Mode: Simulation (no real changes will be made)\n")
            
            # Simulate optimization
            duplicates = self.optimizer.compare_nutexb_files(main_slot, compare_slot)
            
            if not duplicates:
                self.log(f"\nNo duplicate NUTEXB files found between {main_slot} and {compare_slot}")
                return
                
            self.log(f"\nWould move {len(duplicates)} duplicate NUTEXB files to 'junk':")
            # Show all files without truncation
            for file in duplicates:
                self.log(f"  - {os.path.basename(file)}")
                
            self.log(f"\nSimulation completed. {len(duplicates)} NUTEXB files would be moved to 'junk'")
            self.log("\nTo apply the changes, disable 'Simulation mode' and click 'Optimize NUTEXB Files'")
            
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
            
            # Confirm before making changes
            if not messagebox.askyesno("Confirm optimization", 
                                      f"Are you sure you want to optimize NUTEXB files in slot {compare_slot}? "
                                      f"Duplicate files will be moved to the 'junk' folder.\n\n"
                                      "Making a backup is recommended before continuing."):
                self.log("\nOperation canceled by user.")
                return
                
            # Perform optimization
            moved_files = self.optimizer.optimize_nutexb_files(main_slot, compare_slot)
            
            if not moved_files:
                self.log(f"\nNo duplicate NUTEXB files found between {main_slot} and {compare_slot}")
                return
                
            self.log(f"\n{len(moved_files)} duplicate NUTEXB files moved to 'junk':")
            # Show all files without truncation
            for file in moved_files:
                self.log(f"  - {file}")
                
            self.log(f"\nOptimization completed. {len(moved_files)} NUTEXB files moved to 'junk'")
            self.log("\nOriginal files have been saved in the 'junk' folder and "
                     "config.json has been updated to share the textures.")
    
    def optimize_selected_slot(self):
        """Optimizes the selected slot by comparing it with the main slot"""
        if not self.optimizer:
            return
            
        # Verify that slots have been selected
        main_slot = self.main_slot.get()
        compare_slot = self.compare_slot.get()
        
        if not main_slot or not compare_slot:
            self.log("Error: You must select slots to compare")
            return
            
        if main_slot == compare_slot:
            self.log("Error: Cannot compare a slot with itself")
            return
            
        self.log(f"Optimizing slot: {compare_slot} comparing with {main_slot} (main)")
        
        if self.simulate_var.get():
            self.log("Mode: Simulation (no real changes will be made)\n")
            
            # Simulate optimization
            duplicates = self.optimizer.compare_specific_slots(main_slot, compare_slot)
            
            if not duplicates:
                self.log(f"\nNo duplicate files found between {main_slot} and {compare_slot}")
                return
                
            self.log(f"\nWould move {len(duplicates)} duplicate files to 'junk':")
            for file in duplicates[:10]:  # Show only the first 10
                self.log(f"  - {file}")
                
            if len(duplicates) > 10:
                self.log(f"  - ... and {len(duplicates) - 10} more files")
                
            self.log(f"\nSimulation completed. {len(duplicates)} files would be moved to 'junk'")
            self.log("\nTo apply the changes, disable 'Simulation mode' and click 'Optimize Selected Slot'")
            
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
            
            # Confirm before making changes
            if not messagebox.askyesno("Confirm optimization", 
                                      f"Are you sure you want to optimize slot {compare_slot}? "
                                      f"Duplicate files will be moved to the 'junk' folder.\n\n"
                                      "Making a backup is recommended before continuing."):
                self.log("\nOperation canceled by user.")
                return
                
            # Perform optimization
            moved_files = self.optimizer.optimize_specific_slot(main_slot, compare_slot)
            
            if not moved_files:
                self.log(f"\nNo duplicate files found between {main_slot} and {compare_slot}")
                return
                
            self.log(f"\n{len(moved_files)} duplicate files moved to 'junk':")
            for file in moved_files[:10]:  # Show only the first 10
                self.log(f"  - {file}")
                
            if len(moved_files) > 10:
                self.log(f"  - ... and {len(moved_files) - 10} more files")
                
            self.log(f"\nOptimization completed. {len(moved_files)} files moved to 'junk'")
            self.log("\nOriginal files have been saved in the 'junk' folder and "
                     "can be restored manually if needed.")
    
    def analyze_mod(self):
        """Analyzes the mod to find duplicates across all slots"""
        # Get mod directory
        mod_path = self.mod_path_var.get()
        if not mod_path or not os.path.exists(mod_path):
            messagebox.showerror("Error", "Select a valid mod directory")
            return
            
        # Get main slot (if selected)
        main_slot = self.main_slot.get()
        
        self.log(f"Analyzing complete mod: {mod_path}")
        
        # Create optimizer
        try:
            optimizer = MovesetOptimizer(mod_path, main_slot=main_slot, simulation=True)
            
            # Complete analysis
            self.log("Starting full analysis of all slots...")
            duplicates = optimizer.analyze_mod()
            
            total_duplicates = sum(len(files) for files in duplicates.values())
            
            if total_duplicates > 0:
                self.log(f"\nFound {total_duplicates} duplicate files in total")
                
                # Show results by slot
                for slot, files in duplicates.items():
                    self.log(f"  Slot {slot}: {len(files)} duplicate files")
                    
                    # Show some examples
                    max_to_show = min(5, len(files))
                    if max_to_show > 0:
                        self.log("  Examples:")
                        for i in range(max_to_show):
                            self.log(f"    - {files[i]}")
                        
                        if len(files) > max_to_show:
                            self.log(f"    ... and {len(files) - max_to_show} more files")
                
                result_text = f"Found {total_duplicates} duplicate files in total.\n\nIf you want to optimize the mod, select the slots and click 'Optimize Slots'."
                
            else:
                result_text = "No duplicate files found in the mod."
                self.log(result_text)
                
            messagebox.showinfo("Analysis Result", result_text)
                
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def optimize_mod(self):
        """Optimizes the entire mod by comparing all slots"""
        # Get mod directory
        mod_path = self.mod_path_var.get()
        if not mod_path or not os.path.exists(mod_path):
            messagebox.showerror("Error", "Select a valid mod directory")
            return
            
        # Get main slot (if selected)
        main_slot = self.main_slot.get()
        
        # Check if we're in simulation mode
        simulate = self.simulate_var.get()
        simulator_text = "SIMULATING" if simulate else "OPTIMIZING"
        
        self.log(f"{simulator_text} complete mod: {mod_path}")
        
        # Create optimizer
        try:
            optimizer = MovesetOptimizer(mod_path, main_slot=main_slot, simulation=simulate)
            
            # Optimize everything
            self.log("Starting complete optimization...")
            
            if simulate:
                # Analysis only
                duplicates = optimizer.analyze_mod()
                
                total_duplicates = sum(len(files) for files in duplicates.values())
                
                if total_duplicates > 0:
                    self.log(f"\nFound {total_duplicates} duplicate files in total")
                    
                    # Show results by slot
                    for slot, files in duplicates.items():
                        self.log(f"  Slot {slot}: {len(files)} duplicate files")
                    
                    result_text = f"Found {total_duplicates} duplicate files in total.\n\nNOTE: No real changes were made in simulation mode. Uncheck 'Simulation mode' to apply changes and update config.json."
                    
                else:
                    result_text = "No duplicate files found to optimize."
                    self.log(result_text)
            else:
                # Optimize
                results = optimizer.optimize_mod()
                
                total_moved = sum(len(files) for files in results.values())
                
                if total_moved > 0:
                    self.log(f"\nOptimized {total_moved} duplicate files in total")
                    
                    # Show results by slot
                    for slot, files in results.items():
                        self.log(f"  Slot {slot}: {len(files)} files moved to 'junk'")
                        
                    result_text = f"Optimization completed. {total_moved} duplicate files moved to 'junk' and config.json updated with shared files."
                else:
                    result_text = "No duplicate files found to optimize."
                    self.log(result_text)
            
            messagebox.showinfo("Optimization Result", result_text)
                
        except Exception as e:
            error_msg = f"Error during optimization: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def compare_all_nutexb_slots(self):
        """Compares NUTEXB textures between the main slot and all other slots"""
        if not self.optimizer:
            return
            
        self.log(f"Comparing all NUTEXB textures against main slot")
        if self.simulate_var.get():
            self.log("Mode: Simulation (analysis only)\n")
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
        
        # Compare NUTEXB files across all slots
        duplicates = self.optimizer.compare_all_nutexb_slots()
        
        # Show results
        if not duplicates:
            self.log(f"\nNo duplicate NUTEXB files found in any slots")
            return
            
        total_duplicates = sum(len(files) for files in duplicates.values())
        self.log(f"\nFound {total_duplicates} duplicate NUTEXB files across all slots:")
        
        # Show by slot, displaying all files without truncation
        for slot, files in duplicates.items():
            self.log(f"\nSlot {slot}: {len(files)} duplicate files")
            # Show all files
            for file in files:
                self.log(f"  - {os.path.basename(file)}")
            
        self.log(f"\nTotal: {total_duplicates} duplicate NUTEXB files found")
        
        if self.simulate_var.get():
            self.log("\nThis was just a simulation. To apply the changes, " 
                     "disable 'Simulation mode' and click 'Optimize All NUTEXB'")
    
    def optimize_all_nutexb_slots(self):
        """Optimizes NUTEXB textures across all slots by comparing with the main slot"""
        if not self.optimizer:
            return
            
        self.log(f"Optimizing all NUTEXB textures against main slot")
        
        if self.simulate_var.get():
            self.log("Mode: Simulation (no real changes will be made)\n")
            
            # Simulate optimization
            duplicates = self.optimizer.compare_all_nutexb_slots()
            
            if not duplicates:
                self.log(f"\nNo duplicate NUTEXB files found in any slots")
                return
                
            total_duplicates = sum(len(files) for files in duplicates.values())
            self.log(f"\nWould move {total_duplicates} duplicate NUTEXB files to 'junk':")
            
            # Show by slot, displaying all files without truncation
            for slot, files in duplicates.items():
                self.log(f"\nSlot {slot}: {len(files)} duplicate files")
                # Show all files
                for file in files:
                    self.log(f"  - {os.path.basename(file)}")
                
            self.log(f"\nSimulation completed. {total_duplicates} NUTEXB files would be moved to 'junk'")
            self.log("\nTo apply the changes, disable 'Simulation mode' and click 'Optimize All NUTEXB'")
            
        else:
            self.log("Mode: Real (files will be moved to 'junk')\n")
            
            # Confirm before making changes
            if not messagebox.askyesno("Confirm optimization", 
                                      f"Are you sure you want to optimize NUTEXB files across all slots? "
                                      f"Duplicate files will be moved to the 'junk' folder.\n\n"
                                      "Making a backup is recommended before continuing."):
                self.log("\nOperation canceled by user.")
                return
                
            # Perform optimization
            result = self.optimizer.optimize_all_nutexb_slots()
            
            if not result:
                self.log(f"\nNo duplicate NUTEXB files found in any slots")
                return
                
            total_moved = sum(len(files) for files in result.values())
            self.log(f"\n{total_moved} duplicate NUTEXB files moved to 'junk':")
            
            # Show by slot, displaying all files without truncation
            for slot, files in result.items():
                self.log(f"\nSlot {slot}: {len(files)} files moved")
                # Show all files
                for file in files:
                    self.log(f"  - {file}")
                
            self.log(f"\nOptimization completed. {total_moved} NUTEXB files moved to 'junk'")
            self.log("\nOriginal files have been saved in the 'junk' folder and "
                     "config.json has been updated to share the textures.")

    def open_ultimate_tex_cli_download(self, event=None):
        """Open the ultimate_tex_cli download page"""
        webbrowser.open('https://github.com/ScanMountGoat/ultimate_tex/releases')

    def open_readme(self):
        """Opens the README on GitHub"""
        webbrowser.open('https://github.com/CSharpM7/reslotter#readme')
        
    def quit_application(self):
        """Exits the application"""
        if self.is_running:
            if not messagebox.askyesno("Warning", "An operation is in progress. Are you sure you want to exit?"):
                return
        self.root.destroy()
        sys.exit(0)


def main():
    """Main entry point"""
    root = tk.Tk()
    app = MovesetOptimizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 