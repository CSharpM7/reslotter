import os
import os.path
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import sys
import shutil
import webbrowser
import json
import re
import xml.etree.ElementTree as ET

import reslotter

root = Tk()
root.programName="Reslotter GUI"
root.title("")
root.withdraw()
root.maxSources = 256
root.maxSlots = 256
root.exclusive = True
root.UnsavedChanges=False

#Config options
import configparser
config = configparser.ConfigParser()
defaultConfig = configparser.ConfigParser()
defaultConfig['DEFAULT'] = {
    'searchDir' : ""
    }
def CreateConfig():
    print("creating valid config")
    with open('config.ini', 'w+') as configfile:
        defaultConfig.write(configfile)
    config.read('config.ini')

#create a config if necessary
if (not os.path.isfile(os.getcwd() + r"\config.ini")):
    CreateConfig()
config.read('config.ini')


def Init(args):

	#Check for hashes_all.txt
	root.hashes= os.getcwd() +"/Hashes_all.txt"
	if (not os.path.isfile(root.hashes)):
		messagebox.showerror(root.title(),"Hashes_all.txt does not exist in this directory")
		webbrowser.open("https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all")
		root.destroy()
		sys.exit("no hashes")

	#Load mod via drag n drop if possible
	if (len(args)>1):     
		if (not IsValidSearch(args[1])): 
			messagebox.showerror(root.title(),"Dropped folder is not a valid mod folder!")
		else:
			config.set("DEFAULT","searchDir",args[1])
			root.searchDir = args[1]
			with open('config.ini', 'w+') as configfile:
				config.write(configfile)
			return

	if (InitSearch(args)==False):
		root.destroy(searchDir)
		sys.exit("exited prompt or folder does not exist")


#open folder dialogue
def SetsearchDir(firstLoad=True):
    messagebox.showinfo(root.title(),"Select your mod's main folder")
    searchDir = filedialog.askdirectory(title = "Select your mod's main folder")
    if (searchDir == ""):
        if (firstLoad):
        	root.destroy()
        	sys.exit("User exited")
    elif (IsValidSearch(searchDir) == False):
        messagebox.showerror(root.title(),"Please select the root of your mod's folder! This folder should contain a fighter folder within it!")
        if (firstLoad):
        	root.destroy()
        	sys.exit("Not a fighter folder")
    return searchDir

#make sure that it is a validated search folder, otherwise quit
def IsValidSearch(searchDir):
	if (not os.path.isdir(searchDir)):
		return
	whitelist = ["fighter","sound","ui"]
	subfolders = [f.path for f in os.scandir(searchDir) if f.is_dir()]
	for dirname in list(subfolders):
		for w in list(whitelist):
			folderName = os.path.basename(dirname) 
			if (folderName.lower() == w.lower()):
				return True
	return False
        

#Set Search Dir
def InitSearch(firstLoad=True):
    searchDir = config["DEFAULT"]["searchDir"]
    if not (os.path.isdir(searchDir) and firstLoad):
        searchDir = ""

    #Get or Set root.searchDir
    if (searchDir == ""):
        searchDir = SetsearchDir(firstLoad)
    else:
        if (IsValidSearch(searchDir)):
            basename = os.path.basename(searchDir)
            res = messagebox.askquestion(root.title(), 'Use most recent search directory? ('+basename+')')
            if res == 'yes':
                print("using same search dir")
            elif res == 'no':
                searchDir = SetsearchDir()
                print("new search directory")
            else:
                return False
        else:
            searchDir = SetsearchDir(firstLoad)

    if (searchDir == "" and not firstLoad):
    	return False

    root.searchDir = searchDir
    #Write new location to config file      
    config.set("DEFAULT","searchDir",root.searchDir)
    with open('config.ini', 'w+') as configfile:
        config.write(configfile)

