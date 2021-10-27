from __future__ import annotations
from dataclasses import dataclass
import re
import os
import json
from pathlib import Path
import glob
from functools import cached_property
from io import TextIOWrapper
from send2trash import send2trash
import copy
import dpath.util

# Constants

DOT_MATCHER_REGEX = re.compile(r"\.(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)")

# Globals

def create_nested_directory(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def freeze(o):
    if isinstance(o,dict):
        return frozenset({ k:freeze(v) for k,v in o.items()}.items())

    if isinstance(o,list):
        return tuple([freeze(v) for v in o])
    
    return o


def make_hash(o):
    """
    makes a hash out of anything that contains only list,dict and hashable types including string and numeric types
    """
    return hash(freeze(o))

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
        self.__resources: Resource = []

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty

    def register_resource(self, resource):
        """
        Register a child resource. These resources will always be saved first.
        """
        self.__resources.append(resource)

    def _should_save(self):
        """
        Whether the asset can be saved.
        By default, this is related to dirty status
        """
        return self.dirty

    def _should_delete(self):
        return True

    def _save(self, force=False):
        """
        Internal implementation of asset saving.
        
        Should always be implemented.
        """
        raise NotImplementedError()

    def _delete(self, force=False):
        """Internal implementation for asset deletion."""
        raise NotImplementedError()


    def save(self, force=False):
        """
        Save the resource. Should not be overridden.
        """

        # Assets without packs may not save.
        if not self.pack:
            raise FloatingAssetError()

        if self._should_save() or force:
            self.dirty = False
            for resource in self.__resources:
                resource.save(force=force)

            # Internal save handling
            self._save(force=force)
            self.dirty = False

    def delete(self, force=False):
        """
        Deletes the resource. Should not be overridden.
        """

        if self._should_delete() or force:
            # First, delete all resources of children
            for resource in self.__resources:
                resource.delete(force=force)

            # Then delete self
            self._delete(force=force)

            # Then save, respecting points where files may not want to save
            # TODO: Should we force? Or call .save() directly?
            self.save(force=force)

class FileResource(Resource):
    """
    A resource, which is also a file.
    Contains:
     - File path
     - ability to mark for deletion
    """
    def __init__(self, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(file=self, pack=pack)
        
        # All files must register with their pack
        self.pack.register_resource(self)
        
        # Public
        self.file_path = file_path

        if file_path:
            self.file_name = os.path.basename(file_path)

        # Protected
        self.__hash = self._create_hash()

        # Private
        self.__mark_for_deletion: bool = False

    # Deletion does not actually delete, but rather just prevents saving
    def _delete(self, force = False):
        self.__mark_for_deletion = True

    def _should_delete(self):
        return not self.__mark_for_deletion and super()._should_delete()

    def _should_save(self):
        # Files that have been deleted cannot be saved
        if self.__mark_for_deletion:
            return False

        return self.__hash != self._create_hash() or super()._should_save()

    def _create_hash(self):
        # If a file doesn't want to implement a hash, then the file will always
        # be treated as the same, allowing other checks to take control.
        return 0

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

    def convert_to_notify(self, raw_data):
        if isinstance(raw_data, dict):
            return NotifyDict(raw_data, owner=self)

        if isinstance(raw_data, list):
            return NotifyList(raw_data, owner=self)
        
        return raw_data

    def __str__(self):
        return json.dumps(self.data, indent=2, ensure_ascii=False)

    # TODO: Add some kind of trycatch for these methods

    # Removes value at jsonpath location
    def remove_value_at(self, json_path):
        dpath.util.delete(self.data, json_path)

    def pop_value_at(self, json_path):
        data = dpath.util.get(self.data, json_path)
        dpath.util.delete(self.data, json_path)
        return data

    # Sets value at jsonpath location
    def set_value_at(self, json_path, insert_value: any):
        dpath.util.set(self.data, json_path, insert_value)

    # Gets value at jsonpath location
    def get_value_at(self, json_path):
        return dpath.util.get(self.data, json_path)

    # Gets a list of values found at this jsonpath location
    def get_data_at(self, json_path):
        try:
            # Get Data at has a special syntax, to make it clear you are getting a list
            if not json_path.endswith("*"):
                raise AmbiguousAssetError('Data get must end with *', json_path)
            json_path = json_path[:-2]

            result = self.get_value_at(json_path)
            
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
        FileResource.__init__(self, file_path=file_path, pack=pack)
        
        if data != None:
            self.data = NotifyDict(data, owner=self)
        else:
            self.data = NotifyDict(self.pack.load_json(self.file_path), owner=self)

        JsonResource.__init__(self, data=self.data, file=self, pack=pack)


    def _save(self, force):
        self.pack.save_json(self.file_path, self.data)

    def delete(self):
        self.__mark_for_deletion = True

    def _create_hash(self):
        return make_hash(self.data)

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
        self.__resources: JsonSubResource = []
        self.parent.register_resource(self)


    def get_id_from_jsonpath(self, json_path):
        return json_path.split("/")[-1]


    def convert_to_notify(self, raw_data):
        if isinstance(raw_data, dict):
            return NotifyDict(raw_data, owner=self)
        if isinstance(raw_data, list):
            return NotifyList(raw_data, owner=self)
        else:
            return raw_data

    def __str__(self):
        return f'"{self.id}": {json.dumps(self.data, indent=2, ensure_ascii=False)}'

    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty
        self.parent.dirty = dirty

    def register_resource(self, resource: JsonSubResource) -> None:
        self.__resources.append(resource)
        
    def save(self, force=False):
        if self._dirty or force:
            for resource in self.__resources:
                resource.save(force=force)
            
            self.set_value_at(self.json_path, self.parent.data, self.data)
            self._dirty = False

    def delete(self):
        self.parent.dirty = True
        self.parent.remove_value_at(self.json_path)

@dataclass
class Translation:
    key: str
    value: str
    comment: str

class LanguageFile(FileResource):
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
            
    def _save(self, force=False):
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
    def __init__(self, input_path: str, project=None):
        self.resources = []
        self.__language_files = []
        self.__project = project
        self.input_path = input_path
        self.output_path = input_path

    @cached_property
    def project(self) -> Project:
        return self.__project

    def set_output_location(self, output_path: str) -> None:
        self.output_path = output_path

    def load_json(self, local_path):
        return self.get_json_from_path(os.path.join(self.input_path, local_path))

    def save_json(self, local_path, data):
        return self.__save_json(os.path.join(self.output_path, local_path), data)

    def delete_file(self, local_path):
        try:
            send2trash(os.path.join(self.output_path, local_path))
        except:
            pass

    def save(self, force=False):
        for resource in self.resources:
            resource.save(force=force)

    def register_resource(self, resource):
        self.resources.append(resource)

    def get_language_file(self, file_name:str) -> LanguageFile:
        for language_file in self.language_files:
            if language_file.file_name == file_name:
                return language_file
        raise AssetNotFoundError(file_name)

    @cached_property
    def language_files(self) -> list[LanguageFile]:
        base_directory = os.path.join(self.input_path, "texts")
        for local_path in glob.glob(base_directory + "/**/*.lang", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__language_files.append(LanguageFile(file_path = local_path, pack = self))
            
        return self.__language_files

    ## TODO: Move these static methods OUT
    @staticmethod
    def get_json_from_path(path:str) -> dict:
        with open(path, "r") as fh:
            return Pack.__get_json_from_file(fh)

    @staticmethod
    def __get_json_from_file(fh:TextIOWrapper) -> dict:
        try:
            return json.load(fh)
        except:
            try:
                fh.seek(0)
                contents = ""
                for line in fh.readlines():
                    cleanedLine = line.split("//", 1)[0]
                    if len(cleanedLine) > 0 and line.endswith("\n") and "\n" not in cleanedLine:
                        cleanedLine += "\n"
                    contents += cleanedLine
                while "/*" in contents:
                    preComment, postComment = contents.split("/*", 1)
                    contents = preComment + postComment.split("*/", 1)[1]
                return json.loads(contents)
            except Exception as e:
                print(e)
                return {}
    
    @staticmethod
    def __save_json(file_path, data):
        dir_name = os.path.dirname(file_path)

        if not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w+") as f:
            return json.dump(data, f, indent=2, ensure_ascii=False)

class Project():
    def __init__(self, behavior_path: str, resource_path: str):
        self.__behavior_path = behavior_path
        self.__resource_path = resource_path
        self.__resource_pack = None
        self.__behavior_pack = None

    @cached_property
    def resource_pack(self) -> ResourcePack:
        self.__resource_pack = ResourcePack(self.__resource_path, project=self)
        return self.__resource_pack

    @cached_property
    def behavior_pack(self) -> BehaviorPack:
        self.__behavior_pack = BehaviorPack(self.__behavior_path, project=self)
        return self.__behavior_pack

    def save(self, force=False):
        self.__behavior_pack.save(force=force)
        self.__resource_pack.save(force=force)

# Forward Declares
class BehaviorPack(Pack): pass
class ResourcePack(Pack): pass