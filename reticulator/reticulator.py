from __future__ import annotations

import re
import os
import glob

from functools import cached_property
from typing import Tuple

from core import *

def format_version(jsonpath: str = "format_version"):
    """
    Class Decorator which inserts a 'format_version' property, with proper
    semantics.
    """

    def inner_format_version(cls):
        @property
        def format_version(self) -> FormatVersion:
            return FormatVersion(self.get_jsonpath(jsonpath))
        
        @format_version.setter
        def format_version(self, format_version):
            return self.set_jsonpath(jsonpath, str(FormatVersion(format_version)))

        cls.format_version = format_version
        return cls
    
    return inner_format_version


def identifier(jsonpath: str):
    """
    Class Decorator, which injects handling for accessing 'identifier'.
    :param jsonpath: The jsonpath where the identifier can be located.
    """

    def inner(cls):
        @property
        def identifier(self) -> str:
            return self.get_jsonpath(jsonpath)
        
        @identifier.setter
        def identifier(self, identifier):
            return self.set_jsonpath(jsonpath, identifier)

        cls.identifier = identifier
        
        return cls

    return inner


class Pack():
    """
    Pack is a parent class that contains the shared functionality between the
    resource pack and the behavior pack.
    """
    def __init__(self, input_directory: str, project : Project = None):
        self.resources = []
        self._language_files = []
        self._project = project

        # The input path is the path to the folder containing the pack.
        self.input_path: str = input_directory

        # The output path is the path to the output directory, where this
        # pack will be saved. This is the same as the input path, unless
        # explicitely saved.
        self.output_directory: str = input_directory

    @cached_property
    def project(self) -> Project:
        """
        Get the project that this pack is part of. May be None.
        """
        return self._project

    def save(self, force=False):
        """
        Saves every child resource.
        """
        for resource in self.resources:
            resource.save(force=force)

    def register_resource(self, resource: Resource) -> None:
        """
        Register a child resource to this pack. These resources will be saved
        during save.
        """

        # Attempt to set the pack for this resource.
        try:
            resource.pack = self
        except Exception:
            pass
        self.resources.append(resource)

    def get_language_file(self, filepath:str) -> LanguageFile:
        """
        Gets a specific language file, based on the name of the language file.
        For example, 'texts/en_GB.lang'
        """
        for language_file in self.language_files:
            if smart_compare(language_file.filepath, filepath):
                return language_file
        raise AssetNotFoundError(filepath)

    @cached_property
    def language_files(self) -> list[LanguageFile]:
        """
        Returns a list of LanguageFiles, as read from 'texts/*'
        """
        base_directory = os.path.join(self.input_path, "texts")
        for local_path in glob.glob(base_directory + "/**/*.lang", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self._language_files.append(LanguageFile(filepath = local_path, pack = self))
            
        return self._language_files

class Project():
    """
    Project is a class which represents an entire 'addon', via references to a 
    ResourcePack and BehaviorPack, along with some helper methods.
    """
    def __init__(self, behavior_path: str, resource_path: str) -> Project:
        self.__behavior_path = behavior_path
        self.__resource_path = resource_path
        self.__resource_pack : ResourcePack = None
        self.__behavior_pack : BehaviorPack = None
    
    def set_output_directory(self, save_location: str) -> None:
        """
        Sets the save location of the RP and the BP, based on the folder
        name from their input path.

        In other words, pass in a folder where you want both the RP and the BP 
        to be saved.

        If you need finer control, use the 'set_save_location' method on the 
        ResourcePack and BehaviorPack instead.
        """
        self.resource_pack.output_directory = save_location + "/" + os.path.dirname(self.resource_pack.input_path)
        self.behavior_pack.output_directory = save_location + "/" + os.path.dirname(self.behavior_pack.input_path)

    def get_packs(self) -> Tuple[behavior_pack, resource_pack]:
        """
        Returns Behavior Pack followed by ResourcePack.
        Useful for quickly defining rp and bp:
        rp, bp = Project("...").get_packs()
        """
        return self.behavior_pack, self.resource_pack
        
    @cached_property
    def resource_pack(self) -> ResourcePack:
        """
        The resource pack of the project.
        """
        self.__resource_pack = ResourcePack(self.__resource_path, project=self)
        return self.__resource_pack

    @cached_property
    def behavior_pack(self) -> BehaviorPack:
        """
        The behavior pack of the project.
        """
        self.__behavior_pack = BehaviorPack(self.__behavior_path, project=self)
        return self.__behavior_pack

    def save(self, force=False):
        """
        Saves both packs.
        """
        self.__behavior_pack.save(force=force)
        self.__resource_pack.save(force=force)


class LanguageFile(FileResource):
    """
    A LanguageFile is a language file, such as 'en_US.lang', and is made
    up of many Translations.
    """
    def __init__(self, filepath: str = None, pack: Pack = None) -> None:
        super().__init__(filepath=filepath, pack=pack)
        self.__translations: list[Translation] = []
    
    def get_translation(self, key: str) -> Translation:
        """
        Whether the language file contains the specified key.
        """
        for translation in self.translations:
            if translation.key == key:
                return translation 
        raise AssetNotFoundError(f"Translation with key '{key}' not found in language file '{self.filepath}'.")

    def contains_translation(self, key: str) -> bool:
        """
        Whether the language file contains the specified key.
        """

        for translation in self.translations:
            if translation.key == key:
                return True
        return False

    def delete_translation(self, key: str) -> None:
        """
        Deletes a translation based on key, if it exists.
        """
        for translation in self.translations:
            if translation.key == key:
                self.dirty = True
                self.translations.remove(translation)
                return

    def add_translation(self, translation: Translation, overwrite: bool = True) -> bool:
        """
        Adds a new translation key. Overwrites by default.
        """

        # We must complain about duplicates.
        # If no overwrite, don't add
        # If overwrite, delete previous translation
        if self.contains_translation(translation.key):
            if not overwrite:
                return False
            else:
                self.delete_translation(translation.key)

        self.dirty = True
        self.__translations.append(translation)

        return True

    def _save(self):
        path = os.path.join(self.pack.output_directory, self.filepath)
        create_nested_directory(path)
        with open(path, 'w', encoding='utf-8') as file:
            for translation in self.translations:
                file.write(f"{translation.key}={translation.value}\t##{translation.comment}\n")


    @cached_property
    def translations(self) -> list[Translation]:
        with open(os.path.join(self.pack.input_path, self.filepath), "r", encoding='utf-8') as language_file:
            for line in language_file.readlines():
                language_regex = "^([^#\n]+?)=([^#]+)#*?([^#]*?)$"
                if match := re.search(language_regex, line):
                    groups = match.groups()
                    self.__translations.append(
                        Translation(
                            key = groups[0].strip() if len(groups) > 0 else "",
                            value = groups[1].strip() if len(groups) > 1 else "",
                            comment = groups[2].strip() if len(groups) > 2 else "",
                        )
                    )
        return self.__translations

# Generic Resources
class Translation():
    """
    Dataclass for a translation. Many translations together make up a
    TranslationFile.
    """

    def __init__(self, key: str, value: str, comment: str = "") -> None:
        self.key = key
        self.value = value
        self.comment = comment

class FormatVersion():
    def __init__(self, version) -> None:
        if isinstance(version, FormatVersion):
            self.major = version.major
            self.minor = version.minor
            self.patch = version.patch
            return
        elif isinstance(version, str):
            elements = version.split('.')
        else:
            # Change to suitable error
            raise TypeError()

        # Pack with extra data if it's missing
        for i in range(3 - len(elements)):
            elements.append('0')
        
        self.major = int(elements[0])
        self.minor = int(elements[1])
        self.patch = int(elements[2])

    def __repr__(self) -> str:
        return f'{self.major}.{self.minor}.{self.patch}'
        
    def __eq__(self, other):
        other = FormatVersion(other)
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __gt__(self, other):
        if self.major > other.major:
            return True
        elif self.major < other.major:
            return False

        if self.minor > other.minor:
            return True
        elif self.minor < other.minor:
            return False

        if self.patch > other.patch:
            return True
        elif self.patch < other.patch:
            return False
        
        return self != other


class AnimationControllerBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animation_controllers",
        attribute = "animation_controller",
        getter_attribute = "id"
    )

