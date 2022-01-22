# Smart3MF
3MF file manipulator

Why was this created?
1) I wanted a way to export multiple models from a single OpenSCAD file and combine them into a single 3MF file. 
2) I wanted to be able to override settings to specific models, set things as supports etc.

Whats the workflow?
1) Create the geometry in OpenSCAD.
2) Add the markup to an XML file.
3) Export by running the Smart3MF python scrypt.
