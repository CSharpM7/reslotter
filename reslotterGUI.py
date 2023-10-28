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
root.OnlyUseSlotsInMod = True
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
	if (os.path.isfile(os.getcwd() + r"\config.ini")):
		os.remove(os.getcwd() + r"\config.ini")

	with open('config.ini', 'w+') as configfile:
		defaultConfig.write(configfile)
		config.read('config.ini')

#create a config if necessary
if (not os.path.isfile(os.getcwd() + r"\config.ini")):
    CreateConfig()
config.read('config.ini')

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
    if firstLoad:
        CreateConfig()
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
                searchDir = SetsearchDir(firstLoad)
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

def GetSlotsFromFolder(folder):
	foundSlots = []
	if (not os.path.isdir(folder)):
		return foundSlots

	#find slots
	modelfolders = [f.path for f in os.scandir(folder) if f.is_dir()]
	for m in modelfolders:
		slots = [f.path for f in os.scandir(m) if f.is_dir()]
		for s in slots:
			slot = os.path.basename(s)
			if not slot in root.slots:
				foundSlots.append(slot)
	return foundSlots

def GetFightersFromFolders(folders,fighter=""):
	fighters = []
	for folder in folders:
		foldername = os.path.basename(folder)
		if (fighter != "" and foldername != fighter):
			continue
		if (foldername != "common"):
			fighters.append(foldername)
			#find slots
			for s in GetSlotsFromFolder(folder+"/model"):
				root.slots.append(s)
			for s in GetSlotsFromFolder(folder+"/motion"):
				root.slots.append(s)
	return fighters

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def GetFightersFromFiles(folders,fighter=""):
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
				fightername = filename[firstUnder+1:secondUnder]
				slot = filename[secondUnder+1:filename.index(".")]
				if (not "c" in slot):
					slot = "c"+slot

				if (fighter != "" and fightername != fighter):
					continue
				if not fightername in fighters:
					fighters.append(fightername)
				if not slot in root.slots:
					root.slots.append(slot)

	return fighters
	
#Gets fighters from mod folder
def SetFighters(fighter=""):
	if (fighter==""):
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
				fighters = GetFightersFromFiles(soundfolders,fighter)
		else:
			uifolders = [f.path for f in os.scandir(uiFolder) if f.is_dir()]
			fighters = GetFightersFromFiles(uifolders,fighter)
	else:
		fighterfolders = [f.path for f in os.scandir(fighterFolder) if f.is_dir()]
		fighters = GetFightersFromFolders(fighterfolders,fighter)

	if (fighter==""):
		fighters.append("all")
		root.fighters = fighters

#Opens new folder, refreshes window too
def OpenNewFolder():
	if (InitSearch(False) == False):
		return
	CreateConfig()
	SetFighters()
	RefreshMainWindow()

def OpenReadMe():
	webbrowser.open('https://github.com/CSharpM7/reslotter')
def OpenGuide():
	webbrowser.open('https://docs.google.com/document/d/1JQHDcpozZYNbO2IAzgG7GrBWC5OJc1_xfXmMw55pGhM')

#Used to add * with unsaved changes
def UpdateHeader(newheader="",color="black"):
	prefix="*" if root.UnsavedChanges else ""
	workspace= "("+os.path.basename(root.searchDir)+")"

	if (newheader!=""):
		newheader = " - "+newheader

	root.header.config(text = prefix+workspace+newheader, fg = color)

class CreateToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 280   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

