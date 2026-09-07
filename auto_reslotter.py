import os, sys, json, reslotter, time, subprocess, shutil

with open("reslot_mapping.json", "r") as mapping:
    special_default_slots = json.load(mapping)



def add_slash(directory):
    if directory[-1] != "/" and directory[-1] != "\\": directory += "/"
    return directory

def get_slots(directory, slots):
    internal_folders = os.listdir(directory)
    for temp_internal_folder in internal_folders:
        temp_folders = os.listdir(directory+temp_internal_folder)
        for temp_folder in temp_folders:
            if len(temp_folder) > 3 or temp_folder[0] != "c": slots = get_slots(directory+add_slash(temp_internal_folder), slots)
            elif temp_folder not in slots: slots.append(temp_folder)

    return slots


def main(mods_directory, start_slotting_from):
    global special_default_slots

    if start_slotting_from[0] == "c": start_slotting_from = "1"+start_slotting_from[1:]
    elif len(start_slotting_from) == 2: start_slotting_from = "1"+start_slotting_from

    mods_directory = add_slash(mods_directory)

    to_remove = []


    character_used_slots = {}

    mod_folders = reslotter.GetValidModsFolders(mods_directory)

    temp_mod_folders = []

    for temp_folder in mod_folders:
        temp_mod_folders.append(temp_folder.split("/")[-1].split("\\")[-1])
    mod_folders = temp_mod_folders

    for mod_folder in mod_folders:
        new_mod_folder = add_slash(mod_folder)
        internal_folders = os.listdir(mods_directory+new_mod_folder) 
        stored_folder_name = mod_folder
        if "fighter" in internal_folders: internal_folder = "fighter"
        elif "effects" in internal_folders: internal_folder = "effects"
        elif "ui" in internal_folders: internal_folder = "ui"
        else:
            print(f"Error, {new_mod_folder} does not contain character data")
            continue

        config = {}

        internal_folder = add_slash(internal_folder)



        characters = os.listdir(mods_directory+new_mod_folder+internal_folder)

        for character in characters:
            slots = get_slots(mods_directory+new_mod_folder+internal_folder+add_slash(character), [])

            #print(slots)
            new_slots = []

            for old_slot_index in range(len(slots)):
                old_slot = slots[old_slot_index]
                slot = int("1"+old_slot[1:])
                share_slot = "c00"
                if slot > 107:
                    if "share-to-added" in config.keys():
                        for key in config["share-to-added"].keys():
                            if f"{character}/{old_slot}" in config["share-to-added"][key]:
                                slot_index = config["share-to-added"][key].split("/").index(old_slot)
                                share_slot = key.split("/")[slot_index]
                                break
                if character not in special_default_slots.keys():
                    share_slot = "c00"
                    available_slots = ["c00", "c01", "c02", "c03", "c04", "c05", "c06", "c07"]
                elif isinstance(special_default_slots[character], dict):
                    for slot_default in special_default_slots[character].keys():
                        if old_slot in special_default_slots[character][slot_default]:
                            share_slot = slot_default
                            available_slots = special_default_slots[character][slot_default]
                            break
                else: 
                    share_slot = old_slot
                    available_slots = [old_slot]

                if character not in character_used_slots.keys():

                    character_used_slots[character] = []
                    for pad_slot in range(100, int(start_slotting_from)):
                        if pad_slot != int(start_slotting_from):
                            character_used_slots[character].append(str(pad_slot))

                for temp_slot_index in range(100):
                    temp_slot = str(temp_slot_index+100)
                    if temp_slot not in character_used_slots[character]:
                        if temp_slot_index < 8:
                            if f"c{temp_slot[1:]}" in available_slots: 
                                new_slot = temp_slot
                                break
                        else:
                            new_slot = temp_slot
                            break

                character_used_slots[character].append(new_slot)

                process = subprocess.run(['python', 'reslotter.py', mods_directory+new_mod_folder.rstrip("/"), "Hashes_all.txt", character, old_slot, "c"+new_slot[1:], share_slot, f"{mods_directory}New {new_mod_folder.rstrip('/')}", "False", str(new_slots)])
                # subprocess used instead to ensure cache is cleared between runs. Without this each subsequent run of the same character fails

                #reslotter.main(mods_directory+new_mod_folder.rstrip("/"), "Hashes_all.txt", character, old_slot, "c"+new_slot[1:], share_slot, f"{mods_directory}New {new_mod_folder.rstrip('/')}")
                
                to_remove.append(new_mod_folder)
                new_slots.append("c"+str(new_slot)[1:])

    for remove_me in to_remove:
        for attempt_number in range(10):
            try:
                shutil.rmtree(mods_directory+remove_me)
                break
            except:
                time.sleep(0.1)
                print("Failed to remove ",mods_directory+remove_me)
                pass



if __name__ == "__main__":
    if len(sys.argv) == 3:
        mods_directory = sys.argv[1]
        start_slotting_from = sys.argv[2]
    elif len(sys.argv) == 2:
        mods_directory = sys.argv[1]
        start_slotting_from = input("Start slotting from slot (inclusive | cXX): ")
    else:
        mods_directory = input("Mods directory: ")
        start_slotting_from = input("Start slotting from slot (inclusive | cXX): ")

    main(mods_directory, start_slotting_from)