@format_version()
@ImplementsSubResource(
    AnimationControllerBP
)
class AnimationControllerFileBP(JsonFileResource):
    type_info = TypeInfo(
        filepath = "animation_controllers",
        attribute = "animation_controller_file",
        getter_attribute = "filepath",
        child_cls = AnimationControllerBP
    )


class FunctionFile(FileResource):
    """
    A FunctionFile is a function file, such as run.mcfunction, and is
    made up of many commands.
    """
    
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._commands : list[Command] = []

    type_info = TypeInfo(
        filepath = "functions",
        extension = ".mcfunction",
        attribute = "function",
        getter_attribute="filepath"
    )
    
    def strip_comments(self):
        """
        Strips all comments from the function file.
        Generally should be used before accessing and using the `commands` property.
        """
        self.commands = [c for c in self.commands if not c.is_comment()]

    @cached_property
    def commands(self) -> list[Command]:
        """
        The list of commands in this function file. Every line represents a Command.
        """
        with open(os.path.join(self.pack.input_path, self.filepath), "r", encoding='utf-8') as function_file:
            for line in function_file.readlines():
                command = line.strip()
                if command:
                    self._commands.append(Command(command, file=self, pack=self.pack))
        self._commands = convert_to_notify_structure(self._commands, self)
        return self._commands
    
    def _save(self) -> None:
        """
        Writes the commands back to the file, one command at a time.
        """
        path = os.path.join(self.pack.output_directory, self.filepath)
        create_nested_directory(path)
        with open(path, 'w', encoding='utf-8') as file:
            for command in self.commands:
                file.write(command.data + '\n')

