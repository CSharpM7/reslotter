import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import traceback
import time
import platform
import subprocess
import json
import shutil
import glob
from texture_analyzer import TextureAnalyzer, convert_numatb_to_json, convert_numdlb_to_text
import re

class TextureManagerApp:
    def __init__(self, root):
        """Initialize the Texture Manager application"""
        self.root = root
        self.root.title("Texture Manager")
        self.root.geometry("1400x850")
        
        # Set application icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Initialize variables
        self.mod_dir = ""
        self.selected_fighter = None
        self.selected_alt = None
        self.selected_optimizer_fighter = None
        self.selected_optimizer_alt = None
        
        # Configure styles
        style = ttk.Style()
        style.configure("TButton", padding=(5, 5))
        style.configure("TLabel", padding=(5, 5))
        style.configure("TFrame", padding=(5, 5))
        
        # Variables for analyzer
        self.mod_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value="texture_analysis")
        self.analyze_numdlb_var = tk.BooleanVar(value=True)
        self.analyze_txt_var = tk.BooleanVar(value=True)
        self.analyze_json_var = tk.BooleanVar(value=True)
        self.all_alts_var = tk.BooleanVar(value=False)
        self.show_details_var = tk.BooleanVar(value=True)
        self.selected_fighter_var = tk.StringVar()
        self.selected_alt_var = tk.StringVar()
        
        # Variables for optimizer
        self.junk_dir = None
        self.fighters = []
        self.fighters_alts = {}
        
        # Estado interno
        self.analyzer_thread = None
        self.mod_directory = None
        self.cancel_requested = False
        
        # Crear la interfaz
        self.setup_ui()
        
        # Disable tabs until a mod directory is selected
        self.notebook.tab(self.analyzer_tab, state="disabled")
        self.notebook.tab(self.optimizer_tab, state="disabled")
        
        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        # Marco principal
        main_frame = ttk.Frame(self.root, padding=(10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="Texture Manager for Smash Ultimate", 
                             font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Sección para seleccionar directorios
        dirs_frame = ttk.LabelFrame(main_frame, text="Directories", padding=(10, 5))
        dirs_frame.pack(fill=tk.X, pady=5)
        
        # Directorio del mod
        mod_dir_frame = ttk.Frame(dirs_frame)
        mod_dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mod_dir_frame, text="Mod directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(mod_dir_frame, textvariable=self.mod_dir_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(mod_dir_frame, text="Browse...", command=self.on_mod_dir_select).pack(side=tk.LEFT)
        ttk.Button(mod_dir_frame, text="Load", command=self.load_fighters).pack(side=tk.LEFT, padx=(5, 0))
        
        # Notebook con pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Crear las pestañas
        self.analyzer_tab = ttk.Frame(self.notebook)
        self.optimizer_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.analyzer_tab, text="NUMATB Analyzer")
        self.notebook.add(self.optimizer_tab, text="Texture Optimizer")
        
        # Configurar cada pestaña
        self.setup_analyzer_tab()
        self.setup_optimizer_tab()
        
        # Barra de progreso y estado (compartida)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, pady=(0, 2))
        
        self.progress_bar = ttk.Progressbar(status_frame, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X)
    
    def on_mod_dir_select(self):
        """Handle the selection of the mod directory"""
        directory = filedialog.askdirectory(title="Select Mod Directory")
        if directory:
            self.mod_dir = directory
            self.mod_dir_var.set(directory)
            
            # Create junk directory if it doesn't exist
            self.junk_dir = os.path.join(directory, "junk")
            os.makedirs(self.junk_dir, exist_ok=True)
            
            # Log to both consoles
            try:
                self.update_console(f"Mod directory set to: {directory}")
            except:
                pass
            
            try:
                self.log_to_optimizer(f"Mod directory set to: {directory}")
            except:
                pass
            
            # Clear previous data
            self.fighter_listbox.delete(0, tk.END)
            self.alt_listbox.delete(0, tk.END)
            self.optimizer_fighter_listbox.delete(0, tk.END)
            self.optimizer_alt_listbox.delete(0, tk.END)
            
            # Load fighters
            fighters = self.load_fighters()
            for fighter in fighters:
                self.fighter_listbox.insert(tk.END, fighter)
                self.optimizer_fighter_listbox.insert(tk.END, fighter)
            
            # Enable tabs if we have fighters
            if fighters:
                self.notebook.tab(self.analyzer_tab, state="normal")
                self.notebook.tab(self.optimizer_tab, state="normal")
                self.update_console(f"Loaded {len(fighters)} fighters")
                self.log_to_optimizer(f"Loaded {len(fighters)} fighters")
            else:
                self.update_console("No fighters found in the mod directory")
                self.log_to_optimizer("No fighters found in the mod directory")
    
    def load_fighters(self):
        """Load all fighters from the mod directory"""
        fighters = []
        fighter_path = os.path.join(self.mod_dir, "fighter")
        
        if not os.path.exists(fighter_path):
            messagebox.showwarning("Invalid Directory", "No fighter directory found in the selected mod directory.")
            return []
        
        for fighter in os.listdir(fighter_path):
            fighter_dir = os.path.join(fighter_path, fighter)
            if os.path.isdir(fighter_dir):
                model_dir = os.path.join(fighter_dir, "model")
                if os.path.exists(model_dir):
                    fighters.append(fighter)
        
        return sorted(fighters)
    
    def get_alts(self, fighter):
        """Get all available alts for a fighter"""
        alts = []
        body_path = os.path.join(self.mod_dir, "fighter", fighter, "model", "body")
        
        if os.path.exists(body_path):
            for alt in os.listdir(body_path):
                if alt.startswith("c") and alt[1:].isdigit():
                    alts.append(alt[1:])  # Remove the 'c' prefix
        
        return sorted(alts, key=int)
    
    def on_fighter_select(self, event):
        """Handle fighter selection in the analyzer tab"""
        selection = self.fighter_listbox.curselection()
        if not selection:
            return
        
        fighter = self.fighter_listbox.get(selection[0])
        self.selected_fighter_var.set(fighter)
        
        # Update alt list
        self.alt_listbox.delete(0, tk.END)
        alts = self.get_alts(fighter)
        for alt in alts:
            self.alt_listbox.insert(tk.END, alt)
    
    def on_alt_select(self, event):
        """Handle alt selection in the analyzer tab"""
        selection = self.alt_listbox.curselection()
        if not selection:
            return
        
        alt = self.alt_listbox.get(selection[0])
        self.selected_alt_var.set(alt)
    
    def start_analysis(self):
        """Start texture analysis process"""
        mod_dir = self.mod_dir_var.get()
        if not mod_dir or not os.path.exists(mod_dir):
            messagebox.showerror("Error", "Please select a valid mod directory.")
            return
        
        # Verify that it's a Smash mod
        fighter_dir = os.path.join(mod_dir, "fighter")
        if not os.path.exists(fighter_dir) or not os.path.isdir(fighter_dir):
            messagebox.showerror("Error", "The selected directory doesn't appear to be a valid Smash Ultimate mod.")
            return
        
        # Verify fighter/alt selection
        if not self.all_alts_var.get() and not self.selected_fighter_var.get():
            messagebox.showerror("Error", "You must select a fighter to analyze, or enable the 'Include all alts' option.")
            return
        
        # Verify alt selection
        if not self.all_alts_var.get() and not self.selected_alt_var.get() and self.selected_fighter_var.get():
            messagebox.showerror("Error", "You must select an alt to analyze, or enable the 'Include all alts' option.")
            return
        
        # Check if analysis is already in progress
        if self.analyzer_thread and self.analyzer_thread.is_alive():
            messagebox.showinfo("Information", "An analysis is already in progress.")
            return
        
        # Reset state
        self.cancel_requested = False
        
        # Clear previous results
        self.update_console("Starting texture analysis...")
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Start analysis in a separate thread
        self.analyzer_thread = threading.Thread(target=self.analyze_thread)
        self.analyzer_thread.daemon = True
        self.analyzer_thread.start()
    
    def cancel_analysis(self):
        """Cancel ongoing analysis"""
        if self.analyzer_thread and self.analyzer_thread.is_alive():
            self.cancel_requested = True
            self.update_console("Requesting analysis cancellation...")
        else:
            messagebox.showinfo("Information", "No analysis in progress.")
    
    def analyze_thread(self):
        """Thread for texture analysis"""
        try:
            start_time = time.time()
            
            # Prepare output directory
            output_dir = self.output_dir_var.get()
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(self.mod_dir, output_dir)
            
            # Create directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            self.update_console(f"Output directory: {output_dir}")
            
            # Determine what to analyze
            fighters_to_analyze = {}
            
            if self.all_alts_var.get():
                # Analyze all fighters and their alts
                fighters = self.load_fighters()
                for fighter in fighters:
                    alts = self.get_alts(fighter)
                    fighters_to_analyze[fighter] = [f"c{alt}" for alt in alts]  # Add the 'c' prefix back
                self.update_console(f"Analyzing all fighters ({len(fighters_to_analyze)}) and their alts.")
            else:
                # Analyze only the selected fighter and alt
                selected_fighter = self.selected_fighter_var.get()
                selected_alt = self.selected_alt_var.get()
                
                if selected_fighter and selected_alt:
                    fighters_to_analyze = {selected_fighter: [f"c{selected_alt}"]}  # Add the 'c' prefix back
                    self.update_console(f"Analyzing only {selected_fighter} - alt c{selected_alt}")
                else:
                    self.update_console("Error: No valid fighter/alt selected.")
                    self.update_status("Analysis cancelled - Invalid selection")
                    return
            
            # Initialize analyzer with the mod directory
            analyzer = TextureAnalyzer(self.mod_dir)
            
            # Analysis results
            analysis_results = []
            
            # Count total paths for progress
            total_paths = sum(len(alts) for alts in fighters_to_analyze.values())
            current_path = 0
            self.update_progress(0, total_paths)
            
            # Process each fighter
            for fighter, alts in fighters_to_analyze.items():
                self.update_console(f"\nAnalyzing fighter: {fighter}")
                
                for alt in alts:
                    if self.cancel_requested:
                        self.update_console("Analysis cancelled by user.")
                        self.update_status("Analysis cancelled")
                        return
                    
                    self.update_status(f"Analyzing {fighter} - {alt}...")
                    self.update_console(f"  Processing alt: {alt}")
                    
                    # Create directory for results
                    alt_output_dir = os.path.join(output_dir, fighter, alt)
                    os.makedirs(alt_output_dir, exist_ok=True)
                    
                    # Collect files for this alt
                    model_paths, etc_paths = self.get_alt_files(fighter, alt)
                    
                    numatb_files = [f for f in model_paths if f.endswith('.numatb')]
                    numdlb_files = [f for f in model_paths if f.endswith('.numdlb')]
                    
                    self.update_console(f"  - NUMATB files found: {len(numatb_files)}")
                    self.update_console(f"  - NUMDLB files found: {len(numdlb_files)}")
                    
                    # Convert files to readable formats
                    if numatb_files and self.analyze_json_var.get():
                        self.update_console("  Converting NUMATB files to JSON...")
                        for matl_file in numatb_files:
                            json_path = convert_numatb_to_json(matl_file, alt_output_dir)
                            if json_path:
                                rel_path = os.path.relpath(json_path, output_dir)
                                self.update_console(f"    ✓ {os.path.basename(matl_file)} → {os.path.basename(json_path)}")
                                analysis_results.append({
                                    "fighter": fighter,
                                    "file": os.path.basename(matl_file),
                                    "type": "Material (JSON)",
                                    "path": rel_path
                                })
                    
                    if numdlb_files and self.analyze_numdlb_var.get() and self.analyze_txt_var.get():
                        self.update_console("  Converting NUMDLB files to TXT...")
                        for modl_file in numdlb_files:
                            txt_path = convert_numdlb_to_text(modl_file, alt_output_dir)
                            if txt_path:
                                rel_path = os.path.relpath(txt_path, output_dir)
                                self.update_console(f"    ✓ {os.path.basename(modl_file)} → {os.path.basename(txt_path)}")
                                analysis_results.append({
                                    "fighter": fighter,
                                    "file": os.path.basename(modl_file),
                                    "type": "Model (TXT)",
                                    "path": rel_path
                                })
                    
                    # Analyze to find texture references (optional)
                    if self.show_details_var.get():
                        self.update_console("  Analyzing texture references...")
                        refs, texture_files = analyzer.analyze_alt(
                            fighter, 
                            model_paths, 
                            etc_paths,
                            analyze_numatb=True,
                            analyze_nuanmb=False,
                            analyze_numdlb=self.analyze_numdlb_var.get(),
                            convert_to_json=self.analyze_json_var.get() and alt_output_dir,
                            convert_to_txt=self.analyze_txt_var.get() and alt_output_dir
                        )
                        
                        self.update_console(f"  - Texture references found: {len(refs)}")
                        
                        # Show file types found
                        if texture_files:
                            file_types = {}
                            for file_path in texture_files:
                                ext = os.path.splitext(file_path)[1].lower()
                                file_types[ext] = file_types.get(ext, 0) + 1
                            
                            self.update_console("  - File types found:")
                            for ext, count in sorted(file_types.items()):
                                self.update_console(f"    {ext}: {count}")
                    
                    # Update progress
                    current_path += 1
                    self.update_progress(current_path, total_paths)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Update results table
            self.update_results_table(analysis_results)
            
            # Final message
            if analysis_results:
                self.update_console(f"\nAnalysis completed in {elapsed_time:.2f} seconds.")
                self.update_console(f"Processed {len(analysis_results)} files.")
                self.update_console(f"Converted files are in: {output_dir}")
                self.update_status(f"Analysis completed - {len(analysis_results)} files")
            else:
                self.update_console("\nNo files were processed. Check the selected options.")
                self.update_status("Analysis completed - No files processed")
                
        except Exception as e:
            error_msg = f"Analysis error: {str(e)}\n{traceback.format_exc()}"
            self.update_console(error_msg)
            self.update_status("Analysis error")
            
        finally:
            self.set_ui_state(True)  # Re-enable controls
    
    def update_status(self, message):
        """Update the status label"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_progress(self, current, total):
        """Update the progress bar"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_bar["value"] = progress
        else:
            self.progress_bar["value"] = 0
        self.root.update_idletasks()
    
    def update_console(self, message):
        """Update the console in the analyzer tab"""
        try:
            self.analyzer_console.config(state=tk.NORMAL)
            self.analyzer_console.insert(tk.END, message + "\n")
            self.analyzer_console.see(tk.END)
            self.analyzer_console.config(state=tk.DISABLED)
            self.root.update_idletasks()
        except Exception as e:
            print(f"Error updating console: {e}")
    
    def update_results_table(self, results):
        # Limpiar tabla
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Insertar resultados
        for result in results:
            self.results_tree.insert("", "end", values=(
                result["fighter"],
                result["file"],
                result["type"],
                result["path"]
            ))
    
    def open_file_from_results(self, event):
        """Open the selected file from results tree"""
        selected = self.results_tree.selection()
        if not selected:
            return
        
        item_values = self.results_tree.item(selected, "values")
        if len(item_values) < 4:
            return
        
        # Get the full path
        output_dir = self.output_dir_var.get()
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.mod_dir, output_dir)
        
        file_path = os.path.join(output_dir, item_values[3])
        
        # Verify file exists
        if os.path.exists(file_path):
            # Open with default application
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
        else:
            self.update_console(f"Error: Could not find file {file_path}")
    
    def set_ui_state(self, enabled):
        """Enable or disable UI elements during processing"""
        state = tk.NORMAL if enabled else tk.DISABLED
        
        # Try to update UI elements safely
        try:
            # Update analyzer tab controls
            widgets = [
                self.fighter_listbox,
                self.alt_listbox,
                self.analyzer_console,
                self.results_tree
            ]
            
            for widget in widgets:
                if hasattr(widget, 'state'):
                    # For ttk widgets, use '!disabled' or 'disabled'
                    widget.state(['!disabled' if enabled else 'disabled'])
                elif hasattr(widget, 'config'):
                    try:
                        widget.config(state=state)
                    except:
                        pass
        except Exception as e:
            print(f"Error updating UI state: {e}")
    
    def detect_fighters_and_alts(self):
        """Detectar luchadores y alts en el mod"""
        fighters_alts = {}
        fighter_dir = os.path.join(self.mod_directory, "fighter")
        
        # Verificar que existe el directorio fighter
        if not os.path.exists(fighter_dir):
            return fighters_alts
        
        # Buscar directorios de luchadores
        for fighter in os.listdir(fighter_dir):
            fighter_path = os.path.join(fighter_dir, fighter)
            if not os.path.isdir(fighter_path):
                continue
            
            model_dir = os.path.join(fighter_path, "model")
            if not os.path.exists(model_dir):
                continue
            
            # Buscar alts basados en carpetas dentro del directorio model
            alts = []
            
            for root, dirs, files in os.walk(model_dir):
                dir_name = os.path.basename(root)
                
                # Patrones comunes para alts
                if dir_name.startswith("c") and dir_name[1:].isdigit():
                    if dir_name not in alts:
                        alts.append(dir_name)
            
            # Si no se encontraron alts con el patrón, buscar archivos
            if not alts:
                alt_patterns = set()
                for root, dirs, files in os.walk(model_dir):
                    for file in files:
                        if file.endswith((".numatb", ".numdlb")):
                            parts = file.split("/")
                            for part in parts:
                                if part.startswith("c") and len(part) > 1 and part[1:].isdigit():
                                    alt_patterns.add(part)
                
                alts = sorted(list(alt_patterns))
            
            # Si aún no hay alts, usar "c00" como predeterminado
            if not alts:
                alts = ["c00"]
            
            fighters_alts[fighter] = sorted(alts)
        
        return fighters_alts
    
    def get_alt_files(self, fighter, alt):
        """Get all files for a specific alt"""
        model_paths = []
        etc_paths = []
        
        fighter_dir = os.path.join(self.mod_dir, "fighter", fighter)
        model_dir = os.path.join(fighter_dir, "model")
        
        # Look for model files
        for root, dirs, files in os.walk(model_dir):
            if alt in root:
                for file in files:
                    if file.endswith(".numatb"):
                        model_paths.append(os.path.join(root, file))
                    elif file.endswith(".numdlb") and self.analyze_numdlb_var.get():
                        model_paths.append(os.path.join(root, file))
        
        # If no files found in alt folders, look for files with alt in the name
        if not model_paths:
            for root, dirs, files in os.walk(model_dir):
                for file in files:
                    if alt in file:
                        if file.endswith(".numatb"):
                            model_paths.append(os.path.join(root, file))
                        elif file.endswith(".numdlb") and self.analyze_numdlb_var.get():
                            model_paths.append(os.path.join(root, file))
        
        # Look for other files like textures
        for root, dirs, files in os.walk(fighter_dir):
            if alt in root and "model" not in root:
                for file in files:
                    if file.endswith((".nutexb", ".numshb")):
                        etc_paths.append(os.path.join(root, file))
        
        return model_paths, etc_paths

    def setup_analyzer_tab(self):
        """Configura la pestaña del analizador de texturas"""
        analyzer_frame = ttk.Frame(self.analyzer_tab, padding=(10, 5))
        analyzer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Directorio de salida
        output_dir_frame = ttk.Frame(analyzer_frame)
        output_dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_dir_frame, text="Output directory:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(output_dir_frame, text="Browse...", command=self.browse_output_dir).pack(side=tk.LEFT)
        
        # Sección para selección de personaje/alt
        fighter_frame = ttk.LabelFrame(analyzer_frame, text="Fighter and Alt Selection", padding=(10, 5))
        fighter_frame.pack(fill=tk.X, pady=5)
        
        # Layout con dos columnas para listas
        fighter_lists_frame = ttk.Frame(fighter_frame)
        fighter_lists_frame.pack(fill=tk.X, pady=5)
        
        # Lista de luchadores (izquierda)
        fighter_list_frame = ttk.Frame(fighter_lists_frame)
        fighter_list_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(fighter_list_frame, text="Fighter:").pack(anchor=tk.W)
        
        # Lista y scrollbar
        fighter_select_frame = ttk.Frame(fighter_list_frame)
        fighter_select_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fighter_listbox = tk.Listbox(fighter_select_frame, height=5)
        fighter_scrollbar = ttk.Scrollbar(fighter_select_frame, orient=tk.VERTICAL, command=self.fighter_listbox.yview)
        self.fighter_listbox.configure(yscrollcommand=fighter_scrollbar.set)
        
        self.fighter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        fighter_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vincular selección
        self.fighter_listbox.bind("<<ListboxSelect>>", self.on_fighter_select)
        
        # Lista de alts (derecha)
        alt_list_frame = ttk.Frame(fighter_lists_frame)
        alt_list_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        ttk.Label(alt_list_frame, text="Alt:").pack(anchor=tk.W)
        
        # Lista y scrollbar
        alt_select_frame = ttk.Frame(alt_list_frame)
        alt_select_frame.pack(fill=tk.BOTH, expand=True)
        
        self.alt_listbox = tk.Listbox(alt_select_frame, height=5)
        alt_scrollbar = ttk.Scrollbar(alt_select_frame, orient=tk.VERTICAL, command=self.alt_listbox.yview)
        self.alt_listbox.configure(yscrollcommand=alt_scrollbar.set)
        
        self.alt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        alt_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Vincular selección
        self.alt_listbox.bind("<<ListboxSelect>>", self.on_alt_select)
        
        # Opciones de análisis
        options_frame = ttk.LabelFrame(analyzer_frame, text="Analysis Options", padding=(10, 5))
        options_frame.pack(fill=tk.X, pady=5)
        
        # Primera fila - Tipos de archivos
        file_types_frame = ttk.Frame(options_frame)
        file_types_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_types_frame, text="Analyze files:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(file_types_frame, text="NUMATB (Materials)", state=tk.DISABLED, variable=tk.BooleanVar(value=True)).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(file_types_frame, text="NUMDLB (Models)", variable=self.analyze_numdlb_var).pack(side=tk.LEFT, padx=5)
        
        # Segunda fila - Formatos de salida
        output_types_frame = ttk.Frame(options_frame)
        output_types_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_types_frame, text="Generate:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(output_types_frame, text="TXT Files", variable=self.analyze_txt_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(output_types_frame, text="JSON Files", variable=self.analyze_json_var).pack(side=tk.LEFT, padx=5)
        
        # Tercera fila - Otras opciones
        other_options_frame = ttk.Frame(options_frame)
        other_options_frame.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(other_options_frame, text="Include all alts", variable=self.all_alts_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(other_options_frame, text="Show details", variable=self.show_details_var).pack(side=tk.LEFT, padx=5)
        
        # Nota informativa
        note_text = "Note: This analyzer processes .numatb and .numdlb files, generating readable versions for analysis."
        note_label = ttk.Label(options_frame, text=note_text, font=("Segoe UI", 9, "italic"), foreground="gray")
        note_label.pack(fill=tk.X, pady=5)
        
        # Botones de acción
        buttons_frame = ttk.Frame(analyzer_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="Analyze Files", command=self.start_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=self.cancel_analysis).pack(side=tk.LEFT, padx=5)
        
        # Tabla de resultados y consola
        results_frame = ttk.Frame(analyzer_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tabla de resultados (izquierda)
        table_frame = ttk.LabelFrame(results_frame, text="Results", padding=(5, 5))
        table_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 5))
        
        # Crear tabla
        self.results_tree = ttk.Treeview(table_frame, columns=("fighter", "file", "type", "path"), 
                                        show="headings", selectmode="browse")
        
        # Configurar columnas
        self.results_tree.heading("fighter", text="Fighter")
        self.results_tree.heading("file", text="File")
        self.results_tree.heading("type", text="Type")
        self.results_tree.heading("path", text="Path")
        
        self.results_tree.column("fighter", width=100)
        self.results_tree.column("file", width=150)
        self.results_tree.column("type", width=100)
        self.results_tree.column("path", width=200)
        
        # Doble clic para abrir archivo
        self.results_tree.bind("<Double-1>", self.open_file_from_results)
        
        # Scrollbar para la tabla
        table_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=table_scroll.set)
        
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Consola de salida (derecha)
        console_frame = ttk.LabelFrame(results_frame, text="Console", padding=(5, 5))
        console_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=(5, 0))
        
        self.analyzer_console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=10)
        self.analyzer_console.pack(fill=tk.BOTH, expand=True)
        self.analyzer_console.config(state=tk.DISABLED)

    def setup_optimizer_tab(self):
        """Configura la pestaña del optimizador de texturas"""
        optimizer_frame = ttk.Frame(self.optimizer_tab, padding=(10, 5))
        optimizer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel de selección (izquierda)
        selection_frame = ttk.LabelFrame(optimizer_frame, text="Fighter and Alt Selection", padding=(10, 5))
        selection_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), pady=5)
        
        # Lista de luchadores
        fighter_frame = ttk.Frame(selection_frame)
        fighter_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(fighter_frame, text="Fighter:").pack(anchor=tk.W)
        self.optimizer_fighter_listbox = tk.Listbox(fighter_frame, height=10, width=20)
        self.optimizer_fighter_listbox.pack(fill=tk.BOTH, expand=True)
        self.optimizer_fighter_listbox.bind("<<ListboxSelect>>", self.on_optimizer_fighter_select)
        
        # Lista de alts
        alt_frame = ttk.Frame(selection_frame)
        alt_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(alt_frame, text="Alt:").pack(anchor=tk.W)
        self.optimizer_alt_listbox = tk.Listbox(alt_frame, height=10, width=20)
        self.optimizer_alt_listbox.pack(fill=tk.BOTH, expand=True)
        self.optimizer_alt_listbox.bind("<<ListboxSelect>>", self.on_optimizer_alt_select)
        
        # Botones de acción
        actions_frame = ttk.Frame(selection_frame)
        actions_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(actions_frame, text="Analyze", command=self.analyze_optimizer_selected).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="Optimize", command=self.optimize_selected).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="Optimize All Alts", command=self.optimize_all_alts).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="Restore", command=self.restore_junk).pack(fill=tk.X, pady=2)
        ttk.Button(actions_frame, text="Delete Files for Analysis", command=self.clean_analysis_files).pack(fill=tk.X, pady=2)
        
        # Panel de resultados (derecha)
        results_frame = ttk.Frame(optimizer_frame)
        results_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        
        # Tabla de texturas
        table_frame = ttk.LabelFrame(results_frame, text="Textures", padding=(5, 5))
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("texture", "status", "size")
        self.texture_tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        
        self.texture_tree.heading("texture", text="Texture")
        self.texture_tree.heading("status", text="Status")
        self.texture_tree.heading("size", text="Size")
        
        self.texture_tree.column("texture", width=300)
        self.texture_tree.column("status", width=100)
        self.texture_tree.column("size", width=80)
        
        # Scrollbars para la tabla
        tree_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.texture_tree.yview)
        self.texture_tree.configure(yscrollcommand=tree_scroll_y.set)
        
        tree_scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.texture_tree.xview)
        self.texture_tree.configure(xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.texture_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Consola de salida
        console_frame = ttk.LabelFrame(results_frame, text="Console", padding=(5, 5))
        console_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.optimizer_console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=10)
        self.optimizer_console.pack(fill=tk.BOTH, expand=True)
        self.optimizer_console.config(state=tk.DISABLED)
        
        # Estadísticas
        stats_frame = ttk.LabelFrame(results_frame, text="Statistics")
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_text = ttk.Label(stats_frame, text="No data available")
        self.stats_text.pack(fill=tk.X, pady=5, padx=5)

    def on_optimizer_fighter_select(self, event):
        """Handle fighter selection in the optimizer tab"""
        selection = self.optimizer_fighter_listbox.curselection()
        if not selection:
            return
        
        self.optimizer_alt_listbox.delete(0, tk.END)
        fighter = self.optimizer_fighter_listbox.get(selection[0])
        self.selected_optimizer_fighter = fighter
        
        for alt in self.get_alts(fighter):
            self.optimizer_alt_listbox.insert(tk.END, alt)
        
        # Select the first alt by default
        if self.optimizer_alt_listbox.size() > 0:
            self.optimizer_alt_listbox.selection_set(0)
            self.on_optimizer_alt_select(None)
    
    def on_optimizer_alt_select(self, event):
        """Handle alt selection in the optimizer tab"""
        selection = self.optimizer_alt_listbox.curselection()
        if not selection:
            return
        
        alt = self.optimizer_alt_listbox.get(selection[0])
        self.selected_optimizer_alt = alt
    
    def analyze_optimizer_selected(self):
        """Analyze textures for the selected fighter and alt in optimizer tab"""
        if not hasattr(self, 'selected_optimizer_fighter') or not hasattr(self, 'selected_optimizer_alt'):
            messagebox.showwarning("Selection Required", "Please select a fighter and alt first.")
            return
        
        if not self.selected_optimizer_fighter or not self.selected_optimizer_alt:
            messagebox.showwarning("Selection Required", "Please select a fighter and alt first.")
            return
        
        # Clear previous results
        self.texture_tree.delete(*self.texture_tree.get_children())
        self.optimizer_console.config(state=tk.NORMAL)
        self.optimizer_console.delete(1.0, tk.END)
        self.optimizer_console.config(state=tk.DISABLED)
        
        # Clear statistics
        self.stats_text.config(text="No data available")
        
        self.log_to_optimizer(f"Analyzing textures for {self.selected_optimizer_fighter} (alt {self.selected_optimizer_alt})...")
        
        # Check if texture analysis data exists
        output_dir = self.output_dir_var.get()
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.mod_dir, output_dir)
        
        fighter = self.selected_optimizer_fighter
        alt = f"c{self.selected_optimizer_alt}"
        analysis_dir = os.path.join(output_dir, fighter, alt)
        
        if not os.path.exists(analysis_dir) or not glob.glob(os.path.join(analysis_dir, "*.json")):
            self.log_to_optimizer(f"No texture analysis data found for {fighter}/{alt}")
            self.log_to_optimizer("--------------------------------------------")
            self.log_to_optimizer("Please run the NUMATB Analyzer first:")
            self.log_to_optimizer("1. Switch to the NUMATB Analyzer tab")
            self.log_to_optimizer(f"2. Select {fighter} and alt {self.selected_optimizer_alt}")
            self.log_to_optimizer("3. Click 'Analyze Files'")
            self.log_to_optimizer("4. Come back to this tab and try again")
            self.log_to_optimizer("--------------------------------------------")
            return
        
        # Path to model/body for this alt
        body_dir = os.path.join(self.mod_dir, "fighter", self.selected_optimizer_fighter, "model", "body", f"c{self.selected_optimizer_alt}")
        
        # Check if the directory exists
        if not os.path.exists(body_dir):
            self.log_to_optimizer(f"Directory not found: {body_dir}")
            self.log_to_optimizer("This alt might not have specific textures. Trying other locations...")
            
            # Look for textures in other locations like model/
            model_dir = os.path.join(self.mod_dir, "fighter", self.selected_optimizer_fighter, "model")
            if os.path.exists(model_dir):
                self.log_to_optimizer(f"Searching in {model_dir}...")
                textures = []
                for root, dirs, files in os.walk(model_dir):
                    for file in files:
                        if file.endswith(".nutexb") and f"c{self.selected_optimizer_alt}" in root:
                            textures.append(os.path.join(root, file))
                
                if not textures:
                    # If still no textures found, check if filenames contain the alt number
                    for root, dirs, files in os.walk(model_dir):
                        for file in files:
                            if file.endswith(".nutexb") and f"c{self.selected_optimizer_alt}" in file:
                                textures.append(os.path.join(root, file))
                
                if textures:
                    self.log_to_optimizer(f"Found {len(textures)} textures in other locations")
                else:
                    self.log_to_optimizer("No textures found for this alt. Please select a different fighter or alt.")
                    return
            else:
                self.log_to_optimizer("No valid model directory found for this fighter.")
                return
        else:
            # Get textures from the fighter directory
            textures = self.get_textures_in_directory(body_dir)
            self.log_to_optimizer(f"Found {len(textures)} textures in {body_dir}")
        
        if not textures:
            self.log_to_optimizer("No textures found for this alt. Please select a different fighter or alt.")
            return
        
        # Get NUMATB files to identify actually used textures
        model_files = self.get_model_files(self.selected_optimizer_fighter, self.selected_optimizer_alt)
        used_textures = self.get_used_textures(model_files)
        
        # Update the treeview
        total_size = 0
        used_size = 0
        unused_size = 0
        
        for texture in textures:
            texture_name = os.path.basename(texture)
            texture_size = os.path.getsize(texture)
            total_size += texture_size
            
            # Check if this texture is used by any material
            is_used = any(used_name == texture_name for used_name in used_textures)
            if not is_used:
                # Try partial matching with texture base name (without extension)
                texture_basename = os.path.splitext(texture_name)[0]
                is_used = any(used_name.startswith(texture_basename) for used_name in used_textures)
            
            status = "In Use" if is_used else "Unused"
            size_str = f"{texture_size/1024:.1f} KB"
            
            self.texture_tree.insert("", tk.END, values=(texture_name, status, size_str))
            
            if is_used:
                used_size += texture_size
            else:
                unused_size += texture_size
        
        # Update statistics
        used_count = sum(1 for item in self.texture_tree.get_children() if self.texture_tree.item(item)["values"][1] == "Used")
        unused_count = sum(1 for item in self.texture_tree.get_children() if self.texture_tree.item(item)["values"][1] == "Unused")
        
        stats_text = (f"Total textures: {len(textures)} ({self.format_size(total_size)})\n"
                      f"In Use: {used_count} ({self.format_size(used_size)})\n"
                      f"Unused: {unused_count} ({self.format_size(unused_size)})\n"
                      f"Potential savings: {(unused_size/total_size*100 if total_size > 0 else 0):.1f}% of space")
        
        self.stats_text.config(text=stats_text)
        self.log_to_optimizer("Analysis complete!")
    
    def log_to_optimizer(self, message):
        """Log message to the optimizer console"""
        self.optimizer_console.config(state=tk.NORMAL)
        self.optimizer_console.insert(tk.END, message + "\n")
        self.optimizer_console.see(tk.END)
        self.optimizer_console.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def get_textures_in_directory(self, directory):
        """Get all texture files in a directory"""
        textures = []
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith(".nutexb"):
                    textures.append(os.path.join(directory, file))
        return textures
    
    def get_model_files(self, fighter, alt):
        """Get model files for a fighter and alt to check texture usage"""
        model_files = []
        
        # Check for model/body/c{alt}/ files
        body_dir = os.path.join(self.mod_dir, "fighter", fighter, "model", "body", f"c{alt}")
        if os.path.exists(body_dir):
            for file in os.listdir(body_dir):
                if file.endswith(".numdlb") or file.endswith(".numatb") or file.endswith(".numshb"):
                    model_files.append(os.path.join(body_dir, file))
        
        # Check for model/ files
        model_dir = os.path.join(self.mod_dir, "fighter", fighter, "model")
        if os.path.exists(model_dir):
            for file in os.listdir(model_dir):
                if file.endswith(".numdlb") or file.endswith(".numatb") or file.endswith(".numshb"):
                    model_files.append(os.path.join(model_dir, file))
        
        return model_files
    
    def get_used_textures(self, model_files):
        """Extract texture names used in model files"""
        used_textures = set()
        texture_references = {}  # Path -> count dictionary
        
        # First check for JSON files in the analysis directory
        output_dir = self.output_dir_var.get()
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.mod_dir, output_dir)
        
        fighter = self.selected_optimizer_fighter
        alt = f"c{self.selected_optimizer_alt}"
        analysis_dir = os.path.join(output_dir, fighter, alt)
        
        self.log_to_optimizer(f"Looking for texture analysis in: {analysis_dir}")
        
        # If analysis directory exists, read JSON files
        if os.path.exists(analysis_dir):
            json_files = glob.glob(os.path.join(analysis_dir, "*.json"))
            self.log_to_optimizer(f"Found {len(json_files)} analysis JSON files")
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        material_data = json.load(f)
                    
                    self.log_to_optimizer(f"Parsing {os.path.basename(json_file)}...")
                    
                    # Extract texture references from the material data
                    if isinstance(material_data, list):
                        for material in material_data:
                            if "textures" in material and isinstance(material["textures"], list):
                                for texture in material["textures"]:
                                    if "texture_path" in texture:
                                        texture_path = texture["texture_path"]
                                        
                                        # Extract just the filename from the path
                                        if "/" in texture_path or "\\" in texture_path:
                                            texture_name = os.path.basename(texture_path)
                                        else:
                                            texture_name = texture_path
                                            
                                        # Add .nutexb extension if missing
                                        if not texture_name.endswith(".nutexb"):
                                            texture_name += ".nutexb"
                                        
                                        used_textures.add(texture_name)
                                        texture_references[texture_name] = texture_references.get(texture_name, 0) + 1
                except Exception as e:
                    self.log_to_optimizer(f"Error reading JSON file {json_file}: {str(e)}")
            
            # Show texture reference details
            if texture_references:
                self.log_to_optimizer(f"Found {len(texture_references)} unique texture references in JSON files:")
                for texture, count in sorted(texture_references.items(), key=lambda x: x[1], reverse=True):
                    self.log_to_optimizer(f"  - {texture}: referenced {count} time(s)")
        else:
            self.log_to_optimizer(f"No texture analysis directory found for {fighter}/{alt}")
            self.log_to_optimizer("Please run the NUMATB Analyzer first for this fighter/alt")
        
        # Fallback: If no textures found from JSON, try binary search in NUMATB files
        if not used_textures:
            self.log_to_optimizer("No texture references found in JSON files, using fallback method")
            for model_file in model_files:
                # For NUMATB files, parse to get texture references
                if model_file.endswith(".numatb"):
                    try:
                        with open(model_file, 'rb') as f:
                            data = f.read()
                            
                            # Simple search for texture name patterns in binary
                            # This is a simplified approach - a proper parser would be more robust
                            pattern = re.compile(rb'tex\w+\.nutexb', re.IGNORECASE)
                            matches = pattern.findall(data)
                            
                            for match in matches:
                                texture_name = match.decode('utf-8', errors='ignore')
                                used_textures.add(texture_name)
                                self.log_to_optimizer(f"Found texture reference (binary): {texture_name}")
                    except Exception as e:
                        self.log_to_optimizer(f"Error parsing {model_file}: {str(e)}")
        
        return used_textures
    
    def get_file_size(self, file_path):
        """Get file size in bytes"""
        return os.path.getsize(file_path)
    
    def calculate_total_size(self, textures):
        """Calculate total size of all textures"""
        return sum(os.path.getsize(texture) for texture in textures)
    
    def calculate_used_size(self, textures, used_textures):
        """Calculate size of used textures"""
        return sum(os.path.getsize(texture) for texture in textures 
                  if any(os.path.basename(texture).startswith(used_name) for used_name in used_textures))
    
    def format_size(self, size_in_bytes):
        """Format size in bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} TB"
    
    def optimize_selected(self):
        """Optimize textures for the selected fighter and alt"""
        if not self.selected_optimizer_fighter or not self.selected_optimizer_alt:
            messagebox.showwarning("Selection Required", "Please select a fighter and alt first.")
            return
        
        self.log_to_optimizer(f"Optimizing textures for {self.selected_optimizer_fighter} (alt {self.selected_optimizer_alt})...")
        
        # Get textures
        path = os.path.join(self.mod_dir, "fighter", self.selected_optimizer_fighter, "model", "body", f"c{self.selected_optimizer_alt}")
        textures = self.get_textures_in_directory(path)
        
        # Get used textures
        model_files = self.get_model_files(self.selected_optimizer_fighter, self.selected_optimizer_alt)
        used_textures = self.get_used_textures(model_files)
        
        # Create junk directory if it doesn't exist
        junk_dir = os.path.join(self.mod_dir, "junk", "fighter", self.selected_optimizer_fighter, "model", "body", f"c{self.selected_optimizer_alt}")
        os.makedirs(junk_dir, exist_ok=True)
        
        # Move unused textures to junk
        moved_count = 0
        for texture in textures:
            texture_name = os.path.basename(texture)
            is_used = any(texture_name.startswith(used_name) for used_name in used_textures)
            
            if not is_used:
                junk_path = os.path.join(junk_dir, texture_name)
                shutil.move(texture, junk_path)
                self.log_to_optimizer(f"Moved {texture_name} to junk")
                moved_count += 1
        
        self.log_to_optimizer(f"Optimization complete! Moved {moved_count} unused textures to junk directory.")
        
        # Refresh the analysis
        self.analyze_optimizer_selected()
    
    def optimize_all_alts(self):
        """Optimize textures for all alts of the selected fighter"""
        if not self.selected_optimizer_fighter:
            messagebox.showwarning("Selection Required", "Please select a fighter first.")
            return
        
        self.log_to_optimizer(f"Optimizing textures for all alts of {self.selected_optimizer_fighter}...")
        
        alts = self.get_alts(self.selected_optimizer_fighter)
        for alt in alts:
            self.selected_optimizer_alt = alt
            self.log_to_optimizer(f"Processing alt {alt}...")
            
            # Get textures
            path = os.path.join(self.mod_dir, "fighter", self.selected_optimizer_fighter, "model", "body", f"c{alt}")
            if not os.path.exists(path):
                self.log_to_optimizer(f"Path not found: {path}")
                continue
                
            textures = self.get_textures_in_directory(path)
            
            # Get used textures
            model_files = self.get_model_files(self.selected_optimizer_fighter, alt)
            used_textures = self.get_used_textures(model_files)
            
            # Create junk directory if it doesn't exist
            junk_dir = os.path.join(self.mod_dir, "junk", "fighter", self.selected_optimizer_fighter, "model", "body", f"c{alt}")
            os.makedirs(junk_dir, exist_ok=True)
            
            # Move unused textures to junk
            moved_count = 0
            for texture in textures:
                texture_name = os.path.basename(texture)
                is_used = any(texture_name.startswith(used_name) for used_name in used_textures)
                
                if not is_used:
                    junk_path = os.path.join(junk_dir, texture_name)
                    shutil.move(texture, junk_path)
                    moved_count += 1
            
            self.log_to_optimizer(f"Alt {alt}: Moved {moved_count} unused textures to junk")
        
        self.log_to_optimizer("All alts optimization complete!")
        
        # Refresh the analysis for the current alt
        self.analyze_optimizer_selected()
    
    def restore_junk(self):
        """Restore textures from junk directory"""
        if not self.selected_optimizer_fighter:
            messagebox.showwarning("Selection Required", "Please select a fighter first.")
            return
        
        restore_all = messagebox.askyesno("Restore Options", "Restore all alts? Select 'No' to restore only the current alt.")
        
        if restore_all:
            # Restore all alts
            alts = self.get_alts(self.selected_optimizer_fighter)
            for alt in alts:
                self.restore_alt_junk(alt)
        else:
            # Restore current alt only
            if not self.selected_optimizer_alt:
                messagebox.showwarning("Selection Required", "Please select an alt first.")
                return
            self.restore_alt_junk(self.selected_optimizer_alt)
        
        self.log_to_optimizer("Restore complete!")
        
        # Refresh the analysis
        self.analyze_optimizer_selected()
    
    def restore_alt_junk(self, alt):
        """Restore junk files for a specific alt"""
        junk_dir = os.path.join(self.mod_dir, "junk", "fighter", self.selected_optimizer_fighter, "model", "body", f"c{alt}")
        target_dir = os.path.join(self.mod_dir, "fighter", self.selected_optimizer_fighter, "model", "body", f"c{alt}")
        
        if not os.path.exists(junk_dir):
            self.log_to_optimizer(f"No junk directory found for {self.selected_optimizer_fighter} alt {alt}")
            return
        
        os.makedirs(target_dir, exist_ok=True)
        
        # Move files from junk back to original location
        restored_count = 0
        for file in os.listdir(junk_dir):
            if file.endswith(".nutexb"):
                junk_path = os.path.join(junk_dir, file)
                target_path = os.path.join(target_dir, file)
                shutil.move(junk_path, target_path)
                restored_count += 1
        
        self.log_to_optimizer(f"Restored {restored_count} files for alt {alt}")
        
        # Remove empty junk directory
        if len(os.listdir(junk_dir)) == 0:
            os.rmdir(junk_dir)
            parent_dir = os.path.dirname(junk_dir)
            while parent_dir != self.mod_dir and len(os.listdir(parent_dir)) == 0:
                os.rmdir(parent_dir)
                parent_dir = os.path.dirname(parent_dir)

    def on_tab_change(self, event):
        """Handle tab change event"""
        tab_id = self.notebook.select()
        tab_name = self.notebook.tab(tab_id, "text")
        
        # Update the window title based on the active tab
        self.root.title(f"Texture Manager - {tab_name}")
        
        # Refresh the active tab data if needed
        if tab_name == "Texture Optimizer" and self.mod_dir:
            # If we have selections, refresh the analysis
            if self.selected_optimizer_fighter and self.selected_optimizer_alt:
                self.analyze_optimizer_selected()

    def browse_output_dir(self):
        """Browse for the output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
            self.update_console(f"Output directory set to: {directory}")

    def clean_analysis_files(self):
        """Remove the texture-analysis folder after confirming with the user"""
        output_dir = self.output_dir_var.get()
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(self.mod_dir, output_dir)
        
        if not os.path.exists(output_dir):
            messagebox.showinfo("Information", "No analysis files found to clean.")
            return
        
        # Ask for confirmation
        if messagebox.askyesno("Confirm Cleanup", 
                              "This will remove all NUMATB analysis files.\n\n"
                              "You will need to run the NUMATB Analyzer again if you want to optimize textures.\n\n"
                              "Do you want to continue?"):
            try:
                # Remove the directory and all its contents
                shutil.rmtree(output_dir)
                self.log_to_optimizer("Analysis files cleaned successfully.")
                self.log_to_optimizer("You will need to run the NUMATB Analyzer again before optimizing textures.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not remove analysis files: {str(e)}")
                self.log_to_optimizer(f"Error cleaning analysis files: {str(e)}")

# Create the main application window
if __name__ == "__main__":
    root = tk.Tk()
    app = TextureManagerApp(root)
    root.mainloop() 