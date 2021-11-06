Reticulator
===========

Reticulator is a pack-access library for Minecraft Bedrock Addons.
Reticulator functions by exposing json files as a nested tree of python
classes. This structure allows you to interact with an addon as if it
was an API.

Class: Project
--------------

A ``Project`` generally just acts as a wrapper around a
``ResourcePack``, and ``BehaviorPack``. You can create a ``Project``
like so:

.. code:: py

    project = Project('./path/to/bp', './path/to/rp')

Class: Resource Pack and BehaviorPack
-------------------------------------

All Reticulator file-classes can either be accessed from the
``BehaviorPack`` or the ``ResourcePack``. They are the real "base class"
in Reticulator, and can function independently of a ``Project``.

.. code:: py

    bp = BehaviorPack('./path/to/bp')
    rp = BehaviorPack('./path/to/rp')

    # Or get from a Project:
    project = Project('./path/to/bp', './path/to/rp')
    bp = project.behavior_pack
    rp = project.resource_pack

A pack can be directed to export into a specific location (instead of
exporting into itself, and potentially overwriting files):

.. code:: py

    bp = project.behavior_pack
    bp.set_output_location('./some/path')

Class: JsonFile
---------------

The ``JsonFile`` class is a parent to all json files. That means that
every "file" you interact with in Reticulator, such as ``EntityFileBP``,
or ``AnimationControllerFileRP`` will have access to the attributes and
methods defined here:

This code snippet shows some of the surface area of this class:

.. code:: py

    bp = BehaviorPack('./path/to/bp')

    # EntityFileBP is a child of JsonFile
    zombie = bp.get_entity('minecraft:zombie')

    print(zombie.file_path) # The filepath, local to the pack root
    print(zombie.file_name) # The leaf-name of the file
    print(zombie) # Pretty prints the files json, with proper indenting

    # You can reach upwards in the tree if needed
    zombie.pack.project.resource_pack

    # The data of the file can always be accessed with .data
    print(zombie.data) 

    # We can edit fields here manually
    zombie.data['format_version'] = '1.16.100'

    # We can save our work in a few ways
    zombie.save() # Saves, but only writes to disk if edits were made
    zombie.save(force=True) # Forces the file to dump to disk, regardless of state
    zombie.pack.save() # Saves every file in the pack

Class: SubResource
------------------

The ``SubResource`` class is a lot like a ``JsonResource``, except
instead of owning an entire json file, it only owns a snippet of one.
Everything that you access from a ``JsonResource`` is generally a
``SubResource``. For example ``Components`` or ``Events`` are a
``SubResource``.

The idea is that ``SubResource``'s will own a section of json, allowing
you to interact with that json easily, without dealing with complex
json-paths to reach that content.

.. code:: py

    zombie = bp.get_entity('minecraft:zombie')
    component = zombie.get_component('minecraft:scale')

    # We can edit this component easily without knowing where in the file its located
    component.data['value'] = 10

    # The tree can be accessed via parent
    component.parent.identifier = 'minecraft:zombie_big'

    # SubResources can be saved, but this save will only reach the parent json-file, it won't actually save to disk.
    # When a JsonResource is saved, it will save all SubResources before saving, so this method can generally be left unused.
    component.save()

Access and Attributes
---------------------

Reticulator is built out of classes that extend either ``JsonResource``
or ``SubResource``. These classes are packed full of accessors,
attributes, and creators. This allows you to effortlessly create and
query your addon.

.. code:: py

    bp = BehaviorPack('./path/to/bp')
    rp = ResourcePack('./path/to/rp')

    # Loop over structures easily, and walk up the tree as needed
    for entity in bp:
        for component in entity:
            if component.id == 'minecraft:scale':
                if component.data['value] > 2:
                    print(f"Entity {component.entity.identifier} located at {component.entity.file_path} is too large!")

    # Fetch assets by name directly
    dino_model = rp.get_model('reticulator:dino')

    # Gain valuable diagnostic information about your files
    print(len(dino_model.bones))

    # Create assets in-place
    model_file = rp.get_model_file('lots_of_snakes.json')
    model_file.create_model('rattlesnake', data={...})

Examples
--------

Combining Packs together
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: py

    def minify_model_files(rp):
        # Create new model file, with minimal starting json
        combined = rp.create_model_file("combined.json", data={"format_version":"1.12.0","minecraft:geometry":[]})

        # Loop over all models, and copy json into new model file
        for model in rp.models:
            combined.data["minecraft:geometry"].append(model.data)

        # Mark old files for deletion. They will be remove from disk when saving.
        for model_file in rp.model_files:
            if model_file.file_name != "combined.json":
                model_file.delete()

        # Write to disk.
        project.save()

Fetching every Family name from a Behavior Pack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: py

    from reticulator.reticulator import *
        
    def main():
        bp = BehaviorPack("...")

        gathered_components = []
        families = set()

        # Gather all components, also from groups
        for entity in bp.entities:
            gathered_components.extend(entity.components)
            
            for group in entity.component_groups:
                for component in group.components:
                    gathered_components.append(component)

        
        for component in gathered_components:
            if isinstance(component.data, dict):
                families.update(component.data.get('family', []))

        print(families)
    main()

Clear an Entity
~~~~~~~~~~~~~~~

.. code:: py

    def clear_entity(entity: EntityFileBP):
        """Removes groups, components, and events from an entity."""
        for component in entity.components:
            component.delete()

        for component_group in entity.component_groups:
            component_group.delete()

        for event in entity.events:
            event.delete()