@identifier("minecraft:feature_rules/description/identifier")
@format_version()
class FeatureRuleFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "feature_rules",
        attribute = "feature_rule",
        getter_attribute="identifier"
    )

@identifier("**/description/identifier")
@format_version()
class FeatureFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "features",
        attribute = "feature",
        getter_attribute="identifier"
    )
    
@format_version()
@identifier("minecraft:spawn_rules/description/identifier")
class SpawnRuleFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "spawn_rules",
        attribute = "spawn_rule",
        getter_attribute="identifier"
    )

@identifier("**/identifier")
@format_version()
class RecipeFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "recipes",
        attribute = "recipe",
        getter_attribute="identifier"
    )

class EntityComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/components",
        attribute = "component",
        getter_attribute = "id"
    )

class EntityEventBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/events",
        attribute = "event",
        getter_attribute = "id"
    )

class Component(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "**",
        attribute = "component",
        getter_attribute = "id"
    )

@ImplementsSubResource(
    Component
)
class ComponentGroup(JsonSubResource):
    """
    A component group is a collection of components in an EntityFileBP.
    """
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/component_groups",
        attribute = "component_group",
        getter_attribute = "id"
    )

@format_version()
@identifier("minecraft:entity/description/identifier")
@ImplementsSubResource(
    EntityEventBP, 
    EntityComponentBP, 
    ComponentGroup
)
class EntityFileBP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "entities",
        attribute = "entity",
        plural = "entities",
        getter_attribute = "identifier"
    )

    @property
    def counterpart(self) -> EntityFileRP:
        return self.pack.project.resource_pack.get_entity(self.identifier)

class LootTablePool(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "pools",
        attribute = "pool"
    )

@ImplementsSubResource(
    LootTablePool
)
class LootTableFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "loot_tables",
        attribute = "loot_table",
        getter_attribute = "filepath"
    )

class ItemComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/components",
        attribute = "component",
        getter_attribute = "id"
    )

class ItemEventBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/events",
        attribute = "event",
        getter_attribute = "id"
    )


