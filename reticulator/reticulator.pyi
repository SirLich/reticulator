from __future__ import annotations
from core import *
from typing import Tuple

def ImplementFormatVersion(jsonpath: str = "format_version"):
    """
    Class Decorator which inserts a 'format_version' property, with proper
    semantics.
    """
    def inner_format_version(cls):
        def format_version(self) -> FormatVersion: ...
        def format_version(self, format_version): ...
def ImplementIdentifier(jsonpath: str):
    """
    Class Decorator, which injects handling for accessing 'identifier'.
    :param jsonpath: The jsonpath where the identifier can be located.
    """
    def inner(cls):
        def identifier(self) -> str: ...
        def identifier(self, identifier): ...
class Pack():
    """
    Pack is a parent class that contains the shared functionality between the
    resource pack and the behavior pack.
    """
    def __init__(self, input_directory: str, project : Project = None): ...
    def project(self) -> Project:
        """
        Get the project that this pack is part of. May be None.
        """
    def save(self, force=False):
        """
        Saves every child resource.
        """
    def register_resource(self, resource: Resource) -> None:
        """
        Register a child resource to this pack. These resources will be saved
        during save.
        """
    def get_language_file(self, filepath:str) -> LanguageFile:
        """
        Gets a specific language file, based on the name of the language file.
        For example, 'texts/en_GB.lang'
        """
    def language_files(self) -> list[LanguageFile]:
        """
        Returns a list of LanguageFiles, as read from 'texts/*'
        """
class Project():
    """
    Project is a class which represents an entire 'addon', via references to a 
    ResourcePack and BehaviorPack, along with some helper methods.
    """
    def __init__(self, behavior_path: str, resource_path: str) -> Project: ...
    def set_output_directory(self, save_location: str) -> None:
        """
        Sets the save location of the RP and the BP, based on the folder
        name from their input path.

        In other words, pass in a folder where you want both the RP and the BP 
        to be saved.

        If you need finer control, set the `output_directory` on both the RP
        and the BP individually.
        """
    def get_packs(self) -> Tuple[behavior_pack, resource_pack]:
        """
        Returns Behavior Pack followed by ResourcePack.
        Useful for quickly defining rp and bp:
        rp, bp = Project("...").get_packs()
        """
    def resource_pack(self) -> ResourcePack:
        """
        The resource pack of the project.
        """
    def behavior_pack(self) -> BehaviorPack:
        """
        The behavior pack of the project.
        """
    def save(self, force=False):
        """
        Saves both packs.
        """
class LanguageFile(FileResource):
    """
    A LanguageFile is a language file, such as 'en_US.lang', and is made
    up of many Translations.
    """
    def __init__(self, filepath: str = None, pack: Pack = None) -> None: ...
    def get_translation(self, key: str) -> Translation:
        """
        Whether the language file contains the specified key.
        """
    def contains_translation(self, key: str) -> bool:
        """
        Whether the language file contains the specified key.
        """
    def delete_translation(self, key: str) -> None:
        """
        Deletes a translation based on key, if it exists.
        """
    def add_translation(self, translation: Translation, overwrite: bool = True) -> bool:
        """
        Adds a new translation key. Overwrites by default.
        """
    def _save(self): ...
    def translations(self) -> list[Translation]: ...
class Translation():
    """
    Dataclass for a translation. Many translations together make up a
    TranslationFile.
    """
    def __init__(self, key: str, value: str, comment: str = "") -> None: ...
class FormatVersion():
    def __init__(self, version) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other): ...
    def __gt__(self, other): ...
class AnimationControllerBP(JsonSubResource): ...
class AnimationControllerFileBP(JsonFileResource):
    @property
    def animation_controllers(self) -> list[AnimationControllerBP]: ...
    def get_animation_controller(self, id: str) -> AnimationControllerBP: ...
    def add_animation_controller(self, name: str, data: dict) -> AnimationControllerBP: ...
