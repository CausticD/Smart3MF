import os
import shutil
import zipfile
import tempfile
import argparse
import xml.etree.ElementTree as ET

# Running the exe or the com file directly is fine, but I could not get the -D param to work :( without resorting to a
# batch file, so going with it.

# Thoughts:
# - I wanted a way to add a filament change. Cura does save this in a 3MF if you use the export project option, which saves a 3MF
#   with loads of extra settings. If you look in the '\Cura\Ender-3\Ender-3Pro\Ender-3-3S.global.cfg' is does list the active
#   post processing scripts, one of which can be a 'Filament change at layer'. So, use one such 3MF file as the base.

#openscadexec = '"C:\Program Files\OpenSCAD\openscad.com"'	# Works fine except when wanting the -D param!
openscadexec = "openscad.bat"
openscadexec2 = "openscad2.bat"								# Used for when we also have a -D param

hardcoded_modelpath = "3D/3dmodel.model"
hardcoded_relsfile = '_rels/.rels'
hardcoded_metadatathumb = '/Metadata/thumbnail.png'

def GetSCADInputFiles(scad_tag):
	input_scad = scad_tag.get('file')

	# Check to see if we use the params and presets file and options.

	if scad_tag.get('params') != None:
		input_scad = "-p " + scad_tag.get('params') + " " + input_scad
		
	if scad_tag.get('preset') != None:
		input_scad = "-P " + scad_tag.get('preset') + " " + input_scad
		
	return input_scad
	
def GetOutputFiles(configroot):
	return configroot.find('export').get('file')
	
def ReadNamespaces(file):
	# https://stackoverflow.com/questions/14853243/parsing-xml-with-namespace-in-python-via-elementtree
	return dict([
		node for _, node in ET.iterparse(
			file, events=['start-ns']
		)
	])

def ExtractObject(file, newid, newname):
	my_namespaces = ReadNamespaces(file)
		
	file.seek(0)		# Vital if this is a stream from a file in a zip.
	
	modelroot = ET.parse(file).getroot()
	resources = modelroot.find('{'+my_namespaces['']+'}'+'resources') # Passing in my_namespaces as the second param doesn't help
	
	# Set the new id number and name. TODO: Check if there is more than one. That would cause issues!
	
	for object in resources:
		object.set('id', str(newid))
		object.set('name', newname)

	return resources[0]
	
def AddMetaDataGroup(object, addmodeltag):
	mdgtag = addmodeltag.find('metadatagroup')		# This is the one from the config xml file.

	dest = object.find('{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'+'metadatagroup')

	print(object.tag, object.attrib)

	for child in object:
		print(child.tag)

	if dest is not None:
		print(mdgtag, dest)
	
	if mdgtag:
		object.insert(0, mdgtag)

def WriteCombinedFile(steps, file, newobjects):
	basetag = steps.find('base')
	my_namespaces = ReadNamespaces(file)
	
	ET.register_namespace('', my_namespaces[''])

	# Read the primary file.
	base = ET.ElementTree()
	base.parse(file)
	modelroot = base.getroot()
	resources = modelroot.find('{'+my_namespaces['']+'}'+'resources') # Passing in my_namespaces as the second param doesn't help
	
	# Add any meta data
	AddMetaDataGroup(resources[0], basetag)

	for newobj in newobjects:
		idx = len(resources)
		resources.insert(idx, newobj)		# Insert at the end
		
	# Update the <build> tag contents at the end of the 3dmodel.model file. 
	
	build = modelroot.find('{'+my_namespaces['']+'}'+'build') # Passing in my_namespaces as the second param doesn't help
	
	for extobj in build:
		#print('1=====>', extobj.get('objectid'), extobj.get('{'+'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'+'}'+'UUID'))
		extobj.set("transform", basetag.find('transform').text)

	addmodels = steps.findall('model')
	index = 0
	
	for newobj in newobjects:
		newnode = ET.Element('item')
		newnode.set("objectid", newobj.get('id'))
		trans = addmodels[index].find('transform').text
		newnode.set("transform", trans)
		#print('2=====>', newobj.get('id'), newobj.get('{'+'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'+'}'+'UUID'))
		
		build.insert(len(build), newnode)		# Insert at the end
		
		index += 1

	# Done. Write it out.
	
	base.write(file, encoding='UTF-8', xml_declaration=True)

def ExportStep(key, value, stepfileout, input_scad):
	cmd = openscadexec2 + " " + key + " " + value + " -o " + stepfileout + " " + input_scad
	os.system(cmd)

