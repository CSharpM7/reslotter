#Original code by BluJay <https://github.com/blu-dev> and Jozz <https://github.com/jozz024/ssbu-skin-reslotter>
#Modified by Coolsonickirby to get it to work with dir addition
import os
import shutil
import sys
import json
import re

def usage():
    print("usage: python reslotter.py <mod_directory> <hashes_file> <fighter_name> <current_alt> <target_alt> <out_directory> <exclude other alts (Y/N)>")
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

def reslot_fighter_files(mod_directory, fighter_files, current_alt, target_alt, out_dir, fighter_name,exclude):
    reslotted_files = []
    for file in fighter_files:
        #Exclude will not include any other file outside of the current_alt
        if (exclude.lower()=="y"):
            if (not current_alt.strip('c') in file):
                continue

        # Since each directory has a different structure, we have to go through each directory separately
        if file.startswith(f"fighter/{fighter_name}"):
            if (exclude.lower()=="y"):
                if (not "/"+current_alt+"/" in file):
                    continue
            
            lookfor = f"/{current_alt}/"
            replace = f"/{target_alt}/"
            new_file = file.replace(lookfor, replace)
            
            #Used during "reconfig" to not copy files and simply add to the list of files for the config
            if target_alt != current_alt :
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))

            reslotted_files.append(new_file)

        #Unique to UI folders, we need to check if the filename contains 
        #"_fighter_name_" since all UI files are grouped together
        elif file.startswith("ui/replace/chara"):
            lookfor = f"{current_alt.strip('c')}.bntx"
            replace = f"{target_alt.strip('c')}.bntx"
            new_file = file.replace(lookfor, replace)

            print(target_alt+"/"+current_alt)
            if new_file.__contains__("_" + fighter_name + "_") and target_alt != current_alt :
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))

        elif file.startswith("ui/replace_patch/chara"):
            lookfor = f"{current_alt.strip('c')}.bntx"
            replace = f"{target_alt.strip('c')}.bntx"
            new_file = file.replace(lookfor, replace)

            if new_file.__contains__("_" + fighter_name + "_") and target_alt != current_alt :
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))

        elif file.startswith("sound/bank/fighter"):
            lookfor = f"_{current_alt}"
            replace = f"_{target_alt}"
            new_file = file.replace(lookfor, replace)

            if target_alt != current_alt :
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))
            reslotted_files.append(new_file)
        elif file.startswith(f"effect/fighter"):
            lookfor = f"{current_alt.strip('c')}"
            replace = f"{target_alt.strip('c')}"
            new_file = file.replace(lookfor, replace)
            if target_alt != current_alt :
                makeDirsFromFile(os.path.join(out_dir, new_file))
                shutil.copy(os.path.join(mod_directory, file), os.path.join(out_dir, new_file))
            reslotted_files.append(new_file)

    existing_files.extend(reslotted_files)
    if 7 < int(target_alt.strip("c")):
        current_alt_int = int(current_alt.strip("c"))
        if current_alt_int <= 7:
            add_new_slot(f"fighter/{fighter_name}", current_alt, target_alt)
            add_missing_files(reslotted_files, fighter_name, target_alt,True)
        else:
            current_alt_int = int(target_alt.strip("c")) % 8
            add_new_slot(f"fighter/{fighter_name}", f"c0{current_alt_int}", target_alt)
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

def add_new_slot(dir_info, source_slot, new_slot):
    folders = dir_info.split("/")
    target_dir = dirs_data

    for folder in folders:
        target_dir = target_dir["directories"][folder]

    if source_slot in target_dir["directories"]:
        source_slot_dir = target_dir["directories"][source_slot]
        source_slot_path = "%s/%s" % ((dir_info, source_slot))
        new_slot_dir_path = "%s/%s" % ((dir_info, new_slot))

        resulting_config["new-dir-infos"].append(new_slot_dir_path)

        # Deal with files
        addFilesToDirInfo(new_slot_dir_path, source_slot_dir["files"], new_slot)
        addSharedFiles(source_slot_dir["files"], source_slot, new_slot)

        for dir in source_slot_dir["directories"]:
            source_slot_base = f"{source_slot_path}/{dir}"
            new_slot_base = f"{new_slot_dir_path}/{dir}"
            resulting_config["new-dir-infos-base"][new_slot_base] = source_slot_base

    for dir in target_dir["directories"]:
        target_obj = target_dir["directories"][dir]
        if source_slot in target_obj["directories"]:
            source_slot_dir = target_obj["directories"][source_slot]
            source_slot_path = f"{dir_info}/{dir}/{source_slot}"
            new_slot_dir_path = f"{dir_info}/{dir}/{new_slot}"

            resulting_config["new-dir-infos"].append(new_slot_dir_path)

            # Deal with files
            addFilesToDirInfo(new_slot_dir_path, source_slot_dir["files"], new_slot)
            addSharedFiles(source_slot_dir["files"], source_slot, new_slot)

            # Deal with directories
            for child_dir in source_slot_dir["directories"]:
                source_slot_base = f"{source_slot_path}/{child_dir}"
                new_slot_base = f"{new_slot_dir_path}/{child_dir}"
                resulting_config["new-dir-infos-base"][new_slot_base] = source_slot_base


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

def addSharedFiles(src_files, source_color, target_color):
    used_files = []

    for index in src_files:
        file_path = file_array[index]
        if file_path.startswith("0x"):
            continue
        if file_path.replace(r"/c0[0-9]/", source_color) in used_files:
            continue
        used_files.append(file_path)

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

def main(mod_directory, hashes_file, fighter_name, current_alt, target_alt, out_dir,exclude):
    # get all of the files the mod modifies
    #fighter_files = find_fighter_files(mod_directory)

    # make the out directory if it doesn't exist
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    # reslot the files we use
    reslotted_files, new_fighter_files = reslot_fighter_files(mod_directory, fighter_files, current_alt, target_alt, out_dir, fighter_name,exclude)


def init(hashes_file,mod_directory):
    # load dir_info_with_files_trimmed.json for dir addition config gen
    global dirs_data
    global file_array
    global existing_files
    global resulting_config
    global fighter_files
    fighter_files = find_fighter_files(mod_directory)
    resulting_config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "share-to-vanilla": {},
        "share-to-added": {},
        "new-dir-files": {}
    }
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