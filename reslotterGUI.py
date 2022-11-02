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


def Init():
	root.hashes= os.getcwd() +"/Hashes_all.txt"
	if (not os.path.isfile(root.hashes)):
		messagebox.showerror(root.title(),"Hashes_all.txt does not exist in this directory")
		webbrowser.open("https://github.com/ultimate-research/archive-hashes/blob/master/Hashes_all")
		root.destroy()
		sys.exit("no hashes")


#open folder dialogue
def SetsearchDir():
    messagebox.showinfo(root.title(),"Select your mod's main folder")
    searchDir = filedialog.askdirectory(title = "Select your mod's main folder")
    if (searchDir == ""):
        if (firstLoad):
        	root.destroy()
        	sys.exit("User exited")
    if (IsValidSearch(searchDir) == False):
        messagebox.showerror(root.title(),"Please select the root of your mod's folder! This folder should contain a fighter folder within it!")
        if (firstLoad):
        	root.destroy()
        	sys.exit("Not a fighter folder")
    return searchDir

#make sure that it is a validated search folder, otherwise quit
def IsValidSearch(searchDir):
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
        print("no search")
        searchDir = SetsearchDir()
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
                root.destroy(searchDir)
                sys.exit("exited prompt")
        else:
            searchDir = SetsearchDir()

    if (searchDir == "" and not firstLoad):
    	return

    root.searchDir = searchDir
    #Write new location to config file      
    config.set("DEFAULT","searchDir",root.searchDir)
    with open('config.ini', 'w+') as configfile:
            config.write(configfile)

root.fighters= []
root.slots = []

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

	if ("eflame" in fighters or "elight" in fighters):
		messagebox.showwarning(root.title(),"Heads up, Pyra and Mythra cannot use additional slots. You might have to double check their UI files, too")


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

def MainWindow():
	root.deiconify()
	root.header = Label(root, text="", bd=1, relief=SUNKEN, anchor=N)
	root.header.pack(side = TOP, fill=X)
	UpdateHeader()

	root.comboFighter = ttk.Combobox(root, width = 8)

	root.comboFighter['values'] = [f for f in root.fighters]
	root.comboFighter.current(0)
	root.comboFighter.pack()

	frame = Frame(root)
	frame.pack(pady=5)

	frameCombos = Frame(frame)
	frameCombos.pack(side = TOP,padx=5)
	
	root.sources = []
	root.targets = []
	for i in range(root.maxSources):
		#only use the sources provided
		textSource = "c0"+str(i)
		if (not textSource in root.slots) and (root.exclusive):
			continue
		if (i>=8):
			textSource = "+"+textSource

		strSource = StringVar()
		strTarget = StringVar()

		#Add a header before listing each source
		if (i==0):
			headerText = Frame(frameCombos)
			headerText.pack(side = TOP)
			headerSource = Label(headerText,text="Source")
			headerSource.pack(side = LEFT)
			headerTarget = Label(headerText,text="Target", width = 8)
			headerTarget.pack(side = RIGHT)

		comboEntry = Frame(frameCombos)
		comboEntry.pack()

		labelSource = Label(comboEntry,text=textSource)
		labelSource.pack(side = LEFT)
		root.sources.append(labelSource)

		separater = Frame(comboEntry,width = 8)
		separater.pack(side = LEFT)
		
		#Add possible combo select values
		comboTarget = ttk.Combobox(comboEntry, width = 8)
		values = [""]
		for m in range(root.maxSlots):
			textSlot = "c0"+str(m)
			#don't add 0 to double/triple digits
			if (m>=10):
				textSlot = "+c"+str(m)
			#add + to additional slots
			elif (m>=8):
				textSlot = "+"+textSlot
			values.append(textSlot)

		comboTarget['values'] = values
		comboTarget.current(0)
		comboTarget.pack(side = RIGHT)
		root.targets.append(comboTarget)

	root.excludeCheckVariable = IntVar(value=1)
	root.excludeCheck = Checkbutton(root, text='Exclude Other Alts',variable=root.excludeCheckVariable, onvalue=1, offvalue=0)
	root.excludeCheck.pack()

	root.cloneCheckVariable = IntVar(value=1)
	root.cloneCheck = Checkbutton(root, text='Copy To New Folder',variable=root.cloneCheckVariable, onvalue=1, offvalue=0)
	root.cloneCheck.pack()

	buttons = Frame(root,width = 8)
	buttons.pack(side = BOTTOM,pady=10)

	button = Button(buttons, text="Change Slots", command=Reslot).pack(side = LEFT,padx=5)
	button = Button(buttons, text="Reconfig", command=Reconfig).pack(side = RIGHT,padx=5)
	root.protocol("WM_DELETE_WINDOW", quit)

	root.minsize(175, 150+len(root.targets)*20)

	#Menubar
	root.menubar = Menu(root)
	root.filemenu = Menu(root.menubar, tearoff=0)
	root.filemenu.add_command(label="Slot Addition Guide", command=OpenGuide)
	root.filemenu.add_command(label="Open README", command=OpenReadMe)
	root.filemenu.add_command(label="Exit", command=quit)
	root.menubar.add_cascade(label="File", menu=root.filemenu)
	root.config(menu=root.menubar)



def Reslot():
	RunReslotter(False)
def Reconfig():
	RunReslotter(True)

def RunReslotter(onlyConfig=False):
	fighter = root.comboFighter.get()
	exclude = (root.excludeCheckVariable.get() and not onlyConfig)

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
			targetText = "c0"+str(i)
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
		if (targetText in targetText):
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
	config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "share-to-vanilla": {},
        "share-to-added": {},
        "new-dir-files": {}
    }
	reslotter.init(root.hashes)

	for i in range(len(root.sources)):
		source = sources[i]
		target = targets[i]
		if (target == "" and exclude):
			continue
		# elif (source==target and clone==False):
		# 	continue

		#excludeCall = "Y" if exclude else "N"
		subcall = ["reslotter.py",root.searchDir,root.hashes,fighter,source,target,targetDir]
		print("Changing "+fighter+"'s "+source+" mod to "+target+"...")
		try:
			reslotter.main(subcall[1],subcall[2],subcall[3],subcall[4],subcall[5],subcall[6])
			succeeded=True
		except IndexError:
			reslotter.usage()

	if succeeded:
		newConfigLocation = targetDir + '/config.json'
		with open(newConfigLocation, 'w+', encoding='utf-8') as f:
			json.dump(reslotter.resulting_config, f, ensure_ascii=False, indent=4)

		messagebox.showinfo(root.title(),"Finished!")
		webbrowser.open(targetDir)
	else:
		messagebox.showerror(root.title(),"Failed to reslot")

	root.destroy()
	sys.exit("success")


def quit():
	root.destroy()
	sys.exit("user exited")

def main():
	Init()
	InitSearch()
	SetFighter()
	MainWindow()

main()
root.mainloop()
