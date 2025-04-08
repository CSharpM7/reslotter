#Original code by BluJay <https://github.com/blu-dev> and Jozz <https://github.com/jozz024/ssbu-skin-reslotter>
#Modified by Coolsonickirby to get it to work with dir addition
import os
import shutil
import sys
import json
import re

def usage():
    print("usage: python reslotter.py <mod_directory> <hashes_file> <fighter_name> <current_alt> <target_alt> <share_slot> <out_directory>")
    sys.exit(2)

def makeDirsFromFile(path):
    dirName = os.path.dirname(path)
    try:
        os.makedirs(dirName)
    except:
        pass

def fix_windows_path(path: str, to_linux: bool):
    if to_linux:
        return path.replace("\\", "/")
    else:
        return path.replace("/", os.sep)

def find_fighter_files(mod_directory):
    all_files = []
    # list through the dirs in the mod directory
    for folders in os.listdir(mod_directory):
        full_path = os.path.join(mod_directory, folders)
        if os.path.isdir(full_path):
            # if the entry in the folder is a directory, walk through its contents and append any files you find to the file list
            for root, dirs, files in os.walk(full_path):
                if len(files) != 0:
                    # if files isnt nothing we "iterate" through it to append the file to the file list
                    for file in files:
                        full_file_path = os.path.join(root, file)
                        #toAppend = fix_windows_path(full_file_path, True).lstrip(mod_directory + "/")
                        toAppend = fix_windows_path(full_file_path, True).replace(mod_directory.replace("\\","/")+"/","")
                        all_files.append(toAppend)
    return all_files

def reslot_fighter_files(mod_directory, fighter_files, current_alt, target_alt, share_slot, out_dir, fighter_name):
    #TODO: If not excluding, only run through fighter_files once. Then properly generate a config
    #Maybe the fighter_files part should be moved to main()
    reslotted_files = []

    if out_dir != "":
        for file in fighter_files:
            #Exclude any other file outside of the current_alt
            if (not current_alt.strip('c') in file):
                continue

            lookfor = ""
            replace = ""
            new_file = ""

            #Unique to UI folders, we need to check if the filename contains 
            #"_fighter_name_" since all UI files are grouped together
            if file.startswith("ui/replace/chara") or file.startswith("ui/replace_patch/chara"):
                lookfor = f"{current_alt.strip('c')}.bntx"
                replace = f"{target_alt.strip('c')}.bntx"
                new_file = file.replace(lookfor, replace)

                fighter_keys = [fighter_name]
                #Ice Climber / Aegis Stuff
                if (fighter_name=="popo" or fighter_name=="nana"):
                    fighter_keys = ["ice_climber"]
                elif (fighter_name=="eflame"):
                    fighter_keys = ["eflame_first","eflame_only"]
                elif (fighter_name=="elight"):
                    fighter_keys = ["elight_first","elight_only"]

                for key in fighter_keys:
                    if new_file.__contains__("_" + key + "_") and out_dir != "":
                        makeDirsFromFile(os.path.join(out_dir, new_file))
                        shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))
                continue

            # Since each directory has a different structure, we have to go through each directory separately
            if file.startswith(f"fighter/{fighter_name}"):
                if (not "/"+current_alt+"/" in file):
                    continue
                
                lookfor = f"/{current_alt}/"
                replace = f"/{target_alt}/"
                new_file = file.replace(lookfor, replace)
            elif file.startswith(f"sound/bank/fighter/se_{fighter_name}") or file.startswith(f"sound/bank/fighter_voice/vc_{fighter_name}"):
                lookfor = f"_{current_alt}"
                replace = f"_{target_alt}"
                new_file = file.replace(lookfor, replace)
            elif file.startswith(f"effect/fighter/{fighter_name}"):
                lookfor = f"{current_alt.strip('c')}"
                replace = f"{target_alt.strip('c')}"
                new_file = file.replace(lookfor, replace)
            else:
                continue

            makeDirsFromFile(os.path.join(out_dir, new_file))
            shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))

            #Prevent duplicates
            reslotted_files.append(new_file)

    existing_files.extend(reslotted_files)
    if 7 < int(target_alt.strip("c")):
        current_alt_int = int(current_alt.strip("c"))
        share_alt_int = int(share_slot.strip("c")) % 8
        if current_alt_int <= 7:
            add_new_slot(f"fighter/{fighter_name}", current_alt, target_alt,"c0"+str(share_alt_int))
            add_missing_files(reslotted_files, fighter_name, target_alt,True)
        else:
            current_alt_int = int(target_alt.strip("c")) % 8
            add_new_slot(f"fighter/{fighter_name}", f"c0{current_alt_int}", target_alt,"c0"+str(share_alt_int))
            add_missing_files(reslotted_files, fighter_name, target_alt,True)
    else:
        add_missing_files(reslotted_files, fighter_name, target_alt)

    return reslotted_files, fighter_files

