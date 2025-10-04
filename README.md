The .py files run in Blender's scripting environment. Adjust the path to in the script and run it.
Select a model before running .tmm exporter.
You can select an existing model/armature before you run the .tma script and it will put the animation there.

The .bt files are 010 editor templates. ~~There's a few things that aren't figured out, for example, the very end of building .tmm files is a weird side-on depth texture.~~ Irrelevent now since the file format specs are released with the game's modding documentation.

~~The major thing that isn't figured out is the normal/tangent/bitangents for the .tmm.data file. It's clearly the 6 bytes, but no idea how they are decoded.
This means the .tmm exporter script isn't working and your model *will* look pretty bad in game, like the lighting is reflecting off it in strange ways.~~ File format specs are released so and I've updated the importer. Exporter will take a little more time since I need to do some math.