def CreateMainWindow():
	root.deiconify()
	root.header = Label(root, text="", bd=1, relief=SUNKEN, anchor=N)
	root.header.pack(side = TOP, fill=X)
	UpdateHeader()

	root.strFighter = StringVar(name="")
	root.comboFighter = ttk.Combobox(root,textvar=root.strFighter, width = 16)
	root.comboFighter.pack()
	root.strFighter.trace_add('write',OnFighterChange)

	headerText = Frame(root)
	headerText.pack()
	root.headerSource = Label(headerText,text="Current\nSlot",width = 8)
	root.headerSource.pack(side = LEFT, expand=True)
	root.headerSource_ttp = CreateToolTip(root.headerSource, \
	'The slot the mod is currently on')

	separater = Frame(headerText,width = 8)
	separater.pack(side = LEFT)

	root.headerTarget = Label(headerText,text="New\nSlot",width = 8)
	root.headerTarget.pack(side = LEFT, expand=True)
	root.headerTarget_ttp = CreateToolTip(root.headerTarget, \
	'The slot you want the mod to go on')

	separater = Frame(headerText,width = 8)
	separater.pack(side = LEFT)

	root.headerShare = Label(headerText,text="Share\nFrom", width = 10)
	root.headerShare.pack(side = LEFT, expand=True)
	root.headerShare_ttp = CreateToolTip(root.headerShare, \
	'For additional slots, the slot the mod is originally based on.'
	'\nFor Male/Female fighters, this could be either 0 or 1.'
	'\nFor fighters with other special skins, it depends (ie 0,1,2,3 for Hero or 0/6 for Sephiroth.')

	frame = Frame(root)
	frame.pack(pady=5)

	root.frameCombos = Frame(frame)
	root.frameCombos.pack(padx=5)
	
	buttons = Frame(root,width = 8)
	buttons.pack(side = BOTTOM,pady=10)
	root.reslotButton = Button(buttons, text="Change Slots", command=Reslot)
	root.reslotButton.pack(side = LEFT,padx=5)
	root.configButton = Button(buttons, text="Reconfig", command=Reconfig)
	root.configButton.pack(side = RIGHT,padx=5)

	redirectEntry = Frame(root)
	redirectEntry.pack(side = BOTTOM)
	root.redirectLabel = Label(redirectEntry,text="name_id, start color")
	root.redirectLabel.pack(side = LEFT)
	separater = Frame(redirectEntry,width = 8)
	separater.pack(side = LEFT)

	root.redirectStartVariable = IntVar(value=0)
	root.redirectStartSpinbox = Spinbox(redirectEntry, from_=0, to=255,width = 3)
	root.redirectStartSpinbox.pack(side = RIGHT)
	separater = Frame(redirectEntry,width = 4)
	separater.pack(side = RIGHT)

	root.redirectEntryVariable = StringVar(value="")
	root.redirectEntryCheck = Entry(redirectEntry,textvariable=root.redirectEntryVariable)
	root.redirectEntryCheck.pack(side = RIGHT)

	root.redirect_ttp = CreateToolTip(root.redirectLabel, \
	"The new name id for UI files that are redirected via CSK's plugin. (ie knuckles)"
	"\nLeave blank to use the original fighter's id, or if not using the CSS redirector"
	"\nThe number is the starting color (relative to the new entry). For batch redireciton, keep this at 0"
	"\nIf you are adding mods (ie Knuckles Alt #2), you'll want to set this to that alt's number (ie 2)"
	)


	redirectheader = Label(root, text="CSS Redirect", bd=1, relief=SUNKEN, anchor=N)
	redirectheader.pack(side = BOTTOM, fill=X)
	frame = Frame(root)
	frame.pack(side = BOTTOM,pady=5)

	prcEntry = Frame(root)
	prcEntry.pack(side = BOTTOM)
	root.labelPRC = Label(prcEntry,text="New Max Slots")
	root.labelPRC.pack(side = LEFT)
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

	root.comboPRC_ttp = CreateToolTip(root.labelPRC, \
	'Sets the new maximum slots on the Character Select Screen.'
	'\nAt least one mod per fighter will need a "ui/param/database/ui_chara_db.prcxml file. If this is blank, this file will not be included'
	'\nHaving multiple ui_chara_db.prcxml files for one fighter might have unwanted results.'
	'\nAlternatively, you can have one mod that has a "ui/param/database/ui_chara_db.prc" file that contains all changes for all fighters.'
	)

	root.shareCheckVariable = IntVar(value=0)
	if True:
		root.shareCheck = Checkbutton(root, text='Use share-to libraries',variable=root.shareCheckVariable, onvalue=1, offvalue=0)
		root.shareCheck.pack(side = BOTTOM)
		root.shareCheck_ttp = CreateToolTip(root.shareCheck, \
		'Force non-additional slots to use "share-to-added" and "share-to-vanilla" when creating a config'
		'\nThis will automatically be true for any additional slots')

	root.excludeCheckVariable = IntVar(value=1)
	root.excludeCheck = Checkbutton(root, text='Exclude Blank New Slots',variable=root.excludeCheckVariable, onvalue=1, offvalue=0)
	root.excludeCheck.pack(side = BOTTOM)

	root.excludeCheck_ttp = CreateToolTip(root.excludeCheck, \
	'Controls what happens when you leave a "New Slot" blank.'
	'\nIf True, will ignore any blank slot and not move them to the new folder'
	'\nIf False, will include any blank slot, setting it to whatever is its "Current Slot"')

	root.cloneCheckVariable = IntVar(value=1)
	root.cloneCheck = Checkbutton(root, text='Copy To New Folder',variable=root.cloneCheckVariable, onvalue=1, offvalue=0)
	root.cloneCheck.pack(side = BOTTOM)

	root.cloneCheck_ttp = CreateToolTip(root.cloneCheck, \
	'Creates a new folder called "[Mod name] [slots] when changing slots.'
	'\nIf False, this will overwrite the current folder when changing slots, not entirely recommended...')


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

