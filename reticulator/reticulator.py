from __future__ import annotations
from dataclasses import dataclass
import re
import os
import json
from pathlib import Path
import glob
from functools import cached_property
from io import TextIOWrapper
from typing import Union
from send2trash import send2trash
import copy
import dpath.util

# region globals

def create_nested_directory(path: str):
    """
    Creates a nested directory structure if it doesn't exist.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def freeze(o):
    """
    Makes a hash out of anything that contains only list,dict and hashable types
    including string and numeric types
    """
    if isinstance(o, dict):
        return frozenset({ k:freeze(v) for k,v in o.items()}.items())

    if isinstance(o,list):
        return tuple(freeze(v) for v in o)

    return hash(o)

#endregion
# region exceptions
class ReticulatorException(Exception):
    """
    Base class for Reticulator exceptions.
    """

class FloatingAssetError(ReticulatorException):
    """
    Called when a "floating" asset attempts to access its parent pack, for
    example when saving
    """

class AssetNotFoundError(ReticulatorException):
    """
    Called when attempting to access an asset that does not exist, for
    example getting an entity by name
    """

class AmbiguousAssetError(ReticulatorException):
    """
    Called when a path is not unique
    """
#endregion
# region notify classes

# TODO: Replace these with a hash-based edit-detection method?

class NotifyDict(dict):
    """
    A notify dictionary is a dictionary that can notify its parent when its been
    edited.
    """
    def __init__(self, *args, owner: Resource = None, **kwargs):
        self.__owner = owner

        if len(args) > 0:
            for key, value in args[0].items():
                if isinstance(value, dict):
                    args[0][key] = NotifyDict(value, owner=self.__owner)
                if isinstance(value, list):
                    args[0][key] = NotifyList(value, owner=self.__owner)
        super().__init__(*args, **kwargs)


    def get_item(self, attr):
        try:
            return self.__getitem__(attr)
        except:
            return None
    
    def __delitem__(self, v) -> None:
        if(self.__owner != None):
            self.__owner.dirty = True
        return super().__delitem__(v)

    def __setitem__(self, attr, value):
        if isinstance(value, dict):
            value = NotifyDict(value, owner=self.__owner)
        if isinstance(value, list):
            value = NotifyList(value, owner=self.__owner)

        if self.get_item(attr) != value:
            if(self.__owner != None):
                self.__owner.dirty = True

        super().__setitem__(attr, value)

class NotifyList(list):
    """
    A notify list is a list which can notify its owner when it has
    changed.
    """
    def __init__(self, *args, owner: Resource = None, **kwargs):
        self.__owner = owner

        if len(args) > 0:
            for i in range(len(args[0])):
                if isinstance(args[0][i], dict):
                    args[0][i] = NotifyDict(args[0][i], owner=self.__owner)
                if isinstance(args[0][i], list):
                    args[0][i] = NotifyList(args[0][i], owner=self.__owner)

        super().__init__(*args, **kwargs)

    def get_item(self, attr):
        try:
            return self.__getitem__(attr)
        except:
            return None

    def __setitem__(self, attr, value):
        if isinstance(value, dict):
            value = NotifyDict(value, owner=self.__owner)
        if isinstance(value, list):
            value = NotifyList(value, owner=self.__owner)

        if self.__getitem__(attr) != value:
            if(self.__owner != None):
                self.__owner.dirty = True
        
        super().__setitem__(attr, value)

# endregion

NO_ARGUMENT = object()

class Resource():
    """
    The top resource in the inheritance chain.

    Contains:
     - reference to the Pack (could be blank, if floating resource)
     - reference to the File (could be a few links up the chain)
     - dirty status
     - abstract ability to save
     - list of children resources
    """

    def __init__(self, file: FileResource = None, pack: Pack = None) -> None:
        # Public
        self.pack = pack
        self.file = file
        self._dirty = False

        # Private
        self._resources: Resource = []

    @property
    def dirty(self):
        """
        Whether the asset is dirty (has been edited).
        """
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty

    def register_resource(self, resource):
        """
        Register a child resource. These resources will always be saved first.
        """
        self._resources.append(resource)

    def _should_save(self):
        """
        Whether the asset can be saved.
        By default, this is related to dirty status

        Can be overridden by subclasses.
        """
        return self.dirty

    def _should_delete(self):
        """
        Whether the asset can be deleted.

        By default, returns true.
        """
        return True

    def _save(self):
        """
        Internal implementation of asset saving.

        Should always be implemented.
        """
        raise NotImplementedError()

    def _delete(self):
        """
        Internal implementation of asset deletion.

        Should always be implemented.
        """
        raise NotImplementedError()


    def save(self, force=False):
        """
        Saves the resource. Should not be overridden.

        This method will save all child resources first, by calling
        the internal _save implementation.
        """

        # TODO Maybe only files need this check?
        # Assets without packs may not save.
        if not self.pack:
            raise FloatingAssetError("Assets without a pack cannot be saved.")

        if self._should_save() or force:
            self.dirty = False

            # Save all children first
            for resource in self._resources:
                resource.save(force=force)

            # Now, save this resource
            self._save()

    def delete(self, force=False):
        """
        Deletes the resource. Should not be overridden.
        """

        # TODO: Does deletion really need to be recursive?
        if self._should_delete() or force:
            # First, delete all resources of children
            for resource in self._resources:
                resource.delete(force=force)

            # Then delete self
            self._delete()

            # TODO Do we need to call save here?

class FileResource(Resource):
    """
    A resource, which is also a file.
    Contains:
     - File path
     - ability to mark for deletion
    """
    def __init__(self, file_path: str = None, pack: Pack = None) -> None:
        # Initialize resource
        super().__init__(file=self, pack=pack)

        # All files must register themselves with their pack
        # if the pack exists.
        if self.pack:
            pack.register_resource(self)

        # Public
        self.file_path = file_path

        if file_path:
            self.file_name = os.path.basename(file_path)

        # Protected
        self._hash = self._create_hash()
        self._mark_for_deletion: bool = False

    def _delete(self):
        """
        Internal implementation of file deletion.

        Marking for deletion allows us to delete the file during saving,
        without effecting the file system during normal operation.
        """
        self._mark_for_deletion = True

    def _should_delete(self):
        return not self._mark_for_deletion and super()._should_delete()

    def _should_save(self):
        # Files that have been deleted cannot be saved
        if self._mark_for_deletion:
            return False

        return self._hash != self._create_hash() or super()._should_save()

    def _create_hash(self):
        """
        Creates a hash for the file.

        If a file doesn't want to implement a hash, then the file will always
        be treated as the same, allowing other checks to take control.
        """
        return 0

    def _save(self):
        raise NotImplementedError("This file has not implemented a save method.")

class JsonResource(Resource):
    """
    Parent class, which is responsible for all resources which contain
    json data.
    Should not be used directly. Use should JsonFileResource, or JsonSubResource.
    Contains:
     - Data object
     - Method for interacting with the data
    """

    def __init__(self, data: dict = None, file: FileResource = None, pack: Pack = None) -> None:
        super().__init__(file=file, pack=pack)
        self.data = self.convert_to_notify(data)

    def _save(self):
        raise NotImplementedError("This json resource cannot be saved.")

    def _delete(self):
        raise NotImplementedError("This json resource cannot be deleted.")

    def convert_to_notify(self, raw_data):
        if isinstance(raw_data, dict):
            return NotifyDict(raw_data, owner=self)

        if isinstance(raw_data, list):
            return NotifyList(raw_data, owner=self)

        return raw_data

    def __str__(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False)


    def jsonpath_exists(self, json_path:str) -> bool:
        """
        Checks if a jsonpath exists
        """
        try:
            self.get_jsonpath(json_path)
            return True
        except AssetNotFoundError:
            return False

    def delete_jsonpath(self, json_path:str, ensure_exists:bool = False) -> None:
        """
        Removes value at jsonpath location.
        """
        path_exists = self.jsonpath_exists(json_path)
        if path_exists:
            dpath.util.delete(self.data, json_path)
        elif ensure_exists:
            raise AssetNotFoundError(f"Path {json_path} does not exist. Cannot delete.")

    def pop_jsonpath(self, json_path, default=NO_ARGUMENT, ensure_exists=False) \
        -> Union[dict, list, int, str, float]:
        """
        Removes value at jsonpath location, and returns it.
        """

        data = self.get_jsonpath(json_path, default=default)
        self.delete_jsonpath(json_path, ensure_exists=ensure_exists)
        return data

    def set_jsonpath(self, json_path:str, insert_value:any, must_exist:bool=False, overwrite:bool=True):
        """
        Sets value at jsonpath location.

        Can create a new key if it doesn't exist.
        """

        path_exists = self.jsonpath_exists(json_path)

        # If the path must exist, and is missing, we can
        # raise an error by getting the path
        if not path_exists and must_exist:
            raise AssetNotFoundError(f"Path {json_path} does not exist. Cannot set value.")

        # If overwrite is false, it will set the path only
        # if there is no path.
        if path_exists and not overwrite:
            return

        # Otherwise, set the value
        dpath.util.new(self.data, json_path, insert_value)

    def get_jsonpath(self, json_path, default=NO_ARGUMENT):
        """
        Gets value at jsonpath location.

        A default value may be provided, for missing keys.

        raises:
            AssetNotFoundError if the path does not exist.
        """
        try:
            return dpath.util.get(self.data, json_path)
        except Exception as exception:
            if default is not NO_ARGUMENT:
                return default
            raise AssetNotFoundError(
                f"Path {json_path} does not exist."
            ) from exception

    # TODO: Rewrite this to not suck
    # Gets a list of values found at this jsonpath location
    def get_data_at(self, json_path):
        try:
            # Get Data at has a special syntax, to make it clear you are getting a list
            if not json_path.endswith("*"):
                raise AmbiguousAssetError('Data get must end with *', json_path)
            json_path = json_path[:-2]

            result = self.get_jsonpath(json_path, default=[])

            if isinstance(result, dict):
                for key in result.keys():
                    yield json_path + f"/{key}", result[key]
            elif isinstance(result, list):
                for i, element in enumerate(result):
                    yield json_path + f"/[{i}]", element
            else:
                raise AmbiguousAssetError('get_data_at found a single element, not a list or dict.', json_path)

        except KeyError as key_error:
            raise AssetNotFoundError(json_path, self.data) from key_error

class JsonFileResource(FileResource, JsonResource):
    """
    A file, which contains json data. Most files in the addon system
    are of this type, or have it as a resource parent.
    """
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        # Init file resource parent, which gives us access to data
        FileResource.__init__(self, file_path=file_path, pack=pack)
        
        # Data is either set directly, or is read from the filepath for this
        # resource. This allows assets to be created from scratch, whilst
        # still having an associated file location.
        if data is not None:
            self.data = NotifyDict(data, owner=self)
        else:
            self.data = NotifyDict(self.pack.load_json(self.file_path), owner=self)

        # Init json resource, which relies on the new data attribute
        JsonResource.__init__(self, data=self.data, file=self, pack=pack)

    def _save(self):
        self.pack.save_json(self.file_path, self.data)

    def _delete(self):
        self._mark_for_deletion = True

    def _create_hash(self):
        return freeze(self.data)

class JsonSubResource(JsonResource):
    """
    A sub resource represents a chunk of json data, within a file.
    """
    def __init__(self, parent: Resource = None, json_path: str = None, data: dict = None) -> None:
        super().__init__(data = data, pack = parent.pack, file = parent.file)
        self.parent = parent
        self.json_path = json_path
        self.id = self.get_id_from_jsonpath(json_path)
        self.data = self.convert_to_notify(data)
        self._resources: JsonSubResource = []
        self.parent.register_resource(self)
    
    # TODO This feels wrong?
    def get_id_from_jsonpath(self, json_path):
        return json_path.split("/")[-1]

    def convert_to_notify(self, raw_data):
        if isinstance(raw_data, dict):
            return NotifyDict(raw_data, owner=self)

        if isinstance(raw_data, list):
            return NotifyList(raw_data, owner=self)

        return raw_data

    def __str__(self):
        """
        Returns string representation of this resource.

        The json data will be representation for printing: With the id appended,
        and with indentation.
        """
        return f'"{self.id}": {json.dumps(self.data, indent=2, ensure_ascii=False)}'

    @property
    def dirty(self):
        """
        Returns True if this resource has been modified since it was last saved.
        """
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        """
        Set the dirty flag, which stores whether this resource has been 
        modified since it was last saved.
        """
        self._dirty = dirty
        self.parent.dirty = dirty

    def register_resource(self, resource: JsonSubResource) -> None:
        """
        Register a child resource within this resource.
        """
        self._resources.append(resource)

    def _save(self):
        """
        Saves the resource, into its parents json structure.

        This works by replacing the data at the jsonpath location,
        meaning that the parent will contain accurate representation of
        the childrends data, saved into itself.
        """
        self.parent.set_jsonpath(self.json_path, self.data)
        self._dirty = False

    def _delete(self):
        """
        Deletes itself from parent, by removing the data at the jsonpath
        location.
        """
        self.parent.dirty = True
        self.parent.delete_jsonpath(self.json_path)

@dataclass
class Translation:
    """
    Dataclass for a translation. Many translations together make up a
    TranslationFile.
    """
    key: str
    value: str
    comment: str

class FunctionFile(FileResource):
    """
    A FunctionFile is a function file, such as run.mcfunction, and is
    made up of many commands.
    """
    def __init__(self, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(file_path=file_path, pack=pack)
        self.__commands : list[str] = []
    
    @cached_property
    def commands(self) -> list[str]:
        with open(os.path.join(self.pack.input_path, self.file_path), "r", encoding='utf-8') as function_file:
            for line in function_file.readlines():
                if line.strip() and not line.startswith("#"):
                    self.__commands.append(line)
        return self.__commands

    def _save(self):
        path = os.path.join(self.pack.output_path, self.file_path)
        create_nested_directory(path)
        with open(path, 'w', encoding='utf-8') as file:
            for command in self.commands:
                file.write(command)

class LanguageFile(FileResource):
    """
    A LanguageFile is a language file, such as 'en_US.lang', and is made
    up of many Translations.
    """
    def __init__(self, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(file_path=file_path, pack=pack)
        self.__translations: list[Translation] = []

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

        # We must complain about duplicates, unless
        if self.contains_translation(translation.key) and not overwrite:
            return False

        self.dirty = True
        self.__translations.append(translation)

        return True

    def _save(self):
        path = os.path.join(self.pack.output_path, self.file_path)
        create_nested_directory(path)
        with open(path, 'w', encoding='utf-8') as file:
            for translation in self.translations:
                file.write(f"{translation.key}={translation.value}\t##{translation.comment}\n")

    @cached_property
    def translations(self) -> list[Translation]:
        with open(os.path.join(self.pack.input_path, self.file_path), "r", encoding='utf-8') as language_file:
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


class Pack():
    """
    A pack is a holder class for many file assets. 
    """
    def __init__(self, input_path: str, project=None):
        self.resources = []
        self.__language_files = []
        self.__project = project
        self.input_path = input_path
        self.output_path = input_path

    @cached_property
    def project(self) -> Project:
        """
        Get the project that this pack is part of. May be None.
        """
        return self.__project

    def set_output_location(self, output_path: str) -> None:
        """
        The output location will be used when saving, to determine where files
        will be exported.
        """
        self.output_path = output_path

    def load_json(self, local_path: str) -> dict:
        """
        Loads json from file. `local_path` paramater is local to the projects
        input path.
        """
        return self.get_json_from_path(os.path.join(self.input_path, local_path))

    def save_json(self, local_path, data):
        """
        Saves json to file. 'local_path' paramater is local to the projects
        output path.
        """
        return self.__save_json(os.path.join(self.output_path, local_path), data)

    def delete_file(self, local_path):
        # TODO: Why is this local to output path? Why does this except pass?
        try:
            send2trash(os.path.join(self.output_path, local_path))
        except:
            pass

    def save(self, force=False):
        """
        Saves every child resource.
        """
        for resource in self.resources:
            resource.save(force=force)

    def register_resource(self, resource):
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

    def get_language_file(self, file_name:str) -> LanguageFile:
        """
        Gets a specific language file, based on the name of the language file.
        For example, 'en_GB.lang'
        """
        for language_file in self.language_files:
            if language_file.file_name == file_name:
                return language_file
        raise AssetNotFoundError(file_name)

    @cached_property
    def language_files(self) -> list[LanguageFile]:
        """
        Returns a list of LanguageFiles, as read from 'texts/*'
        """
        base_directory = os.path.join(self.input_path, "texts")
        for local_path in glob.glob(base_directory + "/**/*.lang", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__language_files.append(LanguageFile(file_path = local_path, pack = self))
            
        return self.__language_files

    ## TODO: Move these static methods OUT
    @staticmethod
    def get_json_from_path(path:str) -> dict:
        with open(path, "r", encoding='utf8') as fh:
            return Pack.__get_json_from_file(fh)

    @staticmethod
    def __get_json_from_file(fh:TextIOWrapper) -> dict:
        """
        Loads json from file. First attempts to load with fast json.load method,
        but if this fails, a custom comment-aware scraper is used.
        """
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            try:
                fh.seek(0)
                contents = ""
                for line in fh.readlines():
                    cleaned_line = line.split("//", 1)[0]
                    if len(cleaned_line) > 0 and line.endswith("\n") and "\n" not in cleaned_line:
                        cleaned_line += "\n"
                    contents += cleaned_line
                while "/*" in contents:
                    pre_comment, post_comment = contents.split("/*", 1)
                    contents = pre_comment + post_comment.split("*/", 1)[1]
                return json.loads(contents)
            except json.JSONDecodeError as exception:
                print(exception)
                return {}

    @staticmethod
    def __save_json(file_path, data):
        """
        Saves json to a file_path, creating nested directory if required.
        """
        create_nested_directory(file_path)

        with open(file_path, "w+") as file_head:
            return json.dump(data, file_head, indent=2, ensure_ascii=False)

class Project():
    """
    A Project is a holder class which contains reference to both a single
    rp, and a single bp.
    """
    def __init__(self, behavior_path: str, resource_path: str):
        self.__behavior_path = behavior_path
        self.__resource_path = resource_path
        self.__resource_pack = None
        self.__behavior_pack : BehaviorPack = None

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

# Forward Declares, to keep pylint from shouting.
class BehaviorPack(Pack): pass
class ResourcePack(Pack): pass
class ResourcePack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__particles = []
        self.__attachables = []
        self.__animation_controller_files = []
        self.__animation_files = []
        self.__entities = []
        self.__model_files = []
        self.__render_controller_files = []
        self.__items = []
        
    
    @cached_property
    def particles(self) -> list[ParticleFileRP]:
        base_directory = os.path.join(self.input_path, "particles")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__particles.append(ParticleFileRP(file_path = local_path, pack = self))
            
        return self.__particles

    @cached_property
    def attachables(self) -> list[AttachableFileRP]:
        base_directory = os.path.join(self.input_path, "attachables")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__attachables.append(AttachableFileRP(file_path = local_path, pack = self))
            
        return self.__attachables

    @cached_property
    def animation_controller_files(self) -> list[AnimationControllerFileRP]:
        base_directory = os.path.join(self.input_path, "animation_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_controller_files.append(AnimationControllerFileRP(file_path = local_path, pack = self))
            
        return self.__animation_controller_files

    @cached_property
    def animation_files(self) -> list[AnimationFileRP]:
        base_directory = os.path.join(self.input_path, "animations")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_files.append(AnimationFileRP(file_path = local_path, pack = self))
            
        return self.__animation_files

    @cached_property
    def entities(self) -> list[EntityFileRP]:
        base_directory = os.path.join(self.input_path, "entity")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityFileRP(file_path = local_path, pack = self))
            
        return self.__entities

    @cached_property
    def model_files(self) -> list[ModelFileRP]:
        base_directory = os.path.join(self.input_path, "models")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__model_files.append(ModelFileRP(file_path = local_path, pack = self))
            
        return self.__model_files

    @cached_property
    def render_controller_files(self) -> list[RenderControllerFileRP]:
        base_directory = os.path.join(self.input_path, "render_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__render_controller_files.append(RenderControllerFileRP(file_path = local_path, pack = self))
            
        return self.__render_controller_files

    @cached_property
    def items(self) -> list[ItemFileRP]:
        base_directory = os.path.join(self.input_path, "items")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__items.append(ItemFileRP(file_path = local_path, pack = self))
            
        return self.__items

    
    @cached_property
    def render_controllers(self) -> list[RenderControllerRP]:
        children = []
        for file in self.render_controller_files:
            for child in file.render_controllers:
                children.append(child)
        return children

    @cached_property
    def animation_controllers(self) -> list[AnimationControllerRP]:
        children = []
        for file in self.animation_controller_files:
            for child in file.animation_controllers:
                children.append(child)
        return children

    @cached_property
    def models(self) -> list[Model]:
        children = []
        for file in self.model_files:
            for child in file.models:
                children.append(child)
        return children

    
    def get_particle(self, identifier:str) -> ParticleFileRP:
        for child in self.particles:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_attachable(self, identifier:str) -> AttachableFileRP:
        for child in self.attachables:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_animation_controller_file(self, file_name:str) -> AnimationControllerFileRP:
        for child in self.animation_controller_files:
            if child.file_name == file_name:
                return child
        raise AssetNotFoundError(file_name)

    def get_animation_file(self, file_name:str) -> AnimationFileRP:
        for child in self.animation_files:
            if child.file_name == file_name:
                return child
        raise AssetNotFoundError(file_name)

    def get_entity(self, identifier:str) -> EntityFileRP:
        for child in self.entities:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_model_file(self, file_name:str) -> ModelFileRP:
        for child in self.model_files:
            if child.file_name == file_name:
                return child
        raise AssetNotFoundError(file_name)

    def get_render_controller_file(self, file_name:str) -> RenderControllerFileRP:
        for child in self.render_controller_files:
            if child.file_name == file_name:
                return child
        raise AssetNotFoundError(file_name)

    
    def get_render_controller(self, id:str) -> RenderControllerRP:
        for file_child in self.render_controller_files:
            for child in file_child.render_controllers:
                if child.id == id:
                    return child
        raise AssetNotFoundError(id)

    def get_animation_controller(self, id:str) -> AnimationControllerRP:
        for file_child in self.animation_controller_files:
            for child in file_child.animation_controllers:
                if child.id == id:
                    return child
        raise AssetNotFoundError(id)

    def get_model(self, identifier:str) -> Model:
        for file_child in self.model_files:
            for child in file_child.models:
                if child.identifier == identifier:
                    return child
        raise AssetNotFoundError(identifier)

    
class BehaviorPack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__functions = []
        self.__features_file = []
        self.__feature_rules_files = []
        self.__spawn_rules = []
        self.__recipes = []
        self.__entities = []
        self.__animation_controller_files = []
        self.__loot_tables = []
        self.__items = []
        self.__blocks = []
        
    
    @cached_property
    def functions(self) -> list[FunctionFile]:
        base_directory = os.path.join(self.input_path, "functions")
        for local_path in glob.glob(base_directory + "/**/*.mcfunction", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__functions.append(FunctionFile(file_path = local_path, pack = self))
            
        return self.__functions

    @cached_property
    def features_file(self) -> list[FeatureFileBP]:
        base_directory = os.path.join(self.input_path, "features")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__features_file.append(FeatureFileBP(file_path = local_path, pack = self))
            
        return self.__features_file

    @cached_property
    def feature_rules_files(self) -> list[FeatureRulesFileBP]:
        base_directory = os.path.join(self.input_path, "feature_rules")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__feature_rules_files.append(FeatureRulesFileBP(file_path = local_path, pack = self))
            
        return self.__feature_rules_files

    @cached_property
    def spawn_rules(self) -> list[SpawnRuleFile]:
        base_directory = os.path.join(self.input_path, "spawn_rules")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__spawn_rules.append(SpawnRuleFile(file_path = local_path, pack = self))
            
        return self.__spawn_rules

    @cached_property
    def recipes(self) -> list[RecipeFile]:
        base_directory = os.path.join(self.input_path, "recipes")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__recipes.append(RecipeFile(file_path = local_path, pack = self))
            
        return self.__recipes

    @cached_property
    def entities(self) -> list[EntityFileBP]:
        base_directory = os.path.join(self.input_path, "entities")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityFileBP(file_path = local_path, pack = self))
            
        return self.__entities

    @cached_property
    def animation_controller_files(self) -> list[AnimationControllerFileRP]:
        base_directory = os.path.join(self.input_path, "animation_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_controller_files.append(AnimationControllerFileRP(file_path = local_path, pack = self))
            
        return self.__animation_controller_files

    @cached_property
    def loot_tables(self) -> list[LootTableFile]:
        base_directory = os.path.join(self.input_path, "loot_tables")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__loot_tables.append(LootTableFile(file_path = local_path, pack = self))
            
        return self.__loot_tables

    @cached_property
    def items(self) -> list[ItemFileBP]:
        base_directory = os.path.join(self.input_path, "items")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__items.append(ItemFileBP(file_path = local_path, pack = self))
            
        return self.__items

    @cached_property
    def blocks(self) -> list[BlockFileBP]:
        base_directory = os.path.join(self.input_path, "blocks")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__blocks.append(BlockFileBP(file_path = local_path, pack = self))
            
        return self.__blocks

    
    
    def get_function(self, file_path:str) -> FunctionFile:
        for child in self.functions:
            if child.file_path == file_path:
                return child
        raise AssetNotFoundError(file_path)

    def get_feature_rules_file(self, identifier:str) -> FeatureRulesFileBP:
        for child in self.feature_rules_files:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_spawn_rule(self, identifier:str) -> SpawnRuleFile:
        for child in self.spawn_rules:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_recipe(self, identifier:str) -> RecipeFile:
        for child in self.recipes:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_entity(self, identifier:str) -> EntityFileBP:
        for child in self.entities:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_item(self, identifier:str) -> ItemFileBP:
        for child in self.items:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_block(self, identifier:str) -> BlockFileBP:
        for child in self.blocks:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    
    
class FeatureFileBP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        
    
    
    
    
    
class RecipeFile(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("**/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("**/identifier", identifier)

    
    
    
    
class ParticleFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__components = []
        self.__events = []
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    @property
    def identifier(self):
        return self.get_jsonpath("particle_effect/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("particle_effect/description/identifier", identifier)

    
    @cached_property
    def components(self) -> list[JsonSubResource]:
        for path, data in self.get_data_at("particle_effect/components/*"):
            self.__components.append(JsonSubResource(parent = self, json_path = path, data = data))
        return self.__components
    
    @cached_property
    def events(self) -> list[JsonSubResource]:
        for path, data in self.get_data_at("particle_effect/events/*"):
            self.__events.append(JsonSubResource(parent = self, json_path = path, data = data))
        return self.__events
    
    
    def get_component(self, id:str) -> JsonSubResource:
        for child in self.components:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    def get_event(self, id:str) -> JsonSubResource:
        for child in self.events:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    
class AttachableFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:attachable/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:attachable/description/identifier", identifier)

    
    
    
    
class FeatureRulesFileBP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:feature_rules/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:feature_rules/description/identifier", identifier)

    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    
    
    
class RenderControllerFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__render_controllers = []
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    @cached_property
    def render_controllers(self) -> list[RenderControllerRP]:
        for path, data in self.get_data_at("render_controllers/*"):
            self.__render_controllers.append(RenderControllerRP(parent = self, json_path = path, data = data))
        return self.__render_controllers
    
    
    def get_render_controller(self, id:str) -> RenderControllerRP:
        for child in self.render_controllers:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    
class AnimationControllerFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__animation_controllers = []
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    @cached_property
    def animation_controllers(self) -> list[AnimationControllerRP]:
        for path, data in self.get_data_at("animation_controllers/*"):
            self.__animation_controllers.append(AnimationControllerRP(parent = self, json_path = path, data = data))
        return self.__animation_controllers
    
    
    def get_animation_controller(self, id:str) -> AnimationControllerRP:
        for child in self.animation_controllers:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    
class SpawnRuleFile(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:spawn_rules/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:spawn_rules/description/identifier", identifier)

    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    
    
    
class LootTableFile(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__pools = []
        
    
    
    @cached_property
    def pools(self) -> list[LootTablePool]:
        for path, data in self.get_data_at("pools/*"):
            self.__pools.append(LootTablePool(parent = self, json_path = path, data = data))
        return self.__pools
    
    
    
    
class ItemFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__components = []
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:item/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:item/description/identifier", identifier)

    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    @cached_property
    def components(self) -> list[Component]:
        for path, data in self.get_data_at("minecraft:item/components/*"):
            self.__components.append(Component(parent = self, json_path = path, data = data))
        return self.__components
    
    
    
    
class ItemFileBP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__components = []
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:item/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:item/description/identifier", identifier)

    
    @cached_property
    def components(self) -> list[Component]:
        for path, data in self.get_data_at("minecraft:item/components"):
            self.__components.append(Component(parent = self, json_path = path, data = data))
        return self.__components
    
    
    
    
class BlockFileBP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__components = []
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:block/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:block/description/identifier", identifier)

    
    @cached_property
    def components(self) -> list[Component]:
        for path, data in self.get_data_at("minecraft:block/components"):
            self.__components.append(Component(parent = self, json_path = path, data = data))
        return self.__components
    
    
    
    
class EntityFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__animations = []
        
    
    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:client_entity/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:client_entity/description/identifier", identifier)

    
    @cached_property
    def animations(self) -> list[AnimationRP]:
        for path, data in self.get_data_at("minecraft:client_entity/description/animations/*"):
            self.__animations.append(AnimationRP(parent = self, json_path = path, data = data))
        return self.__animations
    
    
    
    
class AnimationFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__animations = []
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    
    @cached_property
    def animations(self) -> list[AnimationRP]:
        for path, data in self.get_data_at("animations/*"):
            self.__animations.append(AnimationRP(parent = self, json_path = path, data = data))
        return self.__animations
    
    
    
    
class EntityFileBP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__component_groups = []
        self.__components = []
        self.__events = []
        
    
    @property
    def format_version(self):
        return self.get_jsonpath("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        return self.set_jsonpath("format_version", format_version)

    @property
    def identifier(self):
        return self.get_jsonpath("minecraft:entity/description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("minecraft:entity/description/identifier", identifier)

    
    @cached_property
    def component_groups(self) -> list[ComponentGroup]:
        for path, data in self.get_data_at("minecraft:entity/component_groups/*"):
            self.__component_groups.append(ComponentGroup(parent = self, json_path = path, data = data))
        return self.__component_groups
    
    @cached_property
    def components(self) -> list[Component]:
        for path, data in self.get_data_at("minecraft:entity/components/*"):
            self.__components.append(Component(parent = self, json_path = path, data = data))
        return self.__components
    
    @cached_property
    def events(self) -> list[Event]:
        for path, data in self.get_data_at("minecraft:entity/events/*"):
            self.__events.append(Event(parent = self, json_path = path, data = data))
        return self.__events
    
    
    def get_component_group(self, id:str) -> ComponentGroup:
        for child in self.component_groups:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    def get_component(self, id:str) -> Component:
        for child in self.components:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    def create_component_group(self, name: str, data: dict) -> ComponentGroup:
        self.set_jsonpath("minecraft:entity/component_groups/" + name, data)
        new_object = ComponentGroup(self, "minecraft:entity/component_groups/." + name, data)
        self.__component_groups.append(new_object)
        return new_object

    def create_component(self, name: str, data: dict) -> Component:
        self.set_jsonpath("minecraft:entity/components/" + name, data)
        new_object = Component(self, "minecraft:entity/components/." + name, data)
        self.__components.append(new_object)
        return new_object

    
class ModelFileRP(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        self.__models = []
        
    
    
    @cached_property
    def models(self) -> list[Model]:
        for path, data in self.get_data_at("minecraft:geometry/*"):
            self.__models.append(Model(parent = self, json_path = path, data = data))
        return self.__models
    
    
    
    
class RenderControllerRP(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        
    
    
    
    
    
class Cube(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        
    
    
    
    
    
class LootTablePool(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        
    
    
    
    
    
class AnimationControllerStateRP(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        
    
    
    
    
    
class AnimationControllerRP(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__states = []
        
    
    @cached_property
    def states(self) -> list[AnimationControllerStateRP]:
        for path, data in self.get_data_at("states/*"):
            self.__states.append(AnimationControllerStateRP(parent = self, json_path = path, data = data))
        return self.__states
    
    
    @property
    def initial_state(self):
        return self.get_jsonpath("initial_state")
    
    @initial_state.setter
    def initial_state(self, initial_state):
        return self.set_jsonpath("initial_state", initial_state)

    
    def get_state(self, id:str) -> AnimationControllerStateRP:
        for child in self.states:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    
class Model(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__bones = []
        
    
    @cached_property
    def bones(self) -> list[Bone]:
        for path, data in self.get_data_at("bones/*"):
            self.__bones.append(Bone(parent = self, json_path = path, data = data))
        return self.__bones
    
    
    @property
    def identifier(self):
        return self.get_jsonpath("description/identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        return self.set_jsonpath("description/identifier", identifier)

    
    
    
class AnimationRP(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__bones = []
        
    
    @cached_property
    def bones(self) -> list[JsonSubResource]:
        for path, data in self.get_data_at("bones"):
            self.__bones.append(JsonSubResource(parent = self, json_path = path, data = data))
        return self.__bones
    
    
    @property
    def loop(self):
        return self.get_jsonpath("loop")
    
    @loop.setter
    def loop(self, loop):
        return self.set_jsonpath("loop", loop)

    
    
    
class ComponentGroup(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__components = []
        
    
    @cached_property
    def components(self) -> list[Component]:
        for path, data in self.get_data_at("*"):
            self.__components.append(Component(parent = self, json_path = path, data = data))
        return self.__components
    
    
    
    
    def create_component(self, name: str, data: dict) -> Component:
        self.set_jsonpath("" + name, data)
        new_object = Component(self, "." + name, data)
        self.__components.append(new_object)
        return new_object

    
class Component(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None , component_group: ComponentGroup = None) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        
    
    
    
    
    
class Event(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__groups_to_add = []
        self.__groups_to_remove = []
        
    
    @cached_property
    def groups_to_add(self) -> list[ComponentGroup]:
        for path, data in self.get_data_at("add/component_groups/*"):
            self.__groups_to_add.append(ComponentGroup(parent = self, json_path = path, data = data))
        return self.__groups_to_add
    
    @cached_property
    def groups_to_remove(self) -> list[ComponentGroup]:
        for path, data in self.get_data_at("remove/component_groups/*"):
            self.__groups_to_remove.append(ComponentGroup(parent = self, json_path = path, data = data))
        return self.__groups_to_remove
    
    
    
    
    
class Bone(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None ) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        
        self.__cubes = []
        
    
    @cached_property
    def cubes(self) -> list[Cube]:
        for path, data in self.get_data_at("cubes/*"):
            self.__cubes.append(Cube(parent = self, json_path = path, data = data))
        return self.__cubes
    
    
    
    
    