# Previous name of function was make_config
def add_missing_files(reslotted_files, fighter_name, target_alt, is_new_slot=False):
    # make a variable that holds the dirinfo path for the new slot
    new_dir_info = f"fighter/{fighter_name}/{target_alt}"
    # we have to do config separately if it's an added slot because those require extra config options

    if new_dir_info not in resulting_config["new-dir-files"]:
        resulting_config["new-dir-files"][new_dir_info] = []
        
    # Agregar entrada para cámara en la estructura correcta (SOLO en la estructura c10X/camera)
    camera_dir_info = f"fighter/{fighter_name}/{target_alt}/camera"
    if camera_dir_info not in resulting_config["new-dir-files"]:
        resulting_config["new-dir-files"][camera_dir_info] = []
        
    # Clave para efectos trasplantados
    transplant_dir_info = f"fighter/{fighter_name}/cmn"
    if transplant_dir_info not in resulting_config["new-dir-files"]:
        resulting_config["new-dir-files"][transplant_dir_info] = []
        
    # Eliminar cualquier entrada antigua de cámara que use otra estructura
    old_camera_dir = f"fighter/{fighter_name}/camera/{target_alt}"
    if old_camera_dir in resulting_config["new-dir-files"]:
        del resulting_config["new-dir-files"][old_camera_dir]

    # Lista extendida de extensiones para archivos personalizados que no forman parte de Smash vanilla
    custom_extensions = [
        '.nuanmb', '.marker', '.bin', '.tonelabel', '.numatb', '.numdlb', '.nutexb',
        '.numshb', '.numshexb', '.nus3audio', '.nus3bank', '.nuhlpb', '.numdlb', '.xmb', '.kime', '.eff'
    ]
    custom_files = []
    camera_files = []
    transplant_files = []
    effect_files = []
    
    # Buscar archivos personalizados en la carpeta del mod
    for file in fighter_files:
        # Detectar efectos trasplantados
        transplant_path = f"effect/fighter/{fighter_name}/transplant/"
        if transplant_path in file:
            if file not in transplant_files:
                transplant_files.append(file)
            continue
            
        # Detectar efectos específicos del slot
        effect_path = f"effect/fighter/{fighter_name}/ef_{fighter_name}_{target_alt}"
        if effect_path in file:
            if file not in effect_files:
                effect_files.append(file)
            continue
            
        # Verificar si el archivo está en la carpeta del target_alt
        if f"/{target_alt}/" in file or file.endswith(f"/{target_alt}"):
            # Manejar archivos de cámara de manera especial
            if file.startswith(f"camera/fighter/{fighter_name}/{target_alt}/"):
                # Solo incluir archivos .nuanmb para cámara, no incluir .kime
                if file.endswith('.nuanmb'):
                    camera_files.append(file)
                continue
                
            file_ext = os.path.splitext(file)[1].lower()
            is_custom = False
            
            # Comprobar si es un archivo personalizado por extensión
            if file_ext in custom_extensions:
                is_custom = True
            
            # O si no está en los archivos conocidos de Smash vanilla
            if file not in known_files:
                is_custom = True
                
            # O si es un archivo de texture/model personalizado
            if any(marker in file.lower() for marker in ['body', 'face', 'hair', 'eye', 'brs_', 'bust_', 'hand_']):
                is_custom = True
            
            # Si es un archivo personalizado, agregarlo a la lista
            if is_custom:
                custom_files.append(file)
    
    # Agregar los archivos personalizados a la configuración
    for custom_file in custom_files:
        if custom_file not in resulting_config["new-dir-files"][new_dir_info]:
            resulting_config["new-dir-files"][new_dir_info].append(custom_file)
    
    # Agregar los archivos de efectos específicos del slot
    for effect_file in effect_files:
        if effect_file not in resulting_config["new-dir-files"][new_dir_info]:
            resulting_config["new-dir-files"][new_dir_info].append(effect_file)
    
    # Agregar los archivos de cámara a la carpeta de cámara (SOLO a c10X/camera, no a camera/c10X)
    # Solo incluir archivos .nuanmb, no .kime
    for camera_file in camera_files:
        if camera_file not in resulting_config["new-dir-files"][camera_dir_info]:
            resulting_config["new-dir-files"][camera_dir_info].append(camera_file)
            
    # Agregar efectos trasplantados a fighter/{fighter_name}/cmn
    for transplant_file in transplant_files:
        if transplant_file not in resulting_config["new-dir-files"][transplant_dir_info]:
            resulting_config["new-dir-files"][transplant_dir_info].append(transplant_file)
    
    # Procesar los archivos reslotteados normales
    for file in reslotted_files:
        # No agregar archivos de cámara en new-dir-files principal
        if file.startswith(f"camera/fighter/{fighter_name}/{target_alt}/"):
            continue
            
        # No agregar efectos trasplantados en new-dir-files principal
        if f"effect/fighter/{fighter_name}/transplant/" in file:
            continue
            
        # No añadir efectos a alts vanilla
        if (not is_new_slot and "effect" in file):
            continue
            
        if file not in known_files and file not in custom_files:
            if file in resulting_config["new-dir-files"][new_dir_info]:
                continue
            resulting_config["new-dir-files"][new_dir_info].append(file)