def ProcessStep(step, folder, models, extractall):
	scad_tag = step.find('scad')
	tmf_tag = step.find('threemf')

	if scad_tag != None:
		key = scad_tag.get('key')
		value = scad_tag.get('value')
		stepfileout = key + "_" + value + ".3mf"			# Temp file
		input = GetSCADInputFiles(scad_tag)
		ExportStep(key, value, stepfileout, input)
	elif tmf_tag != None:
		stepfileout = tmf_tag.get('file')
		
	if extractall:
		# Now to extract all files to an empty temp directory.

		with zipfile.ZipFile(stepfileout, 'r') as myzip:
			myzip.extractall(path=folder)
	
		os.remove(stepfileout)
	else:
		# Extract just the one file from the 3mf aka a zip file.
		
		with zipfile.ZipFile(stepfileout, 'r') as myzip:
			with myzip.open(hardcoded_modelpath) as myfile:
				newobj = ExtractObject(myfile, len(models)+2, step.find('name').text)
				AddMetaDataGroup(newobj, step)
				models.append(newobj)
				
		# Delete the 3mf file as we have got what we need.
		
		if scad_tag != None:
			os.remove(stepfileout)

		return 

def ProcessSteps(steps, folder):
	models = []
	count = 1
	
	# Export the base model first.
	
	base = steps.find('base')

	ProcessStep(base, folder, models, True)

	count += 1
	
	# Now export all the models to add to the base one.
	
	for step in steps.findall('model'):
		ProcessStep(step, folder, models, False)
		count += 1
	
	return models
	
def GenThumbnailFromSCAD(root, dest):
	imgsize = root.get('imgsize')
	camera = root.get('camera')
	
	cmd = openscadexec + " -o " + dest + 'thumbnail.png' + " --imgsize "+imgsize+" --camera "+camera+" --viewall " + GetSCADInputFiles(root)
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	os.system(cmd)

def CopyThumbnail(root, dest):
	filename = root.get('file')

	os.makedirs(os.path.dirname(dest), exist_ok=True)

	shutil.copyfile(filename, dest + 'thumbnail.png')

def UpdateRelsFile(file):
	# Check the existing rels file. This just lists the type of files found inside the 3mf. Basically,
	# a .model file and possibly now a png/jpg for the thumbnail.

	found = False
	
	ET.register_namespace('', 'http://schemas.openxmlformats.org/package/2006/relationships')
	
	base = ET.ElementTree()
	base.parse(file)
	root = base.getroot()
	
	for child in root:
		target = child.get('Target')
		if target == hardcoded_metadatathumb:
			found = True
			
	# If the rels file doesn't have the line mentioning the thumbnail, add the line and overwrite.
	
	if not found:
		newnode = ET.Element('Relationship')
		newnode.set("Target", hardcoded_metadatathumb)
		newnode.set("Id","rel-2")			# No idea what this is for.
		newnode.set("Type","http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail")
		
		root.insert(len(root), newnode)		# Insert at the end
		base.write(file, encoding='UTF-8', xml_declaration=True)			# Might be something I can do here with the default_namespace param

def ZipFolder(targetfile, sourcefolder):
	with zipfile.ZipFile(targetfile, 'w') as zipObj:
		for folderName, subfolders, filenames in os.walk(sourcefolder):
			for filename in filenames:
				filePath = os.path.join(folderName, filename)
				destpath = filePath[len(sourcefolder):]
				zipObj.write(filePath, destpath, compress_type=zipfile.ZIP_DEFLATED)
	
	print('Output:', targetfile)

######
# MAIN
######

parser = argparse.ArgumentParser(description='3MF file manipulator')
parser.add_argument('settingsxml', help='Your settings xml file')
args = parser.parse_args()

# Run the OpenSCAD executable with the version param. Should spit out a single line like 'OpenSCAD version 2021.01' to
# check that the path is correct and abort straight away if not found. 

ret = os.system(openscadexec + " -v")
if ret != 0:
	print('Error running OpenSCAD. Please set path in this python script first.')
	quit()
	
# Load the config XML file and get essential info from that.

configroot = ET.parse(args.settingsxml).getroot()

# Lets get the input and output files.

output_3mf = GetOutputFiles(configroot)

# Check for a multi-stage output system, which is basically the reason to use this system.

with tempfile.TemporaryDirectory() as tempfolder:
	steps = configroot.find('export')

	if not steps:
		print('Config file error. No export steps')
		quit()

	models = ProcessSteps(steps, tempfolder)
	WriteCombinedFile(steps, tempfolder+"/"+hardcoded_modelpath, models)
		
	# Thumbnail (Optional). If present, two options, either generate one using SCAD, or
	# just use one provided as is.

	thumbnailroot = steps.find('thumbnail')

	if thumbnailroot:
		scad_tag = thumbnailroot.find('scad')		# Generate thumbnail from SCAD fast render.
		image_tag = thumbnailroot.find('image')		# Image file provided. Use that.

		if scad_tag != None:
			GenThumbnailFromSCAD(scad_tag, tempfolder+'/Metadata/')
		elif image_tag != None:
			CopyThumbnail(image_tag, tempfolder+'/Metadata/')
		
		UpdateRelsFile(tempfolder+'/'+hardcoded_relsfile)

	# Everything should be ready, so zip up the temp folder.
	ZipFolder(output_3mf, tempfolder)