def OnShareChange(*args):
	root.UnsavedChanges=True
	UpdateHeader()

def RefreshMainWindow():
	root.UnsavedChanges=False
	UpdateHeader()
	root.comboFighter['values'] = [f for f in root.fighters]
	#This automatically calls RefreshSlotWindow
	root.comboFighter.current(0)

	#Info about reslotting unique cases
	if (root.comboFighter['values'][0] in Climber):
		messagebox.showinfo(root.title(),"Popo and Nana will both be reslotted with the same parameters")
	if (root.comboFighter['values'][0] in Trainer):
		messagebox.showinfo(root.title(),"Trainer and their pokemon will all be reslotted with the same parameters")
	if (root.comboFighter['values'][0] in Aegis):
		messagebox.showinfo(root.title(),"Pyra, Mythra and Rex will all be reslotted with the same parameters")
	
def OnFighterChange(*args):
	root.currentFighter = root.comboFighter.get().lower()
	SetFighters(root.currentFighter)
	RefreshSlotWindow()

def GetAssumedShareSlot(source,fighter):
	altsLast2 = ["edge","szerosuit","littlemac","mario","metaknight","jack"]
	altsOdd = ["bayonetta","master","cloud","kamui","ike","shizue","demon",
	"link","packun","reflet","wario","wiifit",
	"ptrainer","ptrainer_low","pfushigisou","plizardon","pzenigame"]
	altsAll = ["koopajr","murabito","purin","pikachu","pichu","sonic"]
	if fighter == "brave" or fighter == "trail":
		return source % 4
	elif fighter == "pikmin" or fighter == "popo" or fighter == "nana":
		return 0 if (source<4) else 4
	elif fighter == "pacman":
		return 0 if (source==0 or source==7) else source
	elif fighter == "ridley":
		return 0 if (source==1 or source==7) else source
	elif fighter == "inkling" or fighter=="pickel":
		return source%2 if source<6 else source
	elif fighter == "shulk":
		return 0 if source<7 else 7
	elif fighter in altsLast2:
		return 0 if source<6 else source
	elif fighter in altsAll:
		return source
	elif fighter in altsOdd:
		return source % 2
	else:
		return 0

def GetLastTarget(currentSlot):
	if currentSlot in config["DEFAULT"]:
		targetSlotStr = config["DEFAULT"][currentSlot]
		if "c" in config["DEFAULT"][currentSlot]:
			return int(config["DEFAULT"][currentSlot].replace("+","").replace("c",""))+1
	return 0

def RefreshSlotWindow():
	for widget in root.frameCombos.winfo_children():
		widget.destroy()

	root.UIsources = []
	root.UItargets = []
	root.UIshares = []
	root.strTargets = {}
	root.strShares = {}

	reslotText = "normal" if (root.currentFighter != "all") else "disabled"
	root.reslotButton["state"]=reslotText

	if (root.currentFighter == "all"):
		return

	for i in range(root.maxSources):
		#only use the sources provided
		textSource = "c%02d" % i
		if (not textSource in root.slots) and (root.OnlyUseSlotsInMod):
			continue
		if (i>=8):
			textSource = "+"+textSource

		strSource = StringVar()
		strTarget = StringVar()


		comboEntry = Frame(root.frameCombos)
		comboEntry.pack()

		labelSource = Label(comboEntry,text=textSource,width = 6)
		labelSource.pack(side = LEFT)
		root.UIsources.append(labelSource)

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
		#comboTarget.current(0)
		comboTarget.current(GetLastTarget(textSource))

		strTarget.trace_add('write',OnTargetChange)
		comboTarget.pack(side = LEFT)
		root.UItargets.append(comboTarget)

		separater = Frame(comboEntry,width = 8)
		separater.pack(side = LEFT)

		root.strShares.update({textSource:StringVar(name="")})
		strShare= root.strShares[textSource]
		#Add possible combo select values
		comboShare = ttk.Combobox(comboEntry,textvar=strShare, width = 8)
		shares = []
		m=0
		#shares.append("")
		for m in range(8):
			textSlot = "c%02d" % m
			#add + to additional slots
			shares.append(textSlot)

		comboShare['values'] = shares
		comboShare.current(GetAssumedShareSlot(i%8,root.comboFighter.get().lower()))
		strShare.trace_add('write',OnShareChange)
		comboShare.pack(side = LEFT)
		root.UIshares.append(comboShare)

	configText = "Rewrite Config" if (os.path.isfile(root.searchDir + "/config.json")) else "Create Config"
	root.configButton.config(text=configText)


	root.minsize(250, 180+len(root.UItargets)*30)