class FunctionFile(FileResource):
    """
    A FunctionFile is a function file, such as run.mcfunction, and is
    made up of many commands.
    """
    def __init__(self, *args, **kwargs) -> None: ...
    def strip_comments(self):
        """
        Strips all comments from the function file.
        Generally should be used before accessing and using the `commands` property.
        """
    def commands(self) -> list[Command]:
        """
        The list of commands in this function file. Every line represents a Command.
        """
    def _save(self) -> None:
        """
        Writes the commands back to the file, one command at a time.
        """
class FeatureRuleFile(JsonFileResource): ...
class FeatureFile(JsonFileResource): ...
class SpawnRuleFile(JsonFileResource): ...
class RecipeFile(JsonFileResource): ...
class EntityComponentBP(JsonSubResource): ...
class EntityEventBP(JsonSubResource): ...
class Component(JsonSubResource): ...
class ComponentGroup(JsonSubResource):
    @property
    def components(self) -> list[Component]: ...
    def get_component(self, id: str) -> Component: ...
    def add_component(self, name: str, data: dict) -> Component: ...
    """
    A component group is a collection of components in an EntityFileBP.
    """
class EntityFileBP(JsonFileResource):
    @property
    def events(self) -> list[EntityEventBP]: ...
    def get_event(self, id: str) -> EntityEventBP: ...
    def add_event(self, name: str, data: dict) -> EntityEventBP: ...
    @property
    def components(self) -> list[EntityComponentBP]: ...
    def get_component(self, id: str) -> EntityComponentBP: ...
    def add_component(self, name: str, data: dict) -> EntityComponentBP: ...
    @property
    def component_groups(self) -> list[ComponentGroup]: ...
    def get_component_group(self, id: str) -> ComponentGroup: ...
    def add_component_group(self, name: str, data: dict) -> ComponentGroup: ...
    def counterpart(self) -> EntityFileRP: ...
class LootTablePool(JsonSubResource): ...
class LootTableFile(JsonFileResource):
    @property
    def pools(self) -> list[LootTablePool]: ...
    def get_pool(self, id: str) -> LootTablePool: ...
    def add_pool(self, name: str, data: dict) -> LootTablePool: ...
class ItemComponentBP(JsonSubResource): ...
class ItemEventBP(JsonSubResource): ...
class ItemFileBP(JsonFileResource):
    @property
    def components(self) -> list[ItemComponentBP]: ...
    def get_component(self, id: str) -> ItemComponentBP: ...
    def add_component(self, name: str, data: dict) -> ItemComponentBP: ...
    @property
    def events(self) -> list[ItemEventBP]: ...
    def get_event(self, id: str) -> ItemEventBP: ...
    def add_event(self, name: str, data: dict) -> ItemEventBP: ...