@format_version()
@identifier("minecraft:item/description/identifier")
@ImplementsSubResource(
    ItemComponentBP, 
    ItemEventBP
)
class ItemFileBP(JsonFileResource):
    type_info = TypeInfo(
        filepath = "items",
        attribute = "item",
        getter_attribute = "identifier"
    )

class BlockFileComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:block/components",
        attribute = "component",
        getter_attribute = "id"
    )


@format_version()
@identifier(jsonpath="minecraft:block/description/identifier")
@ImplementsSubResource(BlockFileComponentBP)
class BlockFileBP(JsonFileResource):
    type_info = TypeInfo(
        filepath = "blocks",
        attribute = "block",
        getter_attribute = "identifier"
    )

@ClassProperty('loop')
class AnimationBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animations",
        attribute = "animation",
        getter_attribute = "id"
    )

@ImplementsSubResource(AnimationBP)
class AnimationFileBP(JsonFileResource):
    type_info = TypeInfo(
        filepath = "animations",
        attribute = "animation_file",
        getter_attribute = "filepath",
        child_cls=AnimationBP
    )

@ImplementsResource(
    FunctionFile,
    FeatureRuleFile,
    FeatureFile,
    SpawnRuleFile,
    RecipeFile,
    EntityFileBP,
    LootTableFile,
    ItemFileBP,
    BlockFileBP,
    AnimationControllerFileBP,
    AnimationFileBP
)
class BehaviorPack(Pack):
    """
    The BehaviorPack represents the behavior pack of a project.
    """

class Event(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__groups_to_add = []
        self.__groups_to_remove = []

    @cached_property
    def groups_to_add(self) -> list[ComponentGroup]:
        for path, data in self.get_data_at("add/component_groups"):
            self.__groups_to_add.append(ComponentGroup(parent = self, json_path = path, data = data))
        return self.__groups_to_add
    
    @cached_property
    def groups_to_remove(self) -> list[ComponentGroup]:
        for path, data in self.get_data_at("remove/component_groups"):
            self.__groups_to_remove.append(ComponentGroup(parent = self, json_path = path, data = data))
        return self.__groups_to_remove

class Command(Resource):
    """
    A command is a wrapper around a string, which represents a single command
    in a function file.

    To use this class, you can access the 'data' property, and treat it like
    a string.
    """
    def __init__(self, command: str, file: FileResource = None, pack: Pack = None) -> None:
        super().__init__(file=file, pack=pack)

        # The 'data' is the actual command, which is stored as a string.
        self._data: str = command

    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, data):
        self._data = data
        self.dirty = True

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        """
        When a command is marked as dirty, it must propagate this to the
        file, so that the file can be marked as dirty.
        """
        self._dirty = dirty
        self.file.dirty = dirty

    def is_comment(self):
        return self.data.startswith("#")

    def __str__(self):
        return self.data

    def __repr__(self):
        return f"Command: '{self.data}'"

class ParticleFileComponent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "particle_effect/components",
        attribute = "component",
        getter_attribute = "id"
    )

class ParticleFileEvent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "particle_effect/events",
        attribute = "event",
        getter_attribute = "id"
    )

@format_version()
@identifier("particle_effect/description/identifier")
@ImplementsSubResource(
    ParticleFileComponent,
    ParticleFileEvent
)
class ParticleFile(JsonFileResource):
    """
    ParticleFile is a JsonFileResource which represents a particle file.
    """
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "particles",
        attribute = "particle",
        getter_attribute = "identifier",
    )

class AnimationControllerStateRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "states",
        attribute = "state",
        getter_attribute = "id"
    )

@ClassProperty('initial_state')
@ImplementsSubResource(
    AnimationControllerStateRP
)
class AnimationControllerRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animation_controllers",
        attribute = "animation_controller",
        getter_attribute = "id"
    )

@ImplementsSubResource(
    AnimationControllerRP
)
class AnimationControllerFileRP(JsonFileResource):
    """
    AnimationControllerFileRP
    """
    type_info = TypeInfo(
        filepath = "animation_controllers",
        attribute = "animation_controller_file",
        getter_attribute = "filepath",
        child_cls=AnimationControllerRP
    )

