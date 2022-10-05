# 0.0.14-beta
 - Added EntityFileRP.textures
 - EntityFileRP.counterpart now throws AssetNotFoundException in instead of returning None
 - Added InvalidJsonError exception
 - Added EntityFileBP.counterpart
 - Added support for 'terrain_texture.json'
 - Added support for 'item_texture.json'
 - Added support for 'flipbook_textures.json
 - Added support for 'biomes_client.json'
 - Added support for 'blocks.json'
 - get_data_at no longer takes '/*' at the end
 - Added special handling for '**' to query the root of a json, in get_data_at
 - Fixed entity component/component group handling
 - Added get_loot_table
 - All file asset getters are once again relative to the root of the pack
 - Fixed bp.get_loot_table
 - Added ItemFileRP.get_component
 - Added BlockFileBP.get_component
 - Added ItemFileBP.get_component
 - Simple data types (string, float, int) now get marked as dirty, when set in-whole
 - Setting 'JsonResource.data' to a new array/dict will properly convert to notify structure
 - JsonSubResource.id now serializes into json_path, and both properties dirty the asset for saving
 - Enabled the possibility to rename or move an asset via either ID or jsonpath
 - Rewrote how textures/models/animations are handled inside of the RP Entity file.

# 0.0.15-beta
 - Removed 'must_exists' and 'ensure_exists' from all jsonpath methods
 - Fix the setter for TexturePair texture_path
 - Added EntityRP.materials
 - Added ResourcePack.materials
 - Added ResourcePack.material_files
 - Added ResourcePack.get_material_file
 - Added ResourcePack.get_material

# 0.0.16-beta
 - Added ModelFile.format_version
 - Added Bone.name
 - Added Model.get_bone
 - Fixed inconsistent path comparison for rp.get_language_file
 - File deletion now properly removes the file from disk
 - Added LanguageFile.get_translation
 - Added Project.set_save_location
 - Added Pack (either RP or BP).set_save_location
 - Added new StandAloneTextureFile type for both `item_texture` and `terrain_texture`
   - texture_definitions
   - add_texture_definition
   - get_texture_definition
   - texture_definition type contains `shortname` and `textures`
 - Added ResourcePack.fogs
 - Added ResourcePack.get_fog
 - FogFile resource:
  - identifier
  - format version
  - distance_components
  - volumetric_density_components
  - volumetric_media_coefficients
  - Getters for all component types

# 0.0.17-beta
 - Replaced EntityFileBP.create_component_group with EntityFileBP.add_component_group
 - Replaced EntityFileBP.create_component with EntityFileBP.add_component
 - Replaced ComponentGroup.create_component with ComponentGroup.add_component
 - Rewrote deletion logic, including support for list-deletes
 - Added context manager for resources
 - Pack saving io internal restructuring:
    - Rename `Project.set_save_locations` to `Project.set_output_directory`
    - Remove `Pack.set_save_locations` (just call `Pack.output_directory = x`)
    - Rename `input_path` to `input_directory`
    - Rename `output_path` to `output_directory`
 - Added FormatVersion class

# 0.0.18-beta
 - Unknown

# 0.1.0-beta
 - Rewrote much of the codebase to use meta-programming
 - Added many missing get/set/delete methods

# 0.1.1-beta
 - Getters now return 'None' instead of throwing an error.
 - Fixed intellisense for resource and sub-resource definitions
 - Added `ItemEventBP` + methods in `ItemFileBP`
 - Allowed JsonFileResources to function when they are created free of a pack

# 0.1.2-beta
 - Introduced a new @SingleResourceDefinition decorator
 - Fixed intellisense for @identifier, @format_version, and @ClassProperty
 - Child Getters now return 'None' instead of throwing an error
 - Streamlined the 'Triple' system, and removed 'exists()', since you can just check for None
 - Switched all 'adders' to use kwargs