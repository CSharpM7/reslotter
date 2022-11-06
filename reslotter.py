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
    for file in fighter_files:
        #Exclude any other file outside of the current_alt
        if (not current_alt.strip('c') in file):
            continue

        # Since each directory has a different structure, we have to go through each directory separately
        if file.startswith(f"fighter/{fighter_name}"):
            if (not "/"+current_alt+"/" in file):
                continue
            
            lookfor = f"/{current_alt}/"
            replace = f"/{target_alt}/"
            new_file = file.replace(lookfor, replace)
            
            #Used during "reconfig" to not copy files and simply add to the list of files for the config
            if out_dir != "":
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))

            reslotted_files.append(new_file)

        #Unique to UI folders, we need to check if the filename contains 
        #"_fighter_name_" since all UI files are grouped together
        elif file.startswith("ui/replace/chara") or file.startswith("ui/replace_patch/chara"):
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

        elif file.startswith("sound/bank/fighter"):
            lookfor = f"_{current_alt}"
            replace = f"_{target_alt}"
            new_file = file.replace(lookfor, replace)

            if out_dir != "":
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))
            reslotted_files.append(new_file)
        elif file.startswith(f"effect/fighter"):
            lookfor = f"{current_alt.strip('c')}"
            replace = f"{target_alt.strip('c')}"
            new_file = file.replace(lookfor, replace)
            if out_dir != "":
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))
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

    for file in reslotted_files:
        #Don't add oneslot effects to vanilla alts configs
        if (not is_new_slot and "effect" in file):
            continue
        if file not in known_files:
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

def addSharedFiles(src_files, source_color, target_color,share_slot):
    used_files = []

    for index in src_files:
        file_path = file_array[index]
        if file_path.startswith("0x"):
            continue
        if file_path.replace(r"/c0[0-9]/", source_color) in used_files:
            continue
        used_files.append(file_path)

        #file_path = file_path.replace(r"/c0[0-9]/", share_slot)

        new_file_path = re.sub(r"c0[0-9]", target_color, file_path, 1)
        if new_file_path in existing_files:
            continue

        share_to = "share-to-vanilla"
        if "motion/" in file_path or "camera/" in file_path:
            share_to = "share-to-added"

        if file_path not in resulting_config[share_to]:
            resulting_config[share_to][file_path] = []
        
        if new_file_path not in resulting_config[share_to][file_path]:
            resulting_config[share_to][file_path].append(new_file_path)

def RecursiveRewrite(info,current_alt,target_alt):
    print(info.replace(current_alt,target_alt))
    return info.replace(current_alt,target_alt)

def main(mod_directory, hashes_file, fighter_name, current_alt, target_alt, share_slot,out_dir):
    # get all of the files the mod modifies
    #fighter_files = find_fighter_files(mod_directory)

    # make the out directory if it doesn't exist
    if (not os.path.exists(out_dir)) and out_dir!="":
        os.mkdir(out_dir)

    reslotted_files, new_fighter_files = reslot_fighter_files(mod_directory, fighter_files, current_alt, target_alt, share_slot, out_dir, fighter_name)


def init(hashes_file,mod_directory,newConfig):
    # load dir_info_with_files_trimmed.json for dir addition config gen
    global dirs_data
    global file_array
    global existing_files
    global existing_config
    global resulting_config
    global fighter_files
    fighter_files = find_fighter_files(mod_directory)
    existing_config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "share-to-vanilla": {},
        "share-to-added": {},
        "new-dir-files": {}
    }
    #If there's an existing config, load it into existing_config to be transferred to resulting_config
    if (not newConfig):
        existing_config_file = mod_directory + "/config.json"
        if (os.path.isfile(existing_config_file)):
            with open(existing_config_file, "r") as f:
                config = json.load(f)
                existing_config = config
                f.close()

    resulting_config = existing_config

    existing_files = []
    # get all of the files in SSBU's Filesystem
    global known_files
    known_files = set(map(lambda x: x.strip(), open(hashes_file, 'r').readlines()))
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