@ClassProperty('loop')
class AnimationRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animations",
        attribute = "animation",
        getter_attribute = "id"
    )

@ImplementsSubResource(
    AnimationRP
)
class AnimationFileRP(JsonFileResource):
    """
    AnimationFileRP is a class which represents a resource pack's animation file.
    Since many animations are defined in the same file, it is often more useful.
    to use the AnimationRP class instead.
    """

    type_info = TypeInfo(
        filepath = "animations",
        attribute = "animation_file",
        getter_attribute = "filepath",
        child_cls=AnimationRP
    )


@format_version()
@identifier("minecraft:attachable/description/identifier")
class AttachableFileRP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "attachables",
        attribute = "attachable",
        getter_attribute = "identifier"
    )


class BiomesClientFile(JsonFileResource):
    """
    BiomesClientFile is a class which represents the data stored in 'rp/biomes_client.json'
    """

    type_info = TypeInfo(
        filepath = "biomes_client",
        attribute = "biomes_client_file",
        plural = "biomes_client_file"
    )


class BlocksFile(JsonFileResource):
    """
    BlocksFile is a class which represents the data stored in 'rp/blocks.json'
    """

    type_info = TypeInfo(
        filepath = "blocks",
        attribute = "blocks_file"
    )



@format_version()
@identifier("minecraft:client_entity/description/identifier")
@ImplementsSubResource(
    EntityEventBP
)
class EntityFileRP(JsonFileResource):
    """
    EntityFileRP is a class which represents a resource pack's entity file.
    """
    type_info = TypeInfo(
        filepath = "entity",
        attribute = "entity",
        plural = "entities",
        getter_attribute = "identifier"
    )

    @property
    def counterpart(self) -> EntityFileBP:
        return self.pack.project.behavior_pack.get_entity(self.identifier)

    # TODO: See if the decoration system can apply to these 'triples'.
    # Or we need to add 'adders' for all three (anim, texture, model)
    @cached_property
    def animations(self) -> list[AnimationTriple]:
        self._animations = []
        for path, data in self.get_data_at("minecraft:client_entity/description/animations"):
            self._animations.append(AnimationTriple(parent = self, json_path = path, data = data))
        return self._animations
    
    def get_animation(self, identifier:str) -> AnimationTriple:
        """
        Fetches an AnimationTriple resource, either by shortname, or identifier.
        """
        for child in self.animations:
            if smart_compare(child.shortname, identifier) or smart_compare(child.identifier, identifier):
                return child
        raise AssetNotFoundError(id)

    @cached_property
    def textures(self) -> list[TextureDouble]:
        self._textures = []
        for path, data in self.get_data_at("minecraft:client_entity/description/textures"):
            self._textures.append(TextureDouble(parent = self, json_path = path, data = data))
        return self._textures
    
    def get_texture(self, identifier:str) -> TextureDouble:
        """
        Fetches a texture resource, either by shortname, or texture_path.
        """
        for child in self.textures:
            if smart_compare(child.shortname, identifier) or smart_compare(child.texture_path, identifier):
                return child
        raise AssetNotFoundError(id)

    @cached_property
    def models(self) -> list[ModelTriple]:
        self._models = []
        for path, data in self.get_data_at("minecraft:client_entity/description/geometry"):
            self._models.append(ModelTriple(parent = self, json_path = path, data = data))
        return self._models
    
    def get_model(self, identifier:str) -> ModelTriple:
        """
        Fetches a model resource, either by shortname, or identifier.
        """
        for child in self.models:
            if smart_compare(child.shortname, identifier) or smart_compare(child.identifier, identifier):
                return child
        raise AssetNotFoundError(id)

    @cached_property
    def materials(self) -> list[MaterialTriple]:
        self._materials = []
        for path, data in self.get_data_at("minecraft:client_entity/description/materials"):
            self._materials.append(MaterialTriple(parent = self, json_path = path, data = data))
        return self._materials
    
    def get_material(self, identifier:str) -> MaterialTriple:
        """
        Fetches a material resource, either by shortname, or material type.
        """
        for child in self.materials:
            if smart_compare(child.shortname, identifier) or smart_compare(child.identifier, identifier):
                return child
        raise AssetNotFoundError(id)


