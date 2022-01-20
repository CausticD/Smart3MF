import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET

# Running the exe or the com file directly is fine, but I could not get the -D param to work :( without resorting to a
# batch file, so going with it.

#openscadexec = '"C:\Program Files\OpenSCAD\openscad.com"'	# Works fine except when wanting the -D param!
openscadexec = "openscad.bat"
openscadexec2 = "openscad2.bat"								# Used for when we also have a -D param

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
	
	for object in resources:
		object.set('id', newid)
		object.set('name', newname)

	return resources[0]

def WriteCombinedFile(file, newobjects):
	print(file)
	my_namespaces = ReadNamespaces(file)
	
	ET.register_namespace('', my_namespaces[''])

	# Read file and save the <object>
	base = ET.ElementTree()
	base.parse(file)
	modelroot = base.getroot()
	resources = modelroot.find('{'+my_namespaces['']+'}'+'resources') # Passing in my_namespaces as the second param doesn't help

	print(newobjects)

	for newobj in newobjects:
		resources.insert(len(resources), newobj)		# Insert at the end
	
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
	print('Base', key, value, stepfileout, input_scad)
	ExportStep(key, value, stepfileout, input_scad)
	print(str(count), base.find('name').text)
	
	# Now to extract all files to an empty temp directory.
	
	print(stepfileout, folder)
	
	with zipfile.ZipFile(stepfileout, 'r') as myzip:
		myzip.extractall(path=folder)
	
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
			with myzip.open('3D/3dmodel.model') as myfile:
				newobj = ExtractObject(myfile, str(count), step.find('name').text)
				count += 1
				models.append(newobj)
		
	print('Models', len(models))
	
	WriteCombinedFile(folder+"/3D/3dmodel.model", models)
	
def GenThumbnail(root, dest):
	print('Thumb', dest)
	imgsize = thumbnailroot.find('imgsize').text
	camera = thumbnailroot.find('camera').text
	print('Thumb', imgsize, camera)
	
	cmd = openscadexec + " -o " + dest + 'thumbnail.png' + " --imgsize "+imgsize+" --camera "+camera+" --viewall " + input_scad
	print(cmd)
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	os.system(cmd)

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
		ProcessSteps(steps, tempfolder)
		
	# Thumbnail
	thumbnailroot = steps.find('addthumbnail')

	if thumbnailroot:
		GenThumbnail(thumbnailroot, tempfolder+'/Metadata/')

	# Everything should be ready, so zip up the temp folder.
	ZipFolder(output_3mf, tempfolder)