def add_new_slot(dir_info, source_slot, new_slot, share_slot):
    folders = dir_info.split("/")
    target_dir = dirs_data

    for folder in folders:
        target_dir = target_dir["directories"][folder]

    if source_slot in target_dir["directories"]:
        source_slot_dir = target_dir["directories"][source_slot]
        source_slot_path = "%s/%s" % ((dir_info, source_slot))
        new_slot_dir_path = "%s/%s" % ((dir_info, new_slot))
        share_slot_dir = target_dir["directories"][share_slot]
        share_slot_path = "%s/%s" % ((dir_info, share_slot))

        if (not new_slot_dir_path in resulting_config["new-dir-infos"]):
            resulting_config["new-dir-infos"].append(new_slot_dir_path)

        # Deal with files
        addFilesToDirInfo(new_slot_dir_path, share_slot_dir["files"], new_slot)
        addSharedFiles(share_slot_dir["files"], source_slot, new_slot,share_slot)

        for dir in source_slot_dir["directories"]:
            source_slot_base = f"{source_slot_path}/{dir}"
            new_slot_base = f"{new_slot_dir_path}/{dir}"
            share_slot_base = f"{share_slot_path}/{dir}"
            resulting_config["new-dir-infos-base"][new_slot_base] = share_slot_base

    for dir in target_dir["directories"]:
        target_obj = target_dir["directories"][dir]
        if source_slot in target_obj["directories"]:
            source_slot_dir = target_obj["directories"][source_slot]
            source_slot_path = f"{dir_info}/{dir}/{source_slot}"
            new_slot_dir_path = f"{dir_info}/{dir}/{new_slot}"
            share_slot_dir = target_obj["directories"][share_slot]
            share_slot_path = f"{dir_info}/{dir}/{share_slot}"

            if (not new_slot_dir_path in resulting_config["new-dir-infos"]):
                resulting_config["new-dir-infos"].append(new_slot_dir_path)

            # Deal with files
            addFilesToDirInfo(new_slot_dir_path, share_slot_dir["files"], new_slot)
            addSharedFiles(share_slot_dir["files"], source_slot, new_slot,share_slot)

            # Deal with directories
            for child_dir in source_slot_dir["directories"]:
                source_slot_base = f"{source_slot_path}/{child_dir}"
                new_slot_base = f"{new_slot_dir_path}/{child_dir}"
                share_slot_base = f"{share_slot_path}/{child_dir}"
                resulting_config["new-dir-infos-base"][new_slot_base] = share_slot_base


def addFilesToDirInfo(dir_info, files, target_color):
    if dir_info not in resulting_config["new-dir-files"]:
        resulting_config["new-dir-files"][dir_info] = []

    for index in files:
        file_path = file_array[index]
        if file_path.startswith("0x"):
            continue
        new_file_path = re.sub(r"c0[0-9]", target_color, file_path, 1)
        if new_file_path in resulting_config["new-dir-files"][dir_info]:
            continue
        resulting_config["new-dir-files"][dir_info].append(new_file_path)

def IsShareableSound(sound_file):
    # Ahora devolvemos True para todos los archivos de sonido
    # para asegurar que se incluyan en el config.json
    return True