class FlipbookTexturesFile(JsonFileResource):
    """
    FlipbookTexturesFile is a class which represents the data stored in 'rp/textures/flipbook_textures.json'
    """

    type_info = TypeInfo(
        filepath = "textures/flipbook_textures",
        attribute = "flipbook_textures_file"
    )


class FogDistanceComponent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:fog_settings/distance",
        attribute = "distance_component",
        getter_attribute = "id"
    )

class FogVolumetricDensityComponent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:fog_settings/volumetric/density",
        attribute = "volumetric_density_component",
        getter_attribute = "id"
    )

class FogVolumetricMediaCoefficient(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:fog_settings/volumetric/media_coefficients",
        attribute = "volumetric_media_coefficient",
        getter_attribute = "id"
    )

@format_version()
@identifier("minecraft:fog_settings/description/identifier")
@ImplementsSubResource(
    FogDistanceComponent,
    FogVolumetricDensityComponent,
    FogVolumetricMediaCoefficient,
    
)
class FogFile(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "fogs",
        attribute = "fog",
        getter_attribute = "identifier"
    )

class ItemComponentRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/components",
        attribute = "components",
        getter_attribute = "id"
    )

@format_version()
@identifier("minecraft:item/description/identifier")
@ImplementsSubResource(
    ItemComponentRP
)
class ItemFileRP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "items",
        attribute = "items",
        getter_attribute = "filepath"
    )

class Material(JsonSubResource):
    """
    Represents a single material, from a .material file
    """

    type_info = TypeInfo(
        jsonpath = "**",
        attribute = "material",
        getter_attribute = "id"
    )

@format_version(jsonpath="materials/version")
@ImplementsSubResource(
    Material
)
class MaterialFile(JsonFileResource):
    """
    MaterialFile is a class which represents a resource pack's material file.
    Since many materials can be defined in the same file, it is often more useful
    to use the MaterialRP class directly.
    """
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "materials",
        attribute = "material_file",
        getter_attribute = "filepath",
        extension="material",
        child_cls=Material
    )

class Cube(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "cubes",
        attribute = "cubes",
        getter_attribute = "id"
    )

@ClassProperty("name")
@ImplementsSubResource(
    Cube
)
class Bone(JsonSubResource):
    name: str
    type_info = TypeInfo(
        jsonpath = "bones",
        attribute = "bone",
        getter_attribute = "name"
    )


@identifier("description/identifier")
@ImplementsSubResource(
    Bone
)
class Model(JsonSubResource):
    identifier: str
    type_info = TypeInfo(
        jsonpath = "minecraft:geometry",
        attribute = "model",
        getter_attribute = "identifier"
    )

@format_version()
@ImplementsSubResource(
    Model
)
class ModelFile(JsonFileResource):
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "models",
        attribute = "model_file",
        getter_attribute = "filepath",
        child_cls=Model
    )

class RenderController(JsonSubResource):
    """
    A JsonSubResource, representing a single Render Controller object, contained
    within a RenderControllerFile.
    """

    type_info = TypeInfo(
        jsonpath = "render_controllers",
        attribute = "render_controller",
        getter_attribute = "id"
    )

@format_version()
@ImplementsSubResource(
    RenderController
)
class RenderControllerFile(JsonFileResource):
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "render_controllers",
        attribute = "render_controller_file",
        getter_attribute = "filepath",
        child_cls=RenderController
    )


@format_version()
class SoundDefinitionsFile(JsonFileResource):
    """
    SoundsDefinitionFile is a class which represents the data stored in
    'rp/sounds/sound_definitions.json'
    """
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "sounds/sound_definitions",
        attribute = "sound_definitions_file"
    )


