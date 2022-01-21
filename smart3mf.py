import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET

# Running the exe or the com file directly is fine, but I could not get the -D param to work :( without resorting to a
# batch file, so going with it.

#openscadexec = '"C:\Program Files\OpenSCAD\openscad.com"'	# Works fine except when wanting the -D param!
openscadexec = "openscad.bat"
openscadexec2 = "openscad2.bat"								# Used for when we also have a -D param

hardcoded_modelpath = "3D/3dmodel.model"
hardcoded_relsfile = '_rels/.rels'
hardcoded_metadatathumb = '/Metadata/thumbnail.png'

def GetInputFiles(configroot):
	sourceroot = configroot.find('source')
	input_scad = sourceroot.find('scad').text

	# Check to see if we use the params and presets file and options.

	if sourceroot.find('params') != None:
		input_scad = "-p " + sourceroot.find('params').text + " " + input_scad
		
	if sourceroot.find('preset') != None:
		input_scad = "-P " + sourceroot.find('preset').text + " " + input_scad
		
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
		object.set('id', newid)
		object.set('name', newname)

	return resources[0]
	
def AddMetaDataGroup(object, addmodeltag):
	mdgtag = addmodeltag.find('metadatagroup')
	
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
		resources.insert(len(resources), newobj)		# Insert at the end
		
	# Update the <build> tag contents.
	
	build = modelroot.find('{'+my_namespaces['']+'}'+'build') # Passing in my_namespaces as the second param doesn't help
	
	
	for extobj in build:
		#print('1=====>', extobj.get('id'), extobj.get('{'+'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'+'}'+'UUID'))
		extobj.set("transform", basetag.find('transform').text)

	addmodels = steps.findall('addmodel')
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
	ret = os.system(cmd)

def ProcessSteps(steps, folder):
	models = []
	count = 1
	
	# Export the base model first.
	
	base = steps.find('base')
	
	key = base.find('cmdparam').get('key')
	value = base.find('cmdparam').get('value')
	stepfileout = key + "_" + value + ".3mf"
	ExportStep(key, value, stepfileout, input_scad)
	
	# Now to extract all files to an empty temp directory.
	
	with zipfile.ZipFile(stepfileout, 'r') as myzip:
		myzip.extractall(path=folder)
	
	os.remove(stepfileout)
	
	count += 1
	
	# Now export all the models to add to the base one.
	
	for step in steps.findall('addmodel'):
		key = step.find('cmdparam').get('key')
		value = step.find('cmdparam').get('value')
		stepfileout = key + "_" + value + ".3mf"
		print('Adding', key, value, stepfileout, input_scad)
		ExportStep(key, value, stepfileout, input_scad)
		
		# We now have a 3mf aka a zip file. We need to extract that.
		
		with zipfile.ZipFile(stepfileout, 'r') as myzip:
			with myzip.open(hardcoded_modelpath) as myfile:
				newobj = ExtractObject(myfile, str(count), step.find('name').text)
				AddMetaDataGroup(newobj, step)
				count += 1
				models.append(newobj)
				
		# Delete the 3mf file as we have got what we need.
		
		os.remove(stepfileout)
	
	return models
	
def GenThumbnail(root, dest):
	print('Thumb', dest)
	imgsize = thumbnailroot.find('imgsize').text
	camera = thumbnailroot.find('camera').text
	
	cmd = openscadexec + " -o " + dest + 'thumbnail.png' + " --imgsize "+imgsize+" --camera "+camera+" --viewall " + input_scad
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	os.system(cmd)

def UpdateRelsFile(file):
	# Check the existing rels file
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

# Run the OpenSCAD executable with the version param. Should spit out a single line like 'OpenSCAD version 2021.01' to
# check that the path is correct and abort straight away if not found. 

ret = os.system(openscadexec + " -v")
if ret != 0:
	print('Error running OpenSCAD. Please set path in this python script first.')
	quit()
	
# Load the config XML file and get essential info from that.

configroot = ET.parse("config.xml").getroot()

# Lets get the input and output files.

input_scad = GetInputFiles(configroot)
output_3mf = GetOutputFiles(configroot)

# Check for a multi-stage output system, which is basically the reason to use this system.

with tempfile.TemporaryDirectory() as tempfolder:
	steps = configroot.find('export')

	if steps:
		models = ProcessSteps(steps, tempfolder)
		WriteCombinedFile(steps, tempfolder+"/"+hardcoded_modelpath, models)
		
	# Thumbnail
	thumbnailroot = steps.find('addthumbnail')

	if thumbnailroot:
		GenThumbnail(thumbnailroot, tempfolder+'/Metadata/')
		UpdateRelsFile(tempfolder+'/'+hardcoded_relsfile)

	# Everything should be ready, so zip up the temp folder.
	ZipFolder(output_3mf, tempfolder)