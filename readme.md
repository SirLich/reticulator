# Reticulator

Reticulator is a pack-access library for Minecraft Bedrock Addons. Load in a project, and the json internals will be represented as a tree structure of python classes. Reticulator can be used non-destructively for reading project files, although files can also be edited and saved to disk. This can occur destructively (overwriting the read project), or non-destructively (exporting into secondary location).

## Example

```py
def minify_model_files(project):
    rp = project.resource_pack

    # Set output location. This would normally be injecting into `development_*_packs`.
    rp.set_output_location("./test/out/rp")

    # Create new model file, with minimal starting json
    combined = rp.create_model_file("combined.json", data={"format_version":"1.12.0","minecraft:geometry":[]})

    # Loop over all models, and copy json into new model file
    for model in rp.models:
        combined.data["minecraft:geometry"].append(model.data)

    # Mark old files for deletion. They will be remove from disk when saving.
    for model_file in rp.model_files:
        if model_file.file_name != "combined.json":
            model_file.delete()

    # Write to disk. Since we set output location, this isn't destructive to the original project.
    project.save(force=True)

```