def GetFightersFromFolders(folders):
	fighters = []
	for folder in folders:
		fighter = os.path.basename(folder)
		if (fighter != "common"):
			fighters.append(fighter)
			#find slots
			modelfolders = [f.path for f in os.scandir(folder+"/model") if f.is_dir()]
			for m in modelfolders:
				slots = [f.path for f in os.scandir(m) if f.is_dir()]
				for s in slots:
					slot = os.path.basename(s)
					if not slot in root.slots:
						root.slots.append(slot)
	return fighters

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def GetFightersFromFiles(folders):
	fighters = []
	for f in folders:
		if (os.path.basename(f) == "replace" or os.path.basename(f) == "replace_patch"):
			fighterfolders = [f.path for f in os.scandir(f+"/chara") if f.is_dir()]
			return GetFightersFromFiles(fighterfolders)

		for (dirpath, dirnames, filenames) in os.walk(f):
			for filename in filenames:
				#we need the last and second to last _
				unders = filename.count("_")
				firstUnder = find_nth(filename,"_",unders-1)
				secondUnder = find_nth(filename,"_",unders)
				fighter = filename[firstUnder+1:secondUnder]
				slot = filename[secondUnder+1:filename.index(".")]
				if (not "c" in slot):
					slot = "c"+slot

				if not fighter in fighters:
					fighters.append(fighter)
				if not slot in root.slots:
					root.slots.append(slot)

	return fighters
	

def SetFighter():
	root.fighters= []
	root.slots = []
	fighters = []
	fighterFolder = root.searchDir+"/fighter"
	uiFolder = root.searchDir+"/ui"
	soundFolder = root.searchDir+"/sound/bank"

	#If no fighter model, check for ui
	if (not os.path.isdir(fighterFolder)):
		#if no ui, check for sound
		if (not os.path.isdir(uiFolder)):
			if (not os.path.isdir(soundFolder)):
				messagebox.showerror(root.title(),"This mod has no fighter folders")
				root.destroy()
				sys.exit("no fighter")
			else:
				soundfolders = [f.path for f in os.scandir(soundFolder) if f.is_dir()]
				fighters = GetFightersFromFiles(soundfolders)
		else:
			uifolders = [f.path for f in os.scandir(uiFolder) if f.is_dir()]
			fighters = GetFightersFromFiles(uifolders)
	else:
		fighterfolders = [f.path for f in os.scandir(fighterFolder) if f.is_dir()]
		fighters = GetFightersFromFolders(fighterfolders)

	root.fighters = fighters

	#if ("eflame" in fighters or "elight" in fighters):
#		messagebox.showwarning(root.title(),"Heads up, Pyra and Mythra cannot use additional slots. You might have to double check their UI files, too")

def OpenNewFolder():
	if (InitSearch(False) == False):
		return
	SetFighter()
	RefreshMainWindow()

def OpenReadMe():
	webbrowser.open('https://github.com/CSharpM7/reslotter')
def OpenGuide():
	webbrowser.open('https://docs.google.com/document/d/1JQHDcpozZYNbO2IAzgG7GrBWC5OJc1_xfXmMw55pGhM')

#truncate strings for labels
def truncate(string,direciton=W,limit=20,ellipsis=True):
	if (len(string) < 3):
		return string
	text = ""
	addEllipsis = "..." if (ellipsis) else ""
	if direciton == W:
		text = addEllipsis+string[len(string)-limit:len(string)]
	else:
		text = string[0:limit]+addEllipsis
	return text

def UpdateHeader(newheader="",color="black"):
	prefix="*" if root.UnsavedChanges else ""
	workspace= "("+os.path.basename(root.searchDir)+")"

	if (newheader!=""):
		newheader = " - "+newheader

	root.header.config(text = prefix+workspace+newheader, fg = color)