class BlockFileComponentBP(JsonSubResource): ...
class BlockFileBP(JsonFileResource): ...
class AnimationBP(JsonSubResource): ...
class AnimationFileBP(JsonFileResource): ...
class BehaviorPack(Pack):
    @property
    def functions(self) -> list[FunctionFile]: ...
    def get_function(self, id: str) -> FunctionFile: ...
    def add_function(self, name: str, data: dict) -> FunctionFile: ...
    @property
    def feature_rules(self) -> list[FeatureRuleFile]: ...
    def get_feature_rule(self, id: str) -> FeatureRuleFile: ...
    def add_feature_rule(self, name: str, data: dict) -> FeatureRuleFile: ...
    @property
    def features(self) -> list[FeatureFile]: ...
    def get_feature(self, id: str) -> FeatureFile: ...
    def add_feature(self, name: str, data: dict) -> FeatureFile: ...
    @property
    def spawn_rules(self) -> list[SpawnRuleFile]: ...
    def get_spawn_rule(self, id: str) -> SpawnRuleFile: ...
    def add_spawn_rule(self, name: str, data: dict) -> SpawnRuleFile: ...
    @property
    def recipes(self) -> list[RecipeFile]: ...
    def get_recipe(self, id: str) -> RecipeFile: ...
    def add_recipe(self, name: str, data: dict) -> RecipeFile: ...
    @property
    def entities(self) -> list[EntityFileBP]: ...
    def get_entity(self, id: str) -> EntityFileBP: ...
    def add_entity(self, name: str, data: dict) -> EntityFileBP: ...
    @property
    def loot_tables(self) -> list[LootTableFile]: ...
    def get_loot_table(self, id: str) -> LootTableFile: ...
    def add_loot_table(self, name: str, data: dict) -> LootTableFile: ...
    @property
    def items(self) -> list[ItemFileBP]: ...
    def get_item(self, id: str) -> ItemFileBP: ...
    def add_item(self, name: str, data: dict) -> ItemFileBP: ...
    @property
    def blocks(self) -> list[BlockFileBP]: ...
    def get_block(self, id: str) -> BlockFileBP: ...
    def add_block(self, name: str, data: dict) -> BlockFileBP: ...
    @property
    def animation_controller_files(self) -> list[AnimationControllerFileBP]: ...
    def get_animation_controller_file(self, id: str) -> AnimationControllerFileBP: ...
    def add_animation_controller_file(self, name: str, data: dict) -> AnimationControllerFileBP: ...
    @property
    def animation_controllers(self) -> list[AnimationControllerBP]: ...
    def get_animation_controller(self, id: str) -> AnimationControllerBP: ...
    @property
    def animation_files(self) -> list[AnimationFileBP]: ...
    def get_animation_file(self, id: str) -> AnimationFileBP: ...
    def add_animation_file(self, name: str, data: dict) -> AnimationFileBP: ...
    @property
    def animations(self) -> list[AnimationBP]: ...
    def get_animation(self, id: str) -> AnimationBP: ...
    """
    The BehaviorPack represents the behavior pack of a project.
    """
