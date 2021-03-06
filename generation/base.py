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

NO_ARGUMENT = object()

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

def convert_to_notify_structure(data: Union[dict, list], parent: Resource) -> Union[NotifyDict, NotifyList]:
    """
    Converts a dict or list to a notify structure.
    """
    if isinstance(data, dict):
        return NotifyDict(data, owner=parent)

    if isinstance(data, list):
        return NotifyList(data, owner=parent)

    return data

def smart_compare(a, b):
    """
    Compares to objects using ==, but if they can both be interpreted as
    path-like objects, it uses path comparison.
    """
    try:
        a = Path(a)
        b = Path(b)

        return a == b
    except Exception:
        return a == b

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

class NotifyDict(dict):
    """
    A notify dictionary is a dictionary that can notify its parent when its been
    edited.
    """
    def __init__(self, *args, owner: Resource = None, **kwargs):
        self.__owner = owner

        if len(args) > 0:
            for key, value in args[0].items():
                args[0][key] = convert_to_notify_structure(value, self.__owner)
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
        value = convert_to_notify_structure(value, self.__owner)

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
                args[0][i] = convert_to_notify_structure(args[0][i], self.__owner)

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
    
    def append(self, v):
        if(self.__owner != None):
            self.__owner.dirty = True
        super().append(v)

    def extend(self, v):
        if(self.__owner != None):
            self.__owner.dirty = True
        super().extend(v)

    def __setitem__(self, attr, value):
        value = convert_to_notify_structure(value, self.__owner)

        if self.__getitem__(attr) != value:
            if(self.__owner != None):
                self.__owner.dirty = True
        
        super().__setitem__(attr, value)

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
    Should not be used directly. Use JsonFileResource, or JsonSubResource instead.
    Contains:
     - Data object
     - Method for interacting with the data
    """

    def __init__(self, data: dict = None, file: FileResource = None, pack: Pack = None) -> None:
        super().__init__(file=file, pack=pack)
        self.data = convert_to_notify_structure(data, self)

    def _save(self):
        raise NotImplementedError("This json resource cannot be saved.")

    def _delete(self):
        raise NotImplementedError("This json resource cannot be deleted.")

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
            self.data = convert_to_notify_structure(data, self)
        else:
            self.data = convert_to_notify_structure(self.pack.load_json(self.file_path), self)

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

        # The parent of the sub-resource is the asset of type Resource
        # which owns this sub-resource. For example a Component is owned by
        # either an EntityFileBP, or a ComponentGroup.
        self.parent = parent

        # The jsonpath is the location within the parent resource, where
        # this sub-resource is stored.
        self.json_path = json_path

        # The ID is the "leaf name" of the subresources jsonpath.
        # For example a 'minecraft:scale' component has an ID of 
        # 'minecraft:scale', and a data of {'value': 1.0}
        self._id = self.get_id_from_jsonpath(json_path)

        # The data is the actual data of the sub-resource, minus the id.
        # For example a 'minecraft:scale' component has a data of {'value': 1.0}
        self.data = convert_to_notify_structure(data, self)

        # Internal list of resources that are children of this sub-resource.
        self._resources: JsonSubResource = []

        # Register self into parent, so that it can be found by the parent
        # during saving, etc.
        self.parent.register_resource(self)
    
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self.dirty = True
        self._id = id

    # TODO This feels wrong?
    def get_id_from_jsonpath(self, json_path):
        return json_path.split("/")[-1]

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

class ShortnameResourcePair(Resource):
    """
    A str:Resource pair, which is used to store assets by their shortname.

    Useful in cases such as EntityRP, where a shortname resource is paired
    with an identifier, which can be converted into a resource
    """
    def __init__(self, shortname: str, resource: Resource, file: FileResource = None, pack: Pack = None) -> None:
        super().__init__(file=FileResource, pack=pack)

        self.shortname = shortname
        self.resource = resource

    def __str__(self):
        return f'{self.shortname}'

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
        self.__commands = NotifyList(self.__commands, owner=self)
        return self.__commands

    def _is_dirty():
        pass
    
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