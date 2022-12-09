# Reticulator

Reticulator is a library for parsing Minecraft Bedrock Add-ons, and interacting with them programmatically. This is possible by reading the project into a virtual filesystem, allowing you to interact with the addon via a nested tree of classes. When you are finished, you can save your changes back to the filesystem.

Reticulator is built 

## Small Example

This small example shows you a minimal example of opening a project, making some changes, and then saving the results.


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