def Reslot():
	RunReslotter(False)
def Reconfig():
	RunReslotter(True)

Climber = ["popo","nana"]
Trainer = ["ptrainer","ptrainer_low","pzenigame","pfushigisou","plizardon"]
Aegis = ["element","eflame","elight"]

def Foresight(onlyConfig):
	res = "yes"
	usesAdditional = False
	for i in range(len(root.UIsources)):
		targetText = root.UItargets[i].get()
		if ("+" in targetText) or (i>7 and onlyConfig):
			usesAdditional=True
	if usesAdditional:
		if (root.currentFighter == "kirby"):
			res = "Kirby can cause extremely long load times on the VS screen with additional slots"
		elif (root.currentFighter in Trainer):
			res = "Trainer might need their ptrainer_low model in the mod folder to use additional slots"
	if res != "yes":
		res = messagebox.askquestion(root.title(), res+"\nContinue with reslotting?")
	return res


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
		#print("Failed to create prcxml directory at "+prcLocation)
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
	if (root.currentFighter == "all"):
		ReconfigAll()
		return
	elif (Foresight(onlyConfig)!="yes"):
		return

	exclude = (root.excludeCheckVariable.get() and not onlyConfig)
	clone = (root.cloneCheckVariable.get() and not onlyConfig)

	if (exclude and not clone):
		res = messagebox.askquestion(root.title(), "If you want to use the same folder, but exclude all other alts,"
			"all mod files that are excluded will be deleted! Are you sure you want to do this?"
			)
		if res != 'yes':
			return

	sources=[""]*len(root.UIsources)
	targets=[""]*len(root.UItargets)
	shares=[""]*len(root.UIshares)
	usesAdditional=False

	targetName = ""
	knownTargets = 0
	#for each potential source, check if the UI exists for it. Then pair them together by source:target
	for i in range(len(root.UIsources)):
		sourceText = root.UIsources[i]["text"]
		sources[i] = sourceText.replace("+","")

		sharesText = root.UIshares[i].get()
		if ("same" in sharesText):
			sharesText = sourceText
		shares[i] = sharesText

		#get the cXX name of the target
		targetText = root.UItargets[i].get()

		#Update Config
		config.set("DEFAULT",sourceText,targetText)
		print("Config:"+sourceText+":"+targetText)

		#Replace it if doing reconfig
		if (onlyConfig):
			targetText = sourceText
		#Else If TargetText is empty, either append blank or append the same slot based on excluding
		elif (not "c" in targetText) and not onlyConfig:
			if (exclude):
				targets[i] = ""
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

	#Update config
	if (root.currentFighter != "all"):
		with open('config.ini', 'w+') as configfile:
			config.write(configfile)

	root.withdraw()
	print(targets)
	#set directory to clone everything to, keep it the same, or use a temp folder
	targetName = " ("+targetName[1:]
	if (onlyConfig):
		root.targetDir = root.searchDir
	else:
		root.targetDir = root.searchDir+targetName+")" if (clone) else root.searchDir+" (Temp)"

	#create target directory
	try:
		os.makedirs(root.targetDir)
	except:
		pass
	

	#Populate with more fighters for these unique cases
	fighters = [root.currentFighter]
	if (root.currentFighter in Climber):
		fighters= Climber
	if (root.currentFighter in Trainer):
		fighters= Trainer
	if (root.currentFighter in Aegis):
		fighters= Aegis

	SubCall(fighters,onlyConfig,sources,targets,shares,exclude,clone)

#This doesn't work atm
def ReconfigAll():
	res = messagebox.askquestion(root.title(), "This is experimental, this will also take an extremely long time based on the amount of"
		" added slots in your mod. Do you want to continue?"
		)
	if (res != "yes"):
		return

	root.targetDir = root.searchDir
	SubCall(root.fighters,True,[],[],[],False,False)


