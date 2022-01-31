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