def CreateMainWindow():
	root.deiconify()
	root.header = Label(root, text="", bd=1, relief=SUNKEN, anchor=N)
	root.header.pack(side = TOP, fill=X)
	UpdateHeader()

	root.comboFighter = ttk.Combobox(root, width = 8)
	root.comboFighter.pack()

	frame = Frame(root)
	frame.pack(pady=5)

	root.frameCombos = Frame(frame)
	root.frameCombos.pack(side = TOP,padx=5)
	
	buttons = Frame(root,width = 8)
	buttons.pack(side = BOTTOM,pady=10)
	button = Button(buttons, text="Change Slots", command=Reslot).pack(side = LEFT,padx=5)
	root.configButton = Button(buttons, text="Reconfig", command=Reconfig)
	root.configButton.pack(side = RIGHT,padx=5)

	prcEntry = Frame(root)
	prcEntry.pack(side = BOTTOM)
	labelPRC = Label(prcEntry,text="New Max Slots")
	labelPRC.pack(side = LEFT)
	separater = Frame(prcEntry,width = 8)
	separater.pack(side = LEFT)

	root.comboPRC = ttk.Combobox(prcEntry, width = 8)
	values = [""]
	for m in range(9,root.maxSlots):
		textSlot = m
		values.append(textSlot)
	root.comboPRC['values'] = values
	root.comboPRC.current(0)
	root.comboPRC.pack(side = RIGHT)

	root.excludeCheckVariable = IntVar(value=1)
	root.excludeCheck = Checkbutton(root, text='Exclude Other Alts',variable=root.excludeCheckVariable, onvalue=1, offvalue=0)
	root.excludeCheck.pack(side = BOTTOM)
	root.cloneCheckVariable = IntVar(value=1)
	root.cloneCheck = Checkbutton(root, text='Copy To New Folder',variable=root.cloneCheckVariable, onvalue=1, offvalue=0)
	root.cloneCheck.pack(side = BOTTOM)


	#Menubar
	root.menubar = Menu(root)
	root.filemenu = Menu(root.menubar, tearoff=0)
	root.filemenu.add_command(label="Open New Mod Folder", command=OpenNewFolder)
	root.filemenu.add_command(label="Slot Addition Guide", command=OpenGuide)
	root.filemenu.add_command(label="Open README", command=OpenReadMe)
	root.filemenu.add_command(label="Exit", command=quit)
	root.menubar.add_cascade(label="File", menu=root.filemenu)
	root.config(menu=root.menubar)
	root.protocol("WM_DELETE_WINDOW", quit)

	RefreshMainWindow()

def OnTargetChange(*args):
	root.UnsavedChanges=True
	UpdateHeader()

def RefreshMainWindow():
	root.UnsavedChanges=False
	UpdateHeader()
	root.comboFighter['values'] = [f for f in root.fighters]
	root.comboFighter.current(0)

	for widget in root.frameCombos.winfo_children():
		widget.destroy()

	root.sources = []
	root.targets = []
	root.strTargets = {}
	for i in range(root.maxSources):
		#only use the sources provided
		textSource = "c%02d" % i
		if (not textSource in root.slots) and (root.exclusive):
			continue
		if (i>=8):
			textSource = "+"+textSource

		strSource = StringVar()
		strTarget = StringVar()

		#Add a header before listing each source
		if (i==0):
			headerText = Frame(root.frameCombos)
			headerText.pack(side = TOP)
			headerSource = Label(headerText,text="Source")
			headerSource.pack(side = LEFT)
			headerTarget = Label(headerText,text="Target", width = 8)
			headerTarget.pack(side = RIGHT)

		comboEntry = Frame(root.frameCombos)
		comboEntry.pack()

		labelSource = Label(comboEntry,text=textSource)
		labelSource.pack(side = LEFT)
		root.sources.append(labelSource)

		separater = Frame(comboEntry,width = 8)
		separater.pack(side = LEFT)
		
		root.strTargets.update({textSource:StringVar(name="")})
		strTarget= root.strTargets[textSource]
		#Add possible combo select values
		comboTarget = ttk.Combobox(comboEntry,textvar=strTarget, width = 8)
		values = [""]
		for m in range(root.maxSlots):
			textSlot = "c%02d" % m
			#add + to additional slots
			if (m>=8):
				textSlot = "+"+textSlot
			values.append(textSlot)

		comboTarget['values'] = values
		comboTarget.current(0)
		strTarget.trace_add('write',OnTargetChange)
		comboTarget.pack(side = RIGHT)
		root.targets.append(comboTarget)

		configText = "Rewrite Config" if (os.path.isfile(root.searchDir + "/config.json")) else "Create Config"
		root.configButton.config(text=configText)

	root.minsize(175, 130+len(root.targets)*30)


