import os, sys, json, reslotter, time, subprocess

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


def main(mods_directory, only_extra_slots):
    global special_default_slots

    mods_directory = add_slash(mods_directory)

    to_remove = []


    character_used_slots = {}

    mod_folders = os.listdir(mods_directory)

    for mod_folder in mod_folders:
        new_mod_folder = add_slash(mod_folder)
        internal_folders = os.listdir(mods_directory+new_mod_folder) 
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

            print(slots)

            for old_slot in slots:
                slot = int("1"+old_slot[1:])
                share_slot = "c00"
                if slot > 107:
                    if "share-to-added" in config.keys():
                        for key in config["share-to-added"].keys():
                            if f"{character}/{old_slot}" in config["share-to-added"][key]:
                                slot_index = config["share-to-added"][key].split("/").index(old_slot)
                                share_slot = key.split("/")[slot_index]
                                break
                else:
                    if character not in special_default_slots.keys():
                        share_slot = "c00"
                        available_slots = ["c00", "c01", "c02", "c03", "c04", "c05", "c06", "c07"]
                    elif isinstance(special_default_slots[special_default_slots], dict):
                        for slot_default in special_default_slots[special_default_slots].keys():
                            if old_slot in special_default_slots[special_default_slots][slot_default]:
                                share_slot = slot_default
                                available_slots = special_default_slots[special_default_slots][slot_default]
                                break
                    else: 
                        share_slot = old_slot
                        available_slots = [old_slot]

                if character in character_used_slots.keys():
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
                else:
                    if not only_extra_slots: 
                        if share_slot != "c00": new_slot = "1"+share_slot[1:]
                        else: new_slot = "100"
                        character_used_slots[character] = []
                    else: 
                        new_slot = "108"
                        character_used_slots[character] = ["100", "101", "102", "103", "104", "105", "106", "107"]
                character_used_slots[character].append(new_slot)


                process = subprocess.run(['python', 'reslotter.py', mods_directory+new_mod_folder.rstrip("/"), "Hashes_all.txt", character, old_slot, "c"+new_slot[1:], share_slot, f"{mods_directory}New {new_mod_folder.rstrip('/')}"])
                # subprocess used instead to ensure cache is cleared between runs. Without this each subsequent run of the same character fails

                #reslotter.main(mods_directory+new_mod_folder.rstrip("/"), "Hashes_all.txt", character, old_slot, "c"+new_slot[1:], share_slot, f"{mods_directory}New {new_mod_folder.rstrip('/')}")
                to_remove.append(new_mod_folder)
                new_mod_folder = f"New {new_mod_folder}"
    for remove_me in to_remove:
        for attempt_number in range(10):
            try:
                os.remove(mods_directory+remove_me)
                break
            except:
                time.sleep(0.1)
                print("Failed to remove ",mods_directory+remove_me)
                pass



if __name__ == "__main__":
    if len(sys.argv) == 3:
        mods_directory = sys.argv[1]
        only_extra_slots = sys.argv[2]
    elif len(sys.argv) == 2:
        mods_directory = sys.argv[1]
        only_extra_slots = input("Only use extra slots (true/false): ")
    else:
        mods_directory = input("Mods directory: ")
        only_extra_slots = input("Only use extra slots (true/false): ")

    if only_extra_slots[0].lower() == "t": only_extra_slots = True
    else: only_extra_slots = False

    main(mods_directory, only_extra_slots)