def addSharedFiles(src_files, source_color, target_color, share_slot):
    used_files = []
    
    # Lista de extensiones que normalmente no se comparten, pero las trataremos de manera especial
    never_share_extensions = ['.nutexb']  # Quitamos los archivos de audio de esta lista
    
    for index in src_files:
        file_path = file_array[index]
        if file_path.startswith("0x"):
            continue
        if file_path.replace(r"/c0[0-9]/", source_color) in used_files:
            continue
        used_files.append(file_path)

        new_file_path = re.sub(r"c0[0-9]", target_color, file_path, 1)
        
        # Don't share if the file already exists in the mod
        if new_file_path in existing_files:
            continue
            
        # Basic filter for textures (ya no filtramos archivos de audio)
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in never_share_extensions:
            # Only don't share if there are other similar files for that alt
            similar_files_exist = False
            file_base_name = os.path.basename(file_path)
            dir_name = os.path.dirname(new_file_path)
            
            for existing_file in existing_files:
                if dir_name in existing_file:
                    similar_files_exist = True
                    break
                    
            if similar_files_exist:
                continue
        
        # Determine target section
        share_to = "share-to-vanilla"
        if "motion/" in file_path or "camera/" in file_path:
            share_to = "share-to-added"
        elif "sound/bank/fighter" in file_path:
            # Siempre añadir archivos de sonido a share-to-added
            share_to = "share-to-added"

        # Add the file to the corresponding section
        if file_path not in resulting_config[share_to]:
            resulting_config[share_to][file_path] = []
        
        if new_file_path not in resulting_config[share_to][file_path]:
            resulting_config[share_to][file_path].append(new_file_path)

def RecursiveRewrite(info,current_alt,target_alt):
    print(info.replace(current_alt,target_alt))
    return info.replace(current_alt,target_alt)

def main(mod_directory, hashes_file, fighter_name, current_alt, target_alt, share_slot, out_dir):
    # get all of the files the mod modifies
    # fighter_files is already loaded in init()
    
    # make the out directory if it doesn't exist
    if (not os.path.exists(out_dir)) and out_dir!="":
        os.mkdir(out_dir)

    reslotted_files, new_fighter_files = reslot_fighter_files(mod_directory, fighter_files, current_alt, target_alt, share_slot, out_dir, fighter_name)
    
    # Reorganize new-dir-files so that fighter/{fighter_name}/cmn is last
    if f"fighter/{fighter_name}/cmn" in resulting_config["new-dir-files"]:
        # Save the transplanted effects
        transplant_effects = resulting_config["new-dir-files"].pop(f"fighter/{fighter_name}/cmn")
        
        # Create a new ordered dictionary
        ordered_new_dir_files = {}
        
        # Add all original entries
        for key in resulting_config["new-dir-files"]:
            ordered_new_dir_files[key] = resulting_config["new-dir-files"][key]
            
        # Add the transplanted effects entry at the end
        ordered_new_dir_files[f"fighter/{fighter_name}/cmn"] = transplant_effects
        
        # Replace the original dictionary with the ordered one
        resulting_config["new-dir-files"] = ordered_new_dir_files

def init(hashes_file, mod_directory, newConfig):
    # load dir_info_with_files_trimmed.json for dir addition config gen
    global dirs_data
    global file_array
    global existing_files
    global existing_config
    global resulting_config
    global fighter_files
    global known_files
    
    # First detect all files in the mod folder
    fighter_files = find_fighter_files(mod_directory)
    
    # Load all known files from vanilla game
    known_files = set(map(lambda x: x.strip(), open(hashes_file, 'r').readlines()))
    
    # Ordered configuration structure with the exact order requested by the user
    existing_config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "share-to-vanilla": {},
        "new-dir-files": {},
        "share-to-added": {}
    }
    
    # If there's an existing configuration, load it but maintain the desired order
    if (not newConfig):
        existing_config_file = mod_directory + "/config.json"
        if (os.path.isfile(existing_config_file)):
            try:
                with open(existing_config_file, "r", encoding='utf-8') as f:
                    config = json.load(f)
                    # Maintain the correct order of sections
                    if "new-dir-infos" in config:
                        existing_config["new-dir-infos"] = config["new-dir-infos"]
                    if "new-dir-infos-base" in config:
                        existing_config["new-dir-infos-base"] = config["new-dir-infos-base"]
                    if "share-to-vanilla" in config:
                        existing_config["share-to-vanilla"] = config["share-to-vanilla"]
                    if "new-dir-files" in config:
                        existing_config["new-dir-files"] = config["new-dir-files"]
                    if "share-to-added" in config:
                        existing_config["share-to-added"] = config["share-to-added"]
                    f.close()
            except Exception as e:
                print(f"Error loading config.json: {e}")
                # If there's an error, use the default configuration
                pass

    resulting_config = existing_config
    
    # Create the list of existing files based on the files in the mod
    existing_files = fighter_files.copy()
    
    with open("dir_info_with_files_trimmed.json", "r") as f:
        res = json.load(f)
        dirs_data = res["dirs"]
        file_array = res["file_array"]
        f.close()


if __name__ == "__main__":
    try:
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6],sys.argv[7])
    except IndexError:
        usage()