def Reslot():
	RunReslotter(False)
def Reconfig():
	RunReslotter(True)



Climber = ["popo","nana"]
Trainer = ["ptrainer","ptrainer_low","pzenigame","pfushigisou","plizardon"]
Aegis = ["element","eflame","elight"]

def CreatePRCXML(fighter,targetDir):
	newColors = [int(s) for s in re.findall(r'\b\d+\b',root.comboPRC.get())]
	if (len(newColors)==0):
		return

	prcFile = "/ui_chara_db.prcxml"
	print(os.getcwd() + prcFile)
	if (not os.path.isfile(os.getcwd() + prcFile)
		or not os.path.isfile(os.getcwd() + prcFile.replace("prcxml","txt"))
	):
		messagebox.showerror(root.title(),
			"Missing ui_chara_db.prcxml or ui_chara_db.txt in program directory! Cannot create a prcxml")
		return

	print("Creating prcxml...")

	prcLocation = targetDir+"/ui/param/database"
	try:
		os.makedirs(prcLocation)
	except:
		pass
	textureListFile = open(prcLocation+prcFile,'w')
	textureListFile.close()

	indexFile = open(os.getcwd() + prcFile.replace("prcxml","txt"),'r')
	indexes = indexFile.readlines()
	indexes = [index.rstrip() for index in indexes]
	indexFile.close()

	targetIndexes = []
	#Our lovely unique cases
	if (fighter in Climber):
		targetIndexes = [17]
	elif (fighter in Trainer):
		targetIndexes = [38,39,40,41]
	elif (fighter in Aegis):
		targetIndexes = [114,115,116,117,118]
	#Otherwise find the index via the fighter's name
	else:
		for i in range(len(indexes)):
			if (fighter == indexes[i].lower()):
				targetIndexes.append(i)

	if (len(targetIndexes)==0):
		print("prcxml error")
		return

	with open(os.getcwd()+prcFile, encoding='utf-8', errors='replace') as file:
		context = ET.iterparse(file, events=('end',))
		for event, elem in context:
			if elem.tag == 'hash40':
				index = elem.attrib['index']
				for targetIndex in targetIndexes:
					if (str(index)==str(targetIndex)):
						elem.text=""
						elem.tag = "struct"
						info = ET.SubElement(elem,'byte')
						info.set("hash","color_num")
						info.text = str(newColors[0])
			with open(prcLocation+prcFile, 'wb') as f:
				f.write(b"<?xml version=\"1.0\" encoding=\"UTF-16\"?>\n")
				f.write(ET.tostring(elem))
	print("Created!")


