# Smart3MF
OpenSCAD exporter and 3MF file manipulator

## Go from this:
![Quick render in OpenSCAD](/OpenSCAD.PNG)

## To this:
![Screenshot inside PrusaSlicer with a single object showing exposed infill](/Prusa1.PNG)
![Screenshot inside PrusaSlicer showing objects and settings](/Prusa2.PNG)

Why was this created?
1) I wanted a way to export multiple models from a single OpenSCAD file and combine them into a single 3MF file. 
2) I wanted to be able to override settings to specific models, set things as supports etc.
3) I wanted to easily add thumbnails to my 3mf files.

Whats the workflow?
1) Create the geometry in OpenSCAD.
2) Add the markup to an XML file.
3) Export by running the Smart3MF python scrypt.

Limitations:
- Very limited testing, and only on Windows.
- Currently heavily linked to OpenSCAD to 3MF.
- Focused on Cura, but metadata tags are set as is to allow some flexibility.
