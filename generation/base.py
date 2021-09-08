from __future__ import annotations
from abc import abstractclassmethod, abstractmethod
from functools import cached_property
from typing import Any
from io import TextIOWrapper
from send2trash import send2trash
import re
import os
import json
import glob

"'minecraft:client_entity' description.animations *"

# TODO What does this do?
DOT_MATCHER_REGEX = re.compile(r"\.(?=(?:[^\"']*[\"'][^\"']*[\"'])*[^\"']*$)")

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
        if(self.__owner is not None):
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

class Reticulator():
    def __init__(self, username=None):
        self.username = username if username != None else os.getlogin()
        self.com_mojang_path = "C:\\Users\\{}\\AppData\\Local\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang".format(username)

    def load_project_from_path(self, input_path) -> Project:
        return Project(input_path)

    def load_behavior_pack_from_path(self, input_path) -> BehaviorPack:
        return BehaviorPack(input_path)
    
    def load_behavior_pack_from_folder_name(self, pack_name):
        search_location = os.path.join(self.com_mojang_path, "development_behavior_packs")
        for dir_name in os.listdir(search_location):
            if dir_name == pack_name:
                return self.load_behavior_pack_from_path(os.path.join(search_location, dir_name))

    def load_behavior_pack_from_name(self):
        pass

    def load_behavior_pack_from_uuid(self):
        pass

    def load_resource_pack_from_path(self, input_path):
        return ResourcePack(input_path)

    def get_resource_packs(self):
        pass

    def get_behavior_packs(self):
        pass

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

        # Protected
        self._data = None
        self._dirty = False

        # Private
        self.__resources: Resource = []


    @property
    def dirty(self):
        raise NotImplementedError

    @dirty.setter
    def dirty(self, dirty):
        raise NotImplementedError

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

    def _save(self, force=False):
        """Internal implementation of asset saving."""
        raise NotImplementedError()

    def _should_delete(self):
        return True

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
            self._save()
            self.dirty = False

    def _delete(self, force=False):
        """Internal implementation for asset deletion."""
        raise NotImplementedError()

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
    def __init__(self, file_path: str, pack: Pack = None) -> None:
        super().__init__(pack, pack=pack, )

        # Public
        self.file_path = file_path

        # Private
        self.__mark_for_deletion: bool = False

    # Deletion does not actually delete, but rather just prevents saving
    def _delete(self, force = False):
        self.__mark_for_deletion = True

    def _should_delete(self):
        return not self.__mark_for_deletion and super()._should_delete()

    def _should_save(self):
        return not self.__mark_for_deletion and super()._should_save()


class JsonResource(Resource):
    """
    Parent class, which is responsible for all resources which contain
    json data.

    Should not be used directly. Use should JsonFileResource, or JsonSubResource.

    Contains:
     - Data object
     - Method for interacting with the data
    """

    def __init__(self, data: dict, file: FileResource = None, pack: Pack = None) -> None:
        self.data = self.convert_to_notify(data)
        super().__init__(file=file, pack=pack)

    def convert_to_notify(self, raw_data):
        if isinstance(raw_data, dict):
            return NotifyDict(raw_data, owner=self)
        if isinstance(raw_data, list):
            return NotifyList(raw_data, owner=self)
        else:
            return raw_data

    # TODO: Make all these methods into using self.data.

    def remove_value_at(self, json_path, data):
        try:
            keys = DOT_MATCHER_REGEX.split(json_path)
            final = keys.pop().strip("'")
            for key in keys:
                data = data[key.strip("'")]
            del data[final]
        except KeyError:
            raise AssetNotFoundError(json_path, data)
            
    def set_value_at(self, json_path, data: dict, insert_data: dict):
        try:
            keys = DOT_MATCHER_REGEX.split(json_path)
            final = keys.pop().strip("'")
            for key in keys:
                data = data[key.strip("'")]
            
            # If number, then cast
            print(final)
            if '[' in final:
                final = int(final.strip('[]'))

            data[final] = insert_data
        except KeyError:
            raise AssetNotFoundError(json_path, data)


    def get_value_at(self, json_path, data):
        try:
            keys = DOT_MATCHER_REGEX.split(json_path)
            for key in keys:
                data = data[key.strip("'")]
            
            return data
        except KeyError:
            raise AssetNotFoundError(json_path, data)

    def get_id_from_jsonpath(self, json_path):
        keys = DOT_MATCHER_REGEX.split(json_path)
        return keys[len(keys) - 1].replace("'", "")

    def get_data_at(self, json_path, data):
        try:
            keys = DOT_MATCHER_REGEX.split(json_path)

            # Last key should always be be *
            if keys.pop().strip("'") != '*':
                raise AmbiguousAssetError('get_data_at used with non-ambiguous path', json_path)

            for key in keys:
                data = data.get(key.strip("'"), {})
            
            base = json_path.strip("*")

            if isinstance(data, dict):
                for key in data.keys():
                    yield base + f"'{key}'", data[key]
            elif isinstance(data, list):
                for i, element in enumerate(data):
                    yield base + f"[{i}]", element
            else:
                raise AmbiguousAssetError('get_data_at found a single element, not a list or dict.', json_path)
            

        except KeyError as key_error:
            raise AssetNotFoundError(json_path, data) from key_error
    

class LanguageResource(Resource):
    def __init__(self, pack: Pack, file: JsonFileResource) -> None:
        super().__init__(pack, file)


class JsonFileResource(FileResource, JsonResource):
    """
    A file, which contains json data. Most files in the addon system
    are of this type, or have it as a resource parent.
    """
    def __init__(self, pack: Pack = None, file_path: str = None, data: dict = None) -> None:
        super().__init__(pack, self)
        self.pack = pack

        if file_path:
            self.file_name = os.path.basename(file_path)

        # The case where data is passed in as an argument
        if data != None:
            self._data = NotifyDict(data, owner=self)

        if pack:
            self.pack.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @property
    def data(self):
        # The case where data was not passed in as an argument
        if self._data == None:
            self._data = NotifyDict(self.pack.load_json(self.file_path), owner=self)
        return self._data

    @data.setter
    def data(self, data):
        self.dirty = True
        self._data = data

    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty

    def _should_save(self):
        return not self.__mark_for_deletion and super()._should_save()

    def _save(self, force):
        self.pack.save_json(self.file_path, self.data)

    def delete(self):
        self.__mark_for_deletion = True

class JsonSubResource(JsonResource):
    def __init__(self, parent: Resource, json_path: str, data: dict) -> None:
        super().__init__(parent.pack, parent.file)
        self.data = data
        self.parent = parent
        self.json_path = json_path
        self.id = self.get_id_from_jsonpath(json_path)
        self.__resources: JsonSubResource = []
        self.parent.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

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
        self.remove_value_at(self.json_path, self.parent.data)

class Pack():
    def __init__(self, input_path: str, project=None):
        self.resources = []
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
            return json.dump(data, f, indent=2)

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