def RunReslotter(onlyConfig=False):
	currentFighter = root.comboFighter.get().lower()

	exclude = (root.excludeCheckVariable.get() and not onlyConfig)
	clone = (root.cloneCheckVariable.get() and not onlyConfig)

	if (exclude and not clone):
		res = messagebox.askquestion(root.title(), "If you want to use the same folder, but exclude all other alts,"
			"all mod files that are excluded will be deleted! Are you sure you want to do this?"
			)
		if res != 'yes':
			return

	sources=[""]*len(root.sources)
	targets=[""]*len(root.targets)
	usesAdditional=False

	targetName = ""
	knownTargets = 0
	#for each potential source, check if the UI exists for it. Then pair them together by source:target
	for i in range(len(root.sources)):
		sourceText = root.sources[i]["text"]
		sources[i] = sourceText.replace("+","")

		#get the cXX name of the target
		targetText = root.targets[i].get()
		#Replace it if doing reconfig
		if (onlyConfig):
			targetText = sourceText
		#Else If TargetText is empty, either append blank or append the same slot based on excluding
		elif (not "c" in targetText) and not onlyConfig:
			if (exclude):
				continue
			else:
				targetText = sourceText

		#Check if we're using added slots, then remove the +
		if ("+" in targetText) or (i>7 and onlyConfig):
			usesAdditional=True
		targetText = targetText.replace("+","")

		#For only 3 slots, append their slotid to the name of the new folder
		if (knownTargets<4):
			targetName=targetName+" "+targetText
			knownTargets+=1

		#Disallow a target with multiple sources
		if (targetText in targets):
			messagebox.showwarning(root.title(),"Multiple sources share the same target! Please keep each target slot unique")
			return
		targets[i] = targetText

	#Return if there are no targets selected and we are reslotting
	if (knownTargets==0 and not onlyConfig):
		messagebox.showwarning(root.title(),"No targets slots are selected!")
		return

	root.withdraw()
	print(targets)
	#set directory to clone everything to, or keep it the same
	targetName = " ("+targetName[1:]
	targetDir = root.searchDir+targetName+")" if (not onlyConfig) else root.searchDir

	#create target directory
	try:
		os.makedirs(targetDir)
	except:
		pass

	succeeded=False
	
	#Warm up the reslotter
	if (os.path.isfile(root.searchDir+"/config.json") and not onlyConfig):
		#At the moment, this program can only append entries, rather than 
		res = messagebox.askquestion(root.title(), "This mod already has a config.json. Would you like to generate a new one?"
			"\n(If no, this will add on to the current config, which would increase the config's filesize)"
			)
		if (res != "yes" and res != "no"):
			return
		reslotter.init(root.hashes,root.searchDir,res == 'yes')
	else:
		reslotter.init(root.hashes,root.searchDir,onlyConfig)

	#Populate with more fighters for these unique cases
	fighters = [currentFighter]
	if (currentFighter in Climber):
		fighters= Climber
	if (currentFighter in Trainer):
		fighters= Trainer
	if (currentFighter in Aegis):
		fighters= Aegis

	for fighter in fighters:
		for i in range(len(root.sources)):
			source = sources[i]
			target = targets[i]
			if (target == "" and exclude==True):
				continue

			#excludeCall = "Y" if exclude else "N"
			subcall = ["reslotter.py",root.searchDir,root.hashes,fighter,source,target,targetDir,"Y"]
			print("Changing "+fighter+"'s "+source+" mod to "+target+"...")

			try:
				reslotter.main(subcall[1],subcall[2],subcall[3],subcall[4],subcall[5],subcall[6],subcall[7])
				succeeded=True
			except IndexError:
				reslotter.usage()

	if succeeded:
		if (not clone and not onlyConfig):
			shutil.rmtree(root.searchDir)
			os.rename(targetDir,root.searchDir)
			targetDir=root.searchDir

		CreatePRCXML(currentFighter,targetDir)

		newConfigLocation = targetDir + '/config.json'
		with open(newConfigLocation, 'w+', encoding='utf-8') as f:
			json.dump(reslotter.resulting_config, f, ensure_ascii=False, indent=4)

		messagebox.showinfo(root.title(),"Finished!")
		webbrowser.open(targetDir)
	else:
		messagebox.showerror(root.title(),"Failed to reslot")

	root.deiconify()
	root.UnsavedChanges=False
	UpdateHeader()

def quit():
	root.destroy()
	sys.exit("user exited")

def main(args):
	Init(args)
	SetFighter()
	CreateMainWindow()


main(sys.argv)
root.mainloop()