class SoundsFile(JsonFileResource):
    """
    SoundsFile is a class which represents the data stored in 'rp/sounds.json'
    """
    type_info = TypeInfo(
        filepath = "sounds",
        attribute = "sounds_file"
    )

class StandAloneTextureFile(JsonFileResource):
    """
    StandAloneTextureFile is a class which represents the data stored in 'rp/textures/*_texture.json'.
    Examples: 'item_texture.json', 'terrain_texture.json.

    These actual children are subclassed
    """
    def __init__(self, data: dict = None, filepath: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, filepath = filepath, pack = pack)
        self.__texture_definitions = []
    
    @cached_property
    def texture_definitions(self) -> list[TextureFileDouble]:
        for path, data in self.get_data_at("texture_data"):
            self.__texture_definitions.append(TextureFileDouble(parent = self, json_path = path, data = data))
        return self.__texture_definitions

    def get_texture_definition(self, shortname: str) -> TextureFileDouble:
        for child in self.texture_definitions:
            if child.shortname == shortname:
                return child
        raise AssetNotFoundError(f"Texture definition for shortname '{shortname}' not found.")

    def add_texture_definition(self, shortname: str, textures: list[str]):
        self.set_jsonpath(f"texture_data/{shortname}", {
            "textures": textures
        })
        self.__texture_definitions.append(TextureFileDouble(parent = self, json_path = f"texture_data/{shortname}", data = {"textures": textures}))

class TerrainTextureFile(StandAloneTextureFile):
    type_info = TypeInfo(
        filepath = "textures/terrain_texture",
        attribute = "terrain_texture_file"
    )

class ItemTextureFile(StandAloneTextureFile):
    type_info = TypeInfo(
        filepath = "textures/item_texture",
        attribute = "item_texture_file"
    )
    

class ResourceTriple(JsonSubResource):
    """
    Base class for handling "shortname": "identifier" pairs, with an underlying, resource.
    """
    @property
    def shortname(self):
        """
        This represents the shortname of the resource. e.g., "shortname": "identifier"
        """
        return self.id

    @shortname.setter
    def shortname(self, shortname):
        self.id = shortname
    
    @property
    def identifier(self):
        """
        This represents the identifier of the resource. e.g., "shortname": "identifier"
        """
        return self.data
    
    @identifier.setter
    def identifier(self, identifier):
        self.data = identifier

    def resource():
        """
        Returns the identifier associated with the resource.
        """
        raise NotImplementedError

class MaterialTriple(ResourceTriple):
    """
    A special sub-resource, which represents a material within an RP entity.
    """

    @property
    def resource(self):
        return self.parent.pack.get_material(self.identifier)


class AnimationTriple(ResourceTriple):
    """
    A special sub-resource, which represents an animation within an RP entity.
    """

    @property
    def resource(self):
        return self.parent.pack.get_animation(self.identifier)
    
class ModelTriple(ResourceTriple):
    """
    A special sub-resource, which represents a model within an RP entity.
    """

    @property
    def resource(self):
        return self.parent.pack.get_model(self.identifier)
    

class TextureDouble(JsonSubResource):
    """
    A special sub-resource, which represents a texture within an RP entity.
    """
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)

    @property
    def shortname(self):
        return self.id

    @shortname.setter
    def shortname(self, shortname):
        self.id = shortname
    
    @property
    def texture_path(self):
        return self.data
    
    @texture_path.setter
    def texture_path(self, texture_path):
        self.data = texture_path
    
    def exists(self) -> bool:
        """
        Returns True if this resource exists in the pack.
        """
        return os.path.exists(os.path.join(self.pack.input_path, self.filepath))