def RenameUI(targetFolder,fighter_name,newname):
	print("New CSS name:"+newname)
	startid = int(root.redirectStartVariable.get())
	folders = [targetFolder+"/ui/replace",targetFolder+"/ui/replace_patch"]
	for folder in folders:
		for (dirpath, dirnames, filenames) in os.walk(folder):
			newid = startid
			for filename in filenames:
				fighter_keys = [fighter_name]
				#Ice Climber / Aegis Stuff
				if (fighter_name=="popo" or fighter_name=="nana"):
					fighter_keys = ["ice_climber"]
				elif (fighter_name=="eflame"):
					fighter_keys = ["eflame_first","eflame_only"]
				elif (fighter_name=="elight"):
					fighter_keys = ["elight_first","elight_only"]

				for oldname in fighter_keys:
					file = os.path.join(dirpath,filename)
					newfilename = filename.replace("_"+oldname+"_","_"+newname+"_")
					costumeslot = newfilename.index(newname+"_")
					newfilename = newfilename[:costumeslot]+newname+"_"+"{:02d}".format(newid)+".bntx"
					newfile = os.path.join(dirpath.replace("/ui/replace_patch","/ui/replace"),newfilename)
					try:
						os.makedirs(dirpath.replace("/ui/replace_patch","/ui/replace"))
					except:
						pass
					os.rename(file,newfile)
				newid = newid + 1


def SubCall(fighters,onlyConfig,sources,targets,shares,exclude,clone):
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

	succeeded=False
	for fighter in fighters:
		if fighter == "all":
			continue
		print("Beginning operations for " + fighter)
		if (root.currentFighter == "all"):
			root.slots=[]
			modelFolder = root.searchDir+"/fighter/"+fighter+"/model"
			motionFolder = root.searchDir+"/fighter/"+fighter+"/motion"
			if (os.path.isdir(modelFolder)):
				for s in GetSlotsFromFolder(modelFolder):
					root.slots.append(s)
			elif (os.path.isdir(motionFolder)):
				for s in GetSlotsFromFolder(motionFolder):
					root.slots.append(s)
			print(str(len(root.slots)) +" slots found in "+fighter)
			root.UIsources = []
			sources=[]
			targets = []
			shares = []
			
			for s in root.slots:
				if s not in root.UIsources:
					root.UIsources.append(s)
					sources.append(s)
					targets.append(s)
					share = s
					sAsInt = int(s.strip("c"))
					if (sAsInt>7):
						share = "c0"+str(GetAssumedShareSlot(sAsInt% 8,fighter))
						print("Slot "+str(sAsInt)+" will share from "+share)
					shares.append(share)

		for i in range(len(root.UIsources)):
			source = sources[i]
			target = targets[i]
			share = shares[i]
			if (not root.shareCheckVariable.get()):
				if "c" in target:
					tAsInt = int(target.strip("c"))
					if (tAsInt<8):
						share = ""
			#print("Source:"+source+" Target:"+target+" Share: "+share)
			if (target == "" and exclude==True):
				continue
			outdirCall = "" if (onlyConfig) else root.targetDir
			subcall = ["reslotter.py",root.searchDir,root.hashes,fighter,source,target,share,outdirCall]

			if (onlyConfig):
				print("Writing config for "+fighter+"'s "+source+" slot")
			else:
				print("Changing "+fighter+"'s "+source+" mod to "+target+"...")
			
			try:
				reslotter.main(subcall[1],subcall[2],subcall[3],subcall[4],subcall[5],subcall[6],subcall[7])
				succeeded=True
			except IndexError:
				reslotter.usage()

	if succeeded:

		extras = ["info.toml","preview.webp"]
		if (not onlyConfig):
			for e in extras:
				eFile = root.searchDir + "/"+e
				if (os.path.isfile(eFile)):
					shutil.copy(eFile,root.targetDir+"/"+e)

			if (not clone):
				shutil.rmtree(root.searchDir, ignore_errors=True)
				os.rename(root.targetDir,root.searchDir)
				root.targetDir=root.searchDir

		if (root.currentFighter != "all"):
			CreatePRCXML(root.currentFighter,root.targetDir)
			newName = root.redirectEntryVariable.get()
			if newName != "":
				RenameUI(root.targetDir,fighter,newName)

		newConfigLocation = root.targetDir + '/config.json'
		with open(newConfigLocation, 'w+', encoding='utf-8') as f:
			json.dump(reslotter.resulting_config, f, ensure_ascii=False, indent=4)

		messagebox.showinfo(root.title(),"Finished!")
		webbrowser.open(root.targetDir)
	else:
		messagebox.showerror(root.title(),"Failed to reslot")

	root.deiconify()
	root.UnsavedChanges=False
	UpdateHeader()

def quit():
	with open('config.ini', 'w+') as configfile:
		config.write(configfile)
		
	root.destroy()
	sys.exit("user exited")

def main(args):
	Init(args)
	SetFighters()
	CreateMainWindow()


main(sys.argv)
root.mainloop()
