# Reticulator

Reticulator is a library for parsing Minecraft Bedrock Add-ons, and interacting with them programmatically. First you read the project into a virtual filesystem, which is represented by a nested list of classes. You can read and write to these data structures. When you are finished, you can save your changes back to the filesystem.

Reticulator is built as a wrapper around the 'dpath' library, which gives you a powerful interface for interacting with the raw json, if desired.

### Minimal Example

This small example shows you a minimal example of opening a project, making some changes, and then saving the results:

```py
import reticulator

# Open up a new Reticulator project. There are various ways to do this.
project = reticulator.Project('./path/to/bp', './path/to/rp')
bp = project.behavior_pack

# Step through the project in a comfortable manor, and adjust the 'health' component.
for entity in bp.entities:
	for component in entity.components:
		if component.id == "minecraft:health":
			print(f"Adjusted Health for {entity.identifier}.")
			component.set_jsonpath('value', 10)

# When you are finished, you can save your changes back to the filesystem
project.save()
```

# Documentation

## Project Structure

### Importing and Installing

Reticulator is available on `pip` package manager. In most cases, you're going to want to install using `pip install reticulator`. Once installed, you can import into your project however you find convenient. To keep the documentation concise, the documentation will assume you're imported the full namespace: 

```py
from reticulator import *
```

### Loading your Project

Reticulator is purpose built for reading and writing Bedrock add-ons. The bedrock wiki contains detailed information about the folder [layout of the folders](https://wiki.bedrock.dev/documentation/pack-structure.html). Reticulator can load projects matching this format.

To load a project with both an RP and a BP, you can use the `Project` class. A `Project` holds a reference to both packs, and allows classes in one side to be aware of the other. For example, an Entity has a definition file in both packs.

```py
project = Project('./path/to/bp', './path/to/rp')
bp = project.behavior_pack
rp = project.resource_pack
```

If you only have a single, stand-alone pack, you can open it directly using `BehaviorPack` or `ResourcePack`, which both inherit from `Pack`:

```py
bp = BehaviorPack('./path/to/bp')
```

### Saving your Project

When you make a change in a reticulator class, it won't be saved back to the filesystem by default. Rather, it will be held in-memory, in a 'virtual filesystem'. To convert this virtual filesystem back into real files, you need to `save` your project.

Here is an example of opening a project, changing the identifier of an entity, and then saving that entity back into the filesystem:

```py
bp = BehaviorPack('./path/to/bp')

entity = bp.get_entity('minecraft:snail')
entity.identifier = 'minecraft:sirlich'

bp.save()
```

The `save()` here will put the files into the packs `output_directory`. By default, that will be the folder where the project files were read from. In other words reticulator is optimized for reading files, and saving the changes back into the same location. This makes it perfect for [Regolith](https://bedrock-oss.github.io/regolith/).

If you want to change the `output_directory` you can do so from the `Pack`:

```py
bp = BehaviorPack('./path/to/bp')

entity = bp.get_entity('minecraft:snail')
entity.identifier = 'minecraft:sirlich'

bp.output_location = './path/to/save/to'
bp.save()
```

In the above example, you may notice that only the file containing `minecraft:sirlich` will be exported. That's because regolith is *lazy* and doesn't do more work than needed: only edited files are exported. Once again, regolith is optimized for destructive-writing into the same folder where the files were read.

To force Regolith to write every file it knows about, you must call save like this:

```py
bp.save(force=True)
```

## Interacting with the Class-Tree

Regolith is designed as a nested tree of classes, each class representing a 'part' of the add-on system which you may want to interact with. Here are a collection of small examples, showcasing the kind of read-calls that Reticulator supports:

Print warnings for miss-matched entities:

```py
project = Project('./path/to/bp', './path/to/rp')
rp = project.resource_pack

for entity in rp.entities:
	if entity.counterpart == None:
		print(f"WARNING: Entity {entity.identifier} has a resource pack definition, but no behavior pack definition!")
```

Ensure that models aren't too complex:

```py
rp = ResourcePack('./path/to/rp')

for model in entity.models:
	cube_count = 0
	for bone in model.bones:
		cube_count += len(bone.cubes)

	if cube_count > 200:
		print(f"Model {model.identifier} contains {cube_count} cubes, which is too many!")
```

## Raw JSON Access

### DPATH

The class-tree is pretty cool, but sometimes it's just a bit too much boilerplate. Regolith provides a user-friendly wrapper around [dpath](https://pypi.org/project/dpath/), which allows you to access and manipulate the json directly.

In a nutshell, dpath allows you to interact with json using a string-path. For example the path: `minecraft:entity/description/identifier` could be used to get the identifier of an entity. You can use `*` to stand in for a single 'layer' or `**` to stand in for an arbitrary number of layers. For example: `**/identifier` would match ANY key called 'identifier' in the entity json.

The following methods are available on any json based class, but I will use an 'entity' to illustrate:
 - Get a path: `data = entity.get_jsonpath('path/to/field')`
 - Set a path: `entity.set_jsonpath('path/to/field', 'new value')`
 - Delete a path: `entity.delete_jsonpath('path/to/field')`
 - Delete a path and return the result: `data = entity.pop_jsonpath('path/to/field')`
 - Appends a value to a path (array expected): `entity.append_jsonpath('path/to/array', 10)`

And then here is a feature complete example, which shows deleting a specific component from all entities. `**` is a wildcard for matching the component wherever it may be found -in components, or component groups:

```py
bp = BehaviorPack('bp')

for entity in bp.entities:
    entity.delete_jsonpath('**/minecraft:minecraft:behavior.melee_attack')

bp.save()
```

### True JSON Access

If the DPATH methods don't please you, you're also welcome to interact with the json data directly, although this is discouraged. To do so, just access the `data` field on any json based class. For example:

```py
bp = BehaviorPack('./path/to/bp')
entity = bp.get_entity('minecraft:snail')

entity.data['minecraft:entity']['description']['identifier'] == 'minecraft:sirlich'
```

I hope you can see why this isn't my favorite way to use Regolith. 

## Language Files

Regolith offers strong support for language file editing. Here are a few examples:


Printing out data:

```py
rp = ResourcePack('./path/to/rp')
for language_file in rp.language_files:
	for translation in language_files:
		print(f"Translation: key='{translation.key}', value='{translation.value}')
```

Auto-translating entity names with place-holder:

```py
rp = ResourcePack('./path/to/rp')
en_us = rp.get_language_file('texts/en_US')

for entity in rp.entities:
	en_us.add_translation(Translation(f"item.spawn_egg.entity.{entity.identifier}.name", f"PLACEHOLDER NAME: {entity.identifier}", "# TODO"))

rp.save()
```

## Functions

We support functions, I just didn't document it yet