class TextureFileDouble(JsonSubResource):
    """
    A special sub-resource, which represents a texture within a texture
    definition file, such as 'item_texture.json'

    This is a special case, as it has some additional logic for obscuring the
    texture path. This is because textures are stored nested under 
    'textures' which is simply inconvenient to work with.
    """

    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
 
        self.textures = data.get("textures", [])
        if not isinstance(self.textures, list):
            self.textures = [self.textures]
        
        self.textures = convert_to_notify_structure(self.textures, self)
        
    @property
    def shortname(self):
        return self.id

    @shortname.setter
    def shortname(self, shortname):
        self.id = shortname
    
    @property
    def data(self):
        """
        Custom data getter allows us to re-create the json structure based
        on the saved textures.
        """
        return {
            "textures": self.textures
        }

@ImplementsResource(
    ParticleFile,
    AttachableFileRP,
    EntityFileRP,
    FogFile,
    ItemFileRP,
    AnimationControllerFileRP,
    AnimationFileRP,
    MaterialFile,
    ModelFile,
    RenderControllerFile
)
class ResourcePack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self._sounds: list[str] = []
        self._textures: list[str] = []

    @cached_property
    def sounds(self) -> list[str]:
        """
        Returns a list of all sounds in the pack, relative to the pack root.
        """
        glob_pattern = os.path.join(self.input_path, "sounds") + "/**/*."
        for extension in SOUND_EXTENSIONS:
            self._sounds.extend(glob.glob(glob_pattern + extension, recursive=True))

        self._sounds = [os.path.relpath(path, self.input_path).replace(os.sep, '/') for path in self._sounds]
        return self._sounds

    def get_sounds(self, search_path: str = "", trim_extension: bool = True) -> list[str]:
        """
        Returns a list of all child sounds of the searchpath, relative to the pack root. 
        Search path should not include 'sounds'.

        You may optionally trim the extension from the returned paths.

        Example: rp.get_sounds("entities", trim_extension=True)
        """
        sounds = []
        glob_pattern = os.path.join(self.input_path, "sounds", search_path) + "/**/*."
        for extension in SOUND_EXTENSIONS:
            sounds.extend(glob.glob(glob_pattern + extension, recursive=True))

        sounds = [os.path.relpath(path, self.input_path).replace(os.sep, '/') for path in sounds]
        if trim_extension:
            sounds = [os.path.splitext(path)[0] for path in sounds]
        return sounds
    
    @cached_property
    def textures(self) -> list[str]:
        """
        Returns a list of all textures in the pack, relative to the pack root.

        Example: "textures/my_texture.png"
        """
        glob_pattern = os.path.join(self.input_path, "textures") + "/**/*."
        for extension in TEXTURE_EXTENSIONS:
            self._textures.extend(glob.glob(glob_pattern + extension, recursive=True)) 

        self._textures = [os.path.relpath(path, self.input_path).replace(os.sep, '/') for path in self._textures]
        return self._textures
    
    def get_textures(self, search_path: str = "", trim_extension: bool = True) -> list[str]:
        """
        Returns a list of all child textures of the searchpath, relative to the pack root. 
        Search path should not include 'textures'.

        You may optionally trim the extension from the returned paths.

        Example: rp.get_textures("entities", trim_extension=True)
        """
        textures = []
        glob_pattern = os.path.join(self.input_path, "textures", search_path) + "/**/*."
        for extension in TEXTURE_EXTENSIONS:
            textures.extend(glob.glob(glob_pattern + extension, recursive=True))

        textures = [os.path.relpath(path, self.input_path).replace(os.sep, '/') for path in textures]
        if trim_extension:
            textures = [os.path.splitext(path)[0] for path in textures]
        return textures

    # === Individual Files ===

    @SingleResourceDefinition(SoundsFile)
    def sounds_file(self): pass

    @SingleResourceDefinition(SoundDefinitionsFile)
    def sound_definitions_file(self): pass

    @SingleResourceDefinition(FlipbookTexturesFile)
    def flipbook_textures_file(self): pass

    @SingleResourceDefinition(BlocksFile)
    def blocks_file(self): pass

    @SingleResourceDefinition(BiomesClientFile)
    def biomes_client_file(self): pass

    @SingleResourceDefinition(TerrainTextureFile)
    def terrain_texture_file(self): pass

    @SingleResourceDefinition(ItemTextureFile)
    def item_texture_file(self): pass