class Event(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None: ...
    def groups_to_add(self) -> list[ComponentGroup]: ...
    def groups_to_remove(self) -> list[ComponentGroup]: ...
class Command(Resource):
    """
    A command is a wrapper around a string, which represents a single command
    in a function file.

    To use this class, you can access the 'data' property, and treat it like
    a string.
    """
    def __init__(self, command: str, file: FileResource = None, pack: Pack = None) -> None: ...
    def data(self): ...
    def data(self, data): ...
    def dirty(self): ...
    def dirty(self, dirty):
        """
        When a command is marked as dirty, it must propagate this to the
        file, so that the file can be marked as dirty.
        """
    def is_comment(self): ...
    def __str__(self): ...
    def __repr__(self): ...
class ParticleFileComponent(JsonSubResource): ...
class ParticleFileEvent(JsonSubResource): ...
class ParticleFile(JsonFileResource):
    @property
    def components(self) -> list[ParticleFileComponent]: ...
    def get_component(self, id: str) -> ParticleFileComponent: ...
    def add_component(self, name: str, data: dict) -> ParticleFileComponent: ...
    @property
    def events(self) -> list[ParticleFileEvent]: ...
    def get_event(self, id: str) -> ParticleFileEvent: ...
    def add_event(self, name: str, data: dict) -> ParticleFileEvent: ...
    """
    ParticleFile is a JsonFileResource which represents a particle file.
    """
class AnimationControllerStateRP(JsonSubResource): ...
class AnimationControllerRP(JsonSubResource):
    @property
    def states(self) -> list[AnimationControllerStateRP]: ...
    def get_state(self, id: str) -> AnimationControllerStateRP: ...
    def add_state(self, name: str, data: dict) -> AnimationControllerStateRP: ...
class AnimationControllerFileRP(JsonFileResource):
    @property
    def animation_controllers(self) -> list[AnimationControllerRP]: ...
    def get_animation_controller(self, id: str) -> AnimationControllerRP: ...
    def add_animation_controller(self, name: str, data: dict) -> AnimationControllerRP: ...
    """
    AnimationControllerFileRP
    """
class AnimationRP(JsonSubResource): ...
class AnimationFileRP(JsonFileResource):
    @property
    def animations(self) -> list[AnimationRP]: ...
    def get_animation(self, id: str) -> AnimationRP: ...
    def add_animation(self, name: str, data: dict) -> AnimationRP: ...
    """
    AnimationFileRP is a class which represents a resource pack's animation file.
    Since many animations are defined in the same file, it is often more useful.
    to use the AnimationRP class instead.
    """
class AttachableFileRP(JsonFileResource): ...
class BiomesClientFile(JsonFileResource):
    """
    BiomesClientFile is a class which represents the data stored in 'rp/biomes_client.json'
    """
class BlocksFile(JsonFileResource):
    """
    BlocksFile is a class which represents the data stored in 'rp/blocks.json'
    """
class EntityFileRP(JsonFileResource):
    @property
    def events(self) -> list[EntityEventBP]: ...
    def get_event(self, id: str) -> EntityEventBP: ...
    def add_event(self, name: str, data: dict) -> EntityEventBP: ...
    """
    EntityFileRP is a class which represents a resource pack's entity file.
    """
    def counterpart(self) -> EntityFileBP: ...
    def animations(self) -> list[AnimationTriple]: ...
    def get_animation(self, identifier:str) -> AnimationTriple:
        """
        Fetches an AnimationTriple resource, either by shortname, or identifier.
        """
    def textures(self) -> list[TextureDouble]: ...
    def get_texture(self, identifier:str) -> TextureDouble:
        """
        Fetches a texture resource, either by shortname, or texture_path.
        """
    def models(self) -> list[ModelTriple]: ...
    def get_model(self, identifier:str) -> ModelTriple:
        """
        Fetches a model resource, either by shortname, or identifier.
        """
    def materials(self) -> list[MaterialTriple]: ...
    def get_material(self, identifier:str) -> MaterialTriple:
        """
        Fetches a material resource, either by shortname, or material type.
        """
class FlipbookTexturesFile(JsonFileResource):
    """
    FlipbookTexturesFile is a class which represents the data stored in 'rp/textures/flipbook_textures.json'
    """
class FogDistanceComponent(JsonSubResource): ...
class FogVolumetricDensityComponent(JsonSubResource): ...
class FogVolumetricMediaCoefficient(JsonSubResource): ...
class FogFile(JsonFileResource):
    @property
    def distance_components(self) -> list[FogDistanceComponent]: ...
    def get_distance_component(self, id: str) -> FogDistanceComponent: ...
    def add_distance_component(self, name: str, data: dict) -> FogDistanceComponent: ...
    @property
    def volumetric_density_components(self) -> list[FogVolumetricDensityComponent]: ...
    def get_volumetric_density_component(self, id: str) -> FogVolumetricDensityComponent: ...
    def add_volumetric_density_component(self, name: str, data: dict) -> FogVolumetricDensityComponent: ...
    @property
    def volumetric_media_coefficients(self) -> list[FogVolumetricMediaCoefficient]: ...
    def get_volumetric_media_coefficient(self, id: str) -> FogVolumetricMediaCoefficient: ...
    def add_volumetric_media_coefficient(self, name: str, data: dict) -> FogVolumetricMediaCoefficient: ...
class ItemComponentRP(JsonSubResource): ...
class ItemFileRP(JsonFileResource):
    @property
    def componentss(self) -> list[ItemComponentRP]: ...
    def get_components(self, id: str) -> ItemComponentRP: ...
    def add_components(self, name: str, data: dict) -> ItemComponentRP: ...
class Material(JsonSubResource):
    """
    Represents a single material, from a .material file
    """
class MaterialFile(JsonFileResource):
    @property
    def materials(self) -> list[Material]: ...
    def get_material(self, id: str) -> Material: ...
    def add_material(self, name: str, data: dict) -> Material: ...
    """
    MaterialFile is a class which represents a resource pack's material file.
    Since many materials can be defined in the same file, it is often more useful
    to use the MaterialRP class directly.
    """
class Cube(JsonSubResource): ...
class Bone(JsonSubResource):
    @property
    def cubess(self) -> list[Cube]: ...
    def get_cubes(self, id: str) -> Cube: ...
    def add_cubes(self, name: str, data: dict) -> Cube: ...
class Model(JsonSubResource):
    @property
    def bones(self) -> list[Bone]: ...
    def get_bone(self, id: str) -> Bone: ...
    def add_bone(self, name: str, data: dict) -> Bone: ...
class ModelFile(JsonFileResource):
    @property
    def models(self) -> list[Model]: ...
    def get_model(self, id: str) -> Model: ...
    def add_model(self, name: str, data: dict) -> Model: ...
class RenderController(JsonSubResource):
    """
    A JsonSubResource, representing a single Render Controller object, contained
    within a RenderControllerFile.
    """
class RenderControllerFile(JsonFileResource):
    @property
    def render_controllers(self) -> list[RenderController]: ...
    def get_render_controller(self, id: str) -> RenderController: ...
    def add_render_controller(self, name: str, data: dict) -> RenderController: ...
class SoundDefinitionsFile(JsonFileResource):
    """
    SoundsDefinitionFile is a class which represents the data stored in
    'rp/sounds/sound_definitions.json'
    """
class SoundsFile(JsonFileResource):
    """
    SoundsFile is a class which represents the data stored in 'rp/sounds.json'
    """
class StandAloneTextureFile(JsonFileResource):
    """
    StandAloneTextureFile is a class which represents the data stored in 'rp/textures/*_texture.json'.
    Examples: 'item_texture.json', 'terrain_texture.json.

    These actual children are subclassed
    """
    def __init__(self, data: dict = None, filepath: str = None, pack: Pack = None) -> None: ...
    def texture_definitions(self) -> list[TextureFileDouble]: ...
    def get_texture_definition(self, shortname: str) -> TextureFileDouble: ...
    def add_texture_definition(self, shortname: str, textures: list[str]): ...
class TerrainTextureFile(StandAloneTextureFile): ...
class ItemTextureFile(StandAloneTextureFile): ...
class ResourceTriple(JsonSubResource):
    """
    Base class for handling "shortname": "identifier" pairs, with an underlying, resource.
    """
    def shortname(self):
        """
        This represents the shortname of the resource. e.g., "shortname": "identifier"
        """
    def shortname(self, shortname): ...
    def identifier(self):
        """
        This represents the identifier of the resource. e.g., "shortname": "identifier"
        """
    def identifier(self, identifier): ...
    def resource():
        """
        Returns the identifier associated with the resource.
        """
class MaterialTriple(ResourceTriple):
    """
    A special sub-resource, which represents a material within an RP entity.
    """
    def resource(self): ...
class AnimationTriple(ResourceTriple):
    """
    A special sub-resource, which represents an animation within an RP entity.
    """
    def resource(self): ...
class ModelTriple(ResourceTriple):
    """
    A special sub-resource, which represents a model within an RP entity.
    """
    def resource(self): ...
class TextureDouble(JsonSubResource):
    """
    A special sub-resource, which represents a texture within an RP entity.
    """
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None: ...
    def shortname(self): ...
    def shortname(self, shortname): ...
    def texture_path(self): ...
    def texture_path(self, texture_path): ...
    def exists(self) -> bool:
        """
        Returns True if this resource exists in the pack.
        """
class TextureFileDouble(JsonSubResource):
    """
    A special sub-resource, which represents a texture within a texture
    definition file, such as 'item_texture.json' ...

    This is a special case, as it has some additional logic for obscuring the
    texture path. This is because textures are stored nested under 
    'textures' which is simply inconvenient to work with.
    """
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None: ...
    def shortname(self): ...
    def shortname(self, shortname): ...
    def data(self):
        """
        Custom data getter allows us to re-create the json structure based
        on the saved textures.
        """
class ResourcePack(Pack):
    @property
    def particles(self) -> list[ParticleFile]: ...
    def get_particle(self, id: str) -> ParticleFile: ...
    def add_particle(self, name: str, data: dict) -> ParticleFile: ...
    @property
    def attachables(self) -> list[AttachableFileRP]: ...
    def get_attachable(self, id: str) -> AttachableFileRP: ...
    def add_attachable(self, name: str, data: dict) -> AttachableFileRP: ...
    @property
    def entities(self) -> list[EntityFileRP]: ...
    def get_entity(self, id: str) -> EntityFileRP: ...
    def add_entity(self, name: str, data: dict) -> EntityFileRP: ...
    @property
    def fogs(self) -> list[FogFile]: ...
    def get_fog(self, id: str) -> FogFile: ...
    def add_fog(self, name: str, data: dict) -> FogFile: ...
    @property
    def itemss(self) -> list[ItemFileRP]: ...
    def get_items(self, id: str) -> ItemFileRP: ...
    def add_items(self, name: str, data: dict) -> ItemFileRP: ...
    @property
    def animation_controller_files(self) -> list[AnimationControllerFileRP]: ...
    def get_animation_controller_file(self, id: str) -> AnimationControllerFileRP: ...
    def add_animation_controller_file(self, name: str, data: dict) -> AnimationControllerFileRP: ...
    @property
    def animation_controllers(self) -> list[AnimationControllerRP]: ...
    def get_animation_controller(self, id: str) -> AnimationControllerRP: ...
    @property
    def animation_files(self) -> list[AnimationFileRP]: ...
    def get_animation_file(self, id: str) -> AnimationFileRP: ...
    def add_animation_file(self, name: str, data: dict) -> AnimationFileRP: ...
    @property
    def animations(self) -> list[AnimationRP]: ...
    def get_animation(self, id: str) -> AnimationRP: ...
    @property
    def material_files(self) -> list[MaterialFile]: ...
    def get_material_file(self, id: str) -> MaterialFile: ...
    def add_material_file(self, name: str, data: dict) -> MaterialFile: ...
    @property
    def materials(self) -> list[Material]: ...
    def get_material(self, id: str) -> Material: ...
    @property
    def model_files(self) -> list[ModelFile]: ...
    def get_model_file(self, id: str) -> ModelFile: ...
    def add_model_file(self, name: str, data: dict) -> ModelFile: ...
    @property
    def models(self) -> list[Model]: ...
    def get_model(self, id: str) -> Model: ...
    @property
    def render_controller_files(self) -> list[RenderControllerFile]: ...
    def get_render_controller_file(self, id: str) -> RenderControllerFile: ...
    def add_render_controller_file(self, name: str, data: dict) -> RenderControllerFile: ...
    @property
    def render_controllers(self) -> list[RenderController]: ...
    def get_render_controller(self, id: str) -> RenderController: ...
    @property
    def sounds_file(self) -> list[SoundsFile]: ...
    @property
    def sound_definitions_file(self) -> list[SoundDefinitionsFile]: ...
    @property
    def flipbook_textures_file(self) -> list[FlipbookTexturesFile]: ...
    @property
    def blocks_file(self) -> list[BlocksFile]: ...
    @property
    def biomes_client_file(self) -> list[BiomesClientFile]: ...
    @property
    def terrain_texture_file(self) -> list[TerrainTextureFile]: ...
    @property
    def item_texture_file(self) -> list[ItemTextureFile]: ...
    def __init__(self, input_path: str, project: Project = None): ...
    def sounds(self) -> list[str]:
        """
        Returns a list of all sounds in the pack, relative to the pack root.
        """
    def get_sounds(self, search_path: str = "", trim_extension: bool = True) -> list[str]:
        """
        Returns a list of all child sounds of the searchpath, relative to the pack root. 
        Search path should not include 'sounds'.

        You may optionally trim the extension from the returned paths.

        Example: rp.get_sounds("entities", trim_extension=True)
        """
    def textures(self) -> list[str]:
        """
        Returns a list of all textures in the pack, relative to the pack root.

        Example: "textures/my_texture.png"
        """
    def get_textures(self, search_path: str = "", trim_extension: bool = True) -> list[str]:
        """
        Returns a list of all child textures of the searchpath, relative to the pack root. 
        Search path should not include 'textures'.

        You may optionally trim the extension from the returned paths.

        Example: rp.get_textures("entities", trim_extension=True)
        """
