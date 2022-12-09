from __future__ import annotations

import re
import os
import json
import glob
import functools 

from pathlib import Path
from functools import cached_property
from typing import Union, Tuple, TypeVar, Any

import dpath

NO_ARGUMENT = object()
TEXTURE_EXTENSIONS = ["png", "jpg", "jpeg", "tga"]
SOUND_EXTENSIONS = ["wav", "fsb", "ogg"]

T = TypeVar('T')

class TypeInfo:
    """
    Class for encapsulating the arguments that are passed to sub-resource based
    decorators.
    """
    
    def __init__(self, *, jsonpath="", filepath="", attribute="", getter_attribute="", extension=".json"):
        self.jsonpath = jsonpath
        self.filepath = filepath
        self.attribute = attribute
        self.getter_attribute = getter_attribute
        self.extension = extension


def convert_to_notify_structure(data: Union[dict, list], parent: Resource) -> Union[NotifyDict, NotifyList]:
    """
    Converts a dict or list to a notify structure.
    """
    if isinstance(data, dict):
        return NotifyDict(data, owner=parent)

    if isinstance(data, list):
        return NotifyList(data, owner=parent)

    return data


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


def ClassProperty(attribute: str, jsonpath: str = NO_ARGUMENT):
    """
    Class Decorator which injects a single 'property' with proper semantics.

    :param attribute: The attribute where this property can be accessed from
    :param jsonpath: The jsonpath where this attribute can be found in the json data
    """

    # Allow single-argument class-properties
    if jsonpath == NO_ARGUMENT:
        jsonpath = attribute

    def inner(cls):
        @property
        def template_property(self) -> str:
            return self.get_jsonpath(jsonpath)
        
        @template_property.setter
        def template_property(self, new_prop):
            return self.set_jsonpath(jsonpath, new_prop)

        setattr(cls, attribute, template_property)

        return cls
    return inner


def JsonChildResource(parent_cls: Resource, child_cls: T):
    """
    Special case, for looping over all children FILES to access
    RESOURCES. 
    
    Classic example is doing `rp.animations` instead of looping over all
    animation files and then painfully getting animations from there.

    NOT CACHED
    """
    
    parent_attribute = parent_cls.type_info.attribute
    child_attribute = child_cls.type_info.attribute

    def decorator(func) -> cached_property[List[T]]:
        @property
        @functools.wraps(func)
        def wrapper(self) -> List[T]:
            sub_resources = []
            for file_resource in getattr(self, parent_attribute):
                for sub_resource in getattr(file_resource, child_attribute):
                    sub_resources.append(sub_resource)
            return sub_resources
        return wrapper
    return decorator


def ResourceDefinition(cls : T):
    """Inserts implementation for JsonFileResource"""

    attribute = cls.__name__
    filepath = cls.type_info.filepath
    extension = cls.type_info.extension

    def decorator(func) -> cached_property[list[T]]:
        @cached_property
        @functools.wraps(func)
        def wrapper(self) -> list[T]:
            setattr(self, attribute, [])
            base_directory = os.path.join(self.input_path, filepath)

            for local_path in glob.glob(base_directory + "/**/*" + extension, recursive=True):
                local_path = os.path.relpath(local_path, self.input_path)

                getattr(self, attribute).append(cls(filepath = local_path, pack = self))
            return getattr(self, attribute)
        return wrapper
    return decorator


def SingleResourceDefinition(cls : T):
    """Inserts implementation for JsonFileResource (single)"""

    attribute = cls.__name__
    filepath = cls.type_info.filepath
    extension = cls.type_info.extension

    def decorator(func) -> cached_property[T]:
        @cached_property
        @functools.wraps(func)
        def wrapper(self) -> T:
            new_object = cls(filepath = filepath + extension, pack = self)
            setattr(self, attribute, new_object)
            return new_object
        return wrapper
    return decorator


def SubResourceDefinition(cls: T):
    jsonpath = cls.type_info.jsonpath
    attribute = cls.type_info.attribute
    def decorator(func) -> cached_property[list[T]]:
        @cached_property
        @functools.wraps(func)
        def wrapper(self) -> list[T]:
            setattr(self, attribute, [])
            for path, data in self.get_data_at(jsonpath):
                getattr(self, attribute).append(cls(parent = self, json_path = path, data = data))
            return getattr(self, attribute)
        return wrapper
    return decorator


def Getter(cls : T):
    """
    Decorator which allows you to get a resource. For example getting a component
    from an entity.
    """
    attribute = cls.type_info.attribute
    getter_attribute = cls.type_info.getter_attribute
    def decorator(func) -> T:
        @functools.wraps(func)
        def wrapper(self, compare):
            for child in getattr(self, attribute):
                if smart_compare(getattr(child, getter_attribute), compare):
                    return child
            return None # No longer raises an error. Allow a getter to return none.
        return wrapper
    return decorator


def ChildGetter(parent_cls : Any, child_cls : T):
    """
    Special getter for getting sub-resources that are further down the chain.
    For example getting 'animations' directly from the RP without passing
    through the AnimationFile class.
    """
    parent_attribute = parent_cls.type_info.attribute
    child_attribute = child_cls.type_info.attribute
    getter_attribute = child_cls.type_info.getter_attribute
    def decorator(func) -> T:
        @functools.wraps(func)
        def wrapper(self, compare):
            for child in getattr(self, parent_attribute):
                for grandchild in getattr(child, child_attribute):
                    if smart_compare(getattr(grandchild, getter_attribute), compare):
                        return grandchild
                return None
        return wrapper
    return decorator
    
def SubResourceAdder(cls : Resource):
    """
    This decorator allows you to inject SubResources into your Resources.
    """
    jsonpath = cls.type_info.jsonpath
    attribute = cls.type_info.attribute

    def decorator_sub_resource(func):
        @functools.wraps(func)
        def wrapper_sub_resource(self, *args, **kwargs):
            # This handles the case where a class is passed in directly.
            # like `add_box(Box(..))``

            if len(args) > 0:
                raise ReticulatorException("This function can only be called with keyword arguments: 'resource' (alone), or 'id' and 'data'")

            if kwargs.get('resource') == None and (kwargs.get('id') == None or kwargs.get('data') == None):
                raise ReticulatorException("This function can only be called with 'resource' OR 'id and 'data'.")

            # Handle Object case
            if new_object := kwargs.get('resource'):
                self.set_jsonpath(new_object.json_path, new_object.data)
                new_object.parent = self

            # This handles the 'normal' flow, where arguments are passed in
            # via 'parts' and are constructed automatically.
            else:
                id = kwargs.get('id')
                data = kwargs.get('data')

                if id == None:
                    raise ReticulatorException("Id may not be None.")

                if data == None:
                    raise ReticulatorException("Data may not be None")

                new_jsonpath = jsonpath + "/" + id
                self.set_jsonpath(new_jsonpath, data)
                new_object = cls(data=data, parent=self, json_path=new_jsonpath)

            if new_object:
                getattr(self, attribute).append(new_object)
                return new_object
            else:
                raise ReticulatorException()


        return wrapper_sub_resource
    return decorator_sub_resource

# def ResourceAdder(cls : Resource):
#     filepath = cls.type_info.filepath
#     attribute = cls.type_info.attribute

#     def decorator_sub_resource(func):
#         @functools.wraps(func)
#         def wrapper_sub_resource(self, *args):
#             # This handles the case where a class is passed in directly.
#             # like `add_box(Box(..))``
#             if len(args) == 1 and isinstance(args[0], cls):
#                 args[0].pack = self

#             # This handles the 'normal' flow, where arguments are passed in
#             # via 'parts' and are constructed automatically.
#             else:
#                 name = args[0]
#                 data = args[1]

#                 new_jsonpath = jsonpath + "/" + name
#                 self.set_jsonpath(new_jsonpath, data)
#                 new_object = cls(data=data, parent=self, json_path=new_jsonpath)
            
#             # Last step is adding the new object to the attribute
#             if new_object:
#                 getattr(self, attribute).append(new_object)
#                 return new_object
#             else:
#                 raise ReticulatorException()


#         return wrapper_sub_resource
#     return decorator_sub_resource

# Methods
def create_nested_directory(path: str):
    """
    Creates a nested directory structure if it doesn't exist.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def save_json(filepath, data):
    """
    Saves json to a filepath, creating nested directory if required.
    """
    create_nested_directory(filepath)
    with open(filepath, "w+") as file_head:
        return json.dump(data, file_head, indent=2, ensure_ascii=False)

def smart_compare(a, b) -> bool:
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


# Exceptions
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

class InvalidJsonError(ReticulatorException):
    """
    Called when a JSON file is invalid.
    """

class AmbiguousAssetError(ReticulatorException):
    """
    Called when a path is not unique.
    """

class FormatVersionError(ReticulatorException):
    """
    Called when a format version does not exist for a file
    """


# Base Classes

class NotifyDict(dict):
    """
    A notify dictionary is a dictionary that can notify its parent when its been
    edited.
    """
    def __init__(self, *args, owner: Resource = None, **kwargs):
        self._owner = owner

        if len(args) > 0:
            for key, value in args[0].items():
                args[0][key] = convert_to_notify_structure(value, self._owner)
        super().__init__(*args, **kwargs)

    def get_item(self, attr):
        try:
            return self.__getitem__(attr)
        except Exception:
            return None
    
    def __delitem__(self, v) -> None:
        if(self._owner != None):
            self._owner.dirty = True
        return super().__delitem__(v)

    def __setitem__(self, attr, value):
        value = convert_to_notify_structure(value, self._owner)

        if self.get_item(attr) != value:
            if(self._owner != None):
                self._owner.dirty = True

        super().__setitem__(attr, value)

class NotifyList(list):
    """
    A notify list is a list which can notify its owner when it has
    changed.
    """
    def __init__(self, *args, owner: Resource = None, **kwargs):
        self._owner = owner

        if len(args) > 0:
            for i in range(len(args[0])):
                args[0][i] = convert_to_notify_structure(args[0][i], self._owner)

        super().__init__(*args, **kwargs)

    def get_item(self, attr):
        try:
            return self.__getitem__(attr)
        except Exception:
            return None
    
    def __delitem__(self, v) -> None:
        if(self._owner != None):
            self._owner.dirty = True
        return super().__delitem__(v)
    
    def append(self, v):
        if(self._owner != None):
            self._owner.dirty = True
        super().append(v)

    def extend(self, v):
        if(self._owner != None):
            self._owner.dirty = True
        super().extend(v)

    def __setitem__(self, attr, value):
        value = convert_to_notify_structure(value, self._owner)

        if self.__getitem__(attr) != value:
            if(self._owner != None):
                self._owner.dirty = True
        
        super().__setitem__(attr, value)

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


class Resource():
    """
    The top resource in the inheritance chain.

    Contains:
     - reference to the Pack (could be blank, if floating resource)
     - reference to the File (could be a few links up the chain)
     - dirty status
     - abstract ability to save, including context manager support
     - list of children resources
    """
    
    jsonpath : str
    
    def __init__(self, file: FileResource = None, pack: Pack = None) -> None:
        # Public
        self.pack: Union[ResourcePack, BehaviorPack] = pack
        self.file = file
        self._dirty = False
        self._deleted = False

        # Private
        self._resources: Resource = []

    def __enter__(self) -> Resource:
        """
        Context manager support.
        """
        return self

    def __exit__(self, type, value, traceback):
        """
        Context manager support. Will save the resource on exit.
        """
        self.save()
    
    @property
    def dirty(self):
        """
        Whether the asset is dirty (has been edited).
        """
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty

    def register_resource(self, resource) -> None:
        """
        Register a child resource. These resources will always be saved first.
        """
        self._resources.append(resource)

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

        # File Assets without packs may not save.
        if isinstance(self, FileResource) and not self.pack:
            raise FloatingAssetError("Assets without a pack cannot be saved.")

        # Only dirty assets can be saved, unless forced.
        if self.dirty or force:
            # Save all children first
            for resource in self._resources:
                resource.save(force=force)

            # Now, save this resource
            self._save()

            # Mark as clean
            self.dirty = False


    def delete(self):
        """
        Deletes the resource. Should not be overridden.
        """

        # First, delete all resources of children
        for resource in self._resources:
            resource.delete()

        # Then delete self
        self._delete()


class FileResource(Resource):
    """
    A resource, which is also a file.
    Contains:
     - File path
     - Ability to mark for deletion
    """
    def __init__(self, filepath: str = None, pack: Pack = None) -> None:
        # Initialize resource
        super().__init__(file=self, pack=pack)

        # All files must register themselves with their pack
        # if the pack exists.
        if self.pack:
            pack.register_resource(self)

        # Public
        self.filepath = filepath

        if filepath:
            self.file_name = os.path.basename(filepath)

    def _delete(self):
        """
        Internal implementation of file deletion.

        Marking for deletion allows us to delete the file during saving,
        without effecting the file system during normal operation.
        """
        self._deleted = True

class JsonResource(Resource):
    """
    Parent class, which is responsible for all resources which contain
    json data.
    Should not be used directly. Use JsonFileResource, or JsonSubResource instead.
    Contains:
     - Data object
     - Method for interacting with the data
    """

    # The type information, used for generating this class at runtime.
    type_info : TypeInfo
    
    def __init__(self, data: dict = None, file: FileResource = None, pack: Pack = None) -> None:
        super().__init__(file=file, pack=pack)
        self._data = data
    
    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self.dirty = True
        self._data = data

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

    def delete_jsonpath(self, json_path:str) -> None:
        """
        Removes value at jsonpath location.
        """
        path_exists = self.jsonpath_exists(json_path)
        if path_exists:
            self.dirty = True
            dpath.delete(self.data, json_path)

    def pop_jsonpath(self, json_path, default=NO_ARGUMENT) \
        -> Union[dict, list, int, str, float]:
        """
        Removes value at jsonpath location, and returns it.
        """

        data = self.get_jsonpath(json_path, default=default)
        self.delete_jsonpath(json_path)
        self.dirty = True
        return data

    def append_jsonpath(self, json_path:str, insert_value:Any):
        """
        Appends a value at jsonpath location. Will create path if it doesn't exist.
        """

        path_exists = self.jsonpath_exists(json_path)

        # Otherwise, set the value
        self.dirty = True

        if path_exists:
            self.get_jsonpath(json_path).append(insert_value)
        else:
            self.set_jsonpath(json_path, [insert_value])

    def set_jsonpath(self, json_path:str, insert_value:any, overwrite:bool=True):
        """
        Sets value at jsonpath location.

        Can create a new key if it doesn't exist.
        """

        path_exists = self.jsonpath_exists(json_path)

        # If overwrite is false, it will set the path only
        # if there is no path.
        if path_exists and not overwrite:
            return

        # Otherwise, set the value
        self.dirty = True
        dpath.new(self.data, json_path, insert_value)
        

    def get_jsonpath(self, json_path, default=NO_ARGUMENT):
        """
        Gets value at jsonpath location.

        A default value may be provided, for missing keys.

        raises:
            AssetNotFoundError if the path does not exist.
        """
        try:
            return dpath.get(self.data, json_path)
        except Exception as exception:
            if default is not NO_ARGUMENT:
                return default
            raise AssetNotFoundError(
                f"Path {json_path} does not exist."
            ) from exception

    def get_data_at(self, json_path):
        """
        Returns a list of jsonpaths found at this jsonpath location.
        For a list, this will return: json_path + list index
        For a dict, this will return json_path + dict key

        Exception will be raised if the result is not a list or dict.
        Missing data path will return []
        """
        try:
            # Special case, to handle the root of the json
            if json_path == "**":
                result = self.data
            else:
                result = self.get_jsonpath(json_path, default=[])

            if isinstance(result, dict):
                for key in result.keys():
                    yield json_path + f"/{key}", result[key]
            elif isinstance(result, list):
                for i, element in enumerate(result):
                    yield json_path + f"/[{i}]", element
            else:
                raise AmbiguousAssetError(f"Path '{json_path}' matched a single element, not a list or dict.")

        except KeyError as key_error:
            raise AssetNotFoundError(json_path, self.data) from key_error


class JsonSubResource(JsonResource):
    """
    A sub resource represents a chunk of json data, within a file.
    """
    def __init__(self, parent: Resource = None, json_path: str = None, data: dict = None) -> None:
        super().__init__(data = data, pack = parent.pack, file = parent.file)

        # The parent of the sub-resource is the asset of type Resource
        # which owns this sub-resource. For example a Component is owned by
        # either an EntityFileBP, or a ComponentGroup.
        self.parent: JsonResource = parent

        # The jsonpath is the location within the parent resource, where
        # this sub-resource is stored.
        self._json_path: str = json_path

        # The original path location needs to be stored, for the purpose
        # of renaming or moving the sub-resource.
        self._original_json_path: str = json_path

        # Register self into parent, so that it can be found by the parent
        # during saving, etc.
        self.parent.register_resource(self)
    
    @property
    def json_path(self):
        return self._json_path

    @json_path.setter
    def json_path(self, json_path):
        self.dirty = True
        self._json_path = json_path

    @property
    def id(self):
        """
        The ID of the sub-resource, such as 'minecraft:scale' for a component.
        """
        return self.json_path.rsplit("/", maxsplit=1)[1]

    @id.setter
    def id(self, id):
        self.dirty = True
        self.json_path = self.json_path.rsplit("/", maxsplit=1)[0] + "/" + id

    def __repr__(self):
        return f"'{self.__class__.__name__}: {self.id}'"

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
        self.parent.dirty = dirty # Pseudo recursive call will travel up the chain


    def _save(self):
        """
        Saves the resource, into its parents json structure.

        This works by replacing the data at the jsonpath location,
        meaning that the parent will contain accurate representation of
        the children's data, saved into itself.
        """

        # If the id was updated, we need to serialize into a new location.
        # This implies first deleting the old location, and then creating
        # a new one.
        if not self._deleted:
            if self.json_path != self._original_json_path:
                self.parent.delete_jsonpath(self._original_json_path)
                self.parent.set_jsonpath(self.json_path, self.data)
            else:
                self.parent.set_jsonpath(self.json_path, self.data)

        self._dirty = False

    def _delete(self):
        """
        Deletes itself from parent, by removing the data at the jsonpath
        location.

        If it is a list, it must only set itself to None. The actual
        deletion will take place during saving.
        """
        self.parent.dirty = True
        self.parent._resources.remove(self)
        self._deleted = True
        self.parent.delete_jsonpath(self.json_path)

class JsonFileResource(FileResource, JsonResource):
    """
    A file, which contains json data. Most files in the addon system
    are of this type, or have it as a resource parent.
    """
    def __init__(self, data: dict = None, filepath: str = None, pack: Pack = None) -> None:
        # Init file resource parent, which gives us access to data
        FileResource.__init__(self, filepath=filepath, pack=pack)
        
        # Data is either set directly, or is read from the filepath for this
        # resource. This allows assets to be created from scratch, whilst
        # still having an associated file location.
        if data is not None:
            self.data = data
        else:
            self.data = self.load_json(self.filepath)

        # Init json resource, which relies on the new data attribute
        JsonResource.__init__(self, data=self.data, file=self, pack=pack)

    def __repr__(self):
        return f"'{self.__class__.__name__}: {self.filepath}'"


    def load_json(self, filepath: str) -> dict:
        """
        Loads json from file. `local_path` paramater is local to the projects
        input path.
        """
        
        if self.pack:
            filepath = os.path.join(self.pack.input_path, filepath)

        if not os.path.exists(filepath):
            raise AssetNotFoundError(f"File not found: {filepath}")
        try:
            with open(filepath, "r", encoding='utf8') as fh:
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
                        return {}
        except Exception:
            raise InvalidJsonError(filepath)

    def _save(self):
        save_path = os.path.join(self.pack.output_directory, self.filepath)
        create_nested_directory(save_path)

        # If the file has been marked for deletion, delete it
        if self._deleted:
            # If the paths are the same, delete the file, otherwise
            # we can just pass
            if smart_compare(self.pack.input_path, self.pack.output_directory):
                os.remove(save_path)
        else:
            with open(save_path, "w+") as file_head:
                clean_data = {k: v for k, v in self.data.items() if v is not None}
                return json.dump(clean_data, file_head, indent=2, ensure_ascii=False)

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
        attribute = "animation_controllers",
        getter_attribute = "id"
    )

@format_version()
class AnimationControllerFileBP(JsonFileResource):

    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "animation_controllers",
        attribute = "animation_controller_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(AnimationControllerBP)
    def animation_controllers(self): pass
    @Getter(AnimationControllerBP)
    def get_animation_controller(self, id: str): pass
    @SubResourceAdder(AnimationControllerBP)
    def add_animation_controller(self, name: str, data: dict): pass


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
        attribute = "functions",
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
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "feature_rules",
        attribute = "feature_rules",
        getter_attribute="identifier"
    )

@identifier("**/description/identifier")
@format_version()
class FeatureFile(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "features",
        attribute = "features",
        getter_attribute="identifier"
    )
    
@format_version()
@identifier("minecraft:spawn_rules/description/identifier")
class SpawnRuleFile(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "spawn_rules",
        attribute = "spawn_rules",
        getter_attribute="identifier"
    )

@identifier("**/identifier")
@format_version()
class RecipeFile(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "recipes",
        attribute = "recipes",
        getter_attribute="identifier"
    )

class EntityComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/components",
        attribute = "components",
        getter_attribute = "id"
    )

class EntityEventBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/events",
        attribute = "events",
        getter_attribute = "id"
    )

class Component(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "**",
        attribute = "components",
        getter_attribute = "id"
    )

class ComponentGroup(JsonSubResource):
    """
    A component group is a collection of components in an EntityFileBP.
    """
    type_info = TypeInfo(
        jsonpath = "minecraft:entity/component_groups",
        attribute = "component_groups",
        getter_attribute = "id"
    )

    @SubResourceDefinition(Component)
    def components(self): pass
    @Getter(Component)
    def get_component(self, id: str): pass
    @SubResourceAdder(Component)
    def add_component(self, name: str, data: dict): pass

@format_version()
@identifier("minecraft:entity/description/identifier")
class EntityFileBP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "entities",
        attribute = "entities",
        getter_attribute = "identifier"
    )

    @property
    def counterpart(self) -> EntityFileRP:
        return self.pack.project.resource_pack.get_entity(self.identifier)

    @SubResourceDefinition(EntityEventBP)
    def events(self): pass
    @Getter(EntityEventBP)
    def get_event(self, id: str): pass
    @SubResourceAdder(EntityEventBP)
    def add_event(self, name: str, data: dict): pass

    @SubResourceDefinition(EntityComponentBP)
    def components(self): pass
    @Getter(EntityComponentBP)
    def get_component(self, id: str): pass
    @SubResourceAdder(EntityComponentBP)
    def add_component(self, name: str, data: dict): pass

    @SubResourceDefinition(ComponentGroup)
    def component_groups(self): pass
    @Getter(ComponentGroup)
    def get_component_group(self, id: str): pass
    @SubResourceAdder(ComponentGroup)
    def add_component_group(self, name: str, data: dict): pass

class LootTablePool(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "pools",
        attribute = "pools"
    )

class LootTableFile(JsonFileResource):
    type_info = TypeInfo(
        filepath = "loot_tables",
        attribute = "loot_tables",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(LootTablePool)
    def pools(self): pass

class ItemComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/components",
        attribute = "components",
        getter_attribute = "id"
    )

class ItemEventBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/events",
        attribute = "events",
        getter_attribute = "id"
    )


@format_version()
@identifier("minecraft:item/description/identifier")
class ItemFileBP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "items",
        attribute = "items",
        getter_attribute = "identifier"
    )

    @SubResourceDefinition(ItemComponentBP)
    def components(self): pass
    @Getter(ItemComponentBP)
    def get_component(self, id: str): pass
    @SubResourceAdder(ItemComponentBP)
    def add_component(self, name: str, data: dict): pass

    @SubResourceDefinition(ItemEventBP)
    def events(self): pass
    @Getter(ItemEventBP)
    def get_event(self, id: str): pass
    @SubResourceAdder(ItemEventBP)
    def add_event(self, name: str, data: dict): pass


class BlockFileComponentBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:block/components",
        attribute = "components",
        getter_attribute = "id"
    )


@format_version()
@identifier(jsonpath="minecraft:block/description/identifier")
class BlockFileBP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "blocks",
        attribute = "blocks",
        getter_attribute = "identifier"
    )

    @SubResourceDefinition(BlockFileComponentBP)
    def components(self): pass
    @Getter(BlockFileComponentBP)
    def get_component(self, id: str): pass
    @SubResourceAdder(BlockFileComponentBP)
    def add_component(self, name: str, data: dict): pass

@ClassProperty('loop')
class AnimationBP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animations",
        attribute = "animations",
        getter_attribute = "id"
    )

class AnimationFileBP(JsonFileResource):
    type_info = TypeInfo(
        filepath = "animations",
        attribute = "animation_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(AnimationBP)
    def animations(self): pass
    @SubResourceAdder(AnimationBP)
    def add_animation(self, name: str, data: dict): pass
    @Getter(AnimationBP)
    def get_animation(self, id: str): pass

class BehaviorPack(Pack):
    """
    The BehaviorPack represents the behavior pack of a project.
    """

    @ResourceDefinition(AnimationControllerFileBP)
    def animation_controller_files(self): pass
    @Getter(AnimationControllerFileBP)
    def get_animation_controller_file(self, filepath: str): pass
    @JsonChildResource(AnimationControllerFileBP, AnimationControllerBP)
    def animation_controllers(self): pass
    @ChildGetter(AnimationControllerFileBP, AnimationControllerBP)
    def get_animation_controller(self, id: str): pass

    @ResourceDefinition(AnimationFileBP)
    def animation_files(self): pass
    @Getter(AnimationFileBP)
    def get_animation_file(self, filepath: str): pass
    @JsonChildResource(AnimationFileBP, AnimationBP)
    def animations(self): pass
    @ChildGetter(AnimationFileBP, AnimationBP)
    def get_animation(self, id: str): pass

    @ResourceDefinition(FunctionFile)
    def functions(self): pass
    @Getter(FunctionFile)
    def get_function(self, filepath: str): pass

    @ResourceDefinition(FeatureRuleFile)
    def feature_rules(self): pass
    @Getter(FeatureRuleFile)
    def get_feature_rule(self, identifier: str): pass

    @ResourceDefinition(FeatureFile)
    def features(self): pass
    @Getter(FeatureFile)
    def get_feature(self, identifier: str): pass

    @ResourceDefinition(SpawnRuleFile)
    def spawn_rules(self): pass
    @Getter(SpawnRuleFile)
    def get_spawn_rule(self, identifier: str): pass

    @ResourceDefinition(RecipeFile)
    def recipes(self): pass
    @Getter(RecipeFile)
    def get_recipe(self, identifier: str): pass

    @ResourceDefinition(EntityFileBP)
    def entities(self): pass
    @Getter(EntityFileBP)
    def get_entity(self, identifier: str): pass

    @ResourceDefinition(LootTableFile)
    def loot_tables(self): pass
    @Getter(LootTableFile)
    def get_loot_table(self, identifier: str): pass

    @ResourceDefinition(ItemFileBP)
    def items(self): pass
    @Getter(ItemFileBP)
    def get_item(self, identifier: str): pass

    @ResourceDefinition(BlockFileBP)
    def blocks(self): pass
    @Getter(BlockFileBP)
    def get_block(self, identifier: str): pass


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
        attribute = "components",
        getter_attribute = "id"
    )

class ParticleFileEvent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "particle_effect/events",
        attribute = "components",
        getter_attribute = "id"
    )

@format_version()
@identifier("particle_effect/description/identifier")
class ParticleFile(JsonFileResource):
    """
    ParticleFile is a JsonFileResource which represents a particle file.
    """
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "particles",
        attribute = "particles",
        getter_attribute = "identifier"
    )

    @SubResourceDefinition(ParticleFileComponent)
    def components(self): pass
    @Getter(ParticleFileComponent)
    def get_component(self, id: str): pass
    @SubResourceAdder(ParticleFileComponent)
    def add_component(self, name: str, data: dict): pass

    @SubResourceDefinition(ParticleFileEvent)
    def events(self): pass
    @Getter(ParticleFileEvent)
    def get_event(self, id: str): pass
    @SubResourceAdder(ParticleFileEvent)
    def add_event(self, name: str, data: dict): pass

class AnimationControllerStateRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "states",
        attribute = "states",
        getter_attribute = "id"
    )

@ClassProperty('initial_state')
class AnimationControllerRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animation_controllers",
        attribute = "animation_controllers",
        getter_attribute = "id"
    )

    @SubResourceDefinition(AnimationControllerStateRP)
    def states(self): pass
    @Getter(AnimationControllerStateRP)
    def get_state(self, id: str): pass
    @SubResourceAdder(AnimationControllerStateRP)
    def add_state(self, name: str, data: dict): pass

class AnimationControllerFileRP(JsonFileResource):
    """
    AnimationControllerFileRP
    """
    type_info = TypeInfo(
        filepath = "animation_controllers",
        attribute = "animation_controller_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(AnimationControllerRP)
    def animation_controllers(self): pass
    @Getter(AnimationControllerRP)
    def get_animation_controller(self, id: str): pass
    @SubResourceAdder(AnimationControllerRP)
    def add_animation_controller(self, name: str, data: dict): pass

@ClassProperty('loop')
class AnimationRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "animations",
        attribute = "animations",
        getter_attribute = "id"
    )

class AnimationFileRP(JsonFileResource):
    """
    AnimationFileRP is a class which represents a resource pack's animation file.
    Since many animations are defined in the same file, it is often more useful.
    to use the AnimationRP class instead.
    """

    type_info = TypeInfo(
        filepath = "animations",
        attribute = "animation_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(AnimationRP)
    def animations(self): pass
    @SubResourceAdder(AnimationRP)
    def add_animation(self, name: str, data: dict): pass
    @Getter(AnimationRP)
    def get_animation(self, id: str): pass

@format_version()
@identifier("minecraft:attachable/description/identifier")
class AttachableFileRP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "attachables",
        attribute = "attachables",
        getter_attribute = "identifier"
    )


class BiomesClientFile(JsonFileResource):
    """
    BiomesClientFile is a class which represents the data stored in 'rp/biomes_client.json'
    """

    type_info = TypeInfo(
        filepath = "biomes_client",
        attribute = "biomes_client_file"
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
class EntityFileRP(JsonFileResource):
    """
    EntityFileRP is a class which represents a resource pack's entity file.
    """
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "entity",
        attribute = "entities",
        getter_attribute = "identifier"
    )

    @property
    def counterpart(self) -> EntityFileBP:
        return self.pack.project.behavior_pack.get_entity(self.identifier)

    @SubResourceDefinition(EntityEventBP)
    def events(self): pass
    @Getter(EntityEventBP)
    def get_event(self, id: str): pass
    @SubResourceAdder(EntityEventBP)
    def add_event(self, name: str, data: dict): pass

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
        attribute = "distance_components",
        getter_attribute = "id"
    )

class FogVolumetricDensityComponent(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:fog_settings/volumetric/density",
        attribute = "volumetric_density_components",
        getter_attribute = "id"
    )

class FogVolumetricMediaCoefficient(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:fog_settings/volumetric/media_coefficients",
        attribute = "volumetric_media_coefficients",
        getter_attribute = "id"
    )

@format_version()
@identifier("minecraft:fog_settings/description/identifier")
class FogFile(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "fogs",
        attribute = "fogs",
        getter_attribute = "identifier"
    )

    @SubResourceDefinition(FogDistanceComponent)
    def distance_components(self): pass
    @Getter(FogDistanceComponent)
    def get_distance_component(self, id: str): pass
    @SubResourceAdder(FogDistanceComponent)
    def add_distance_component(self, name: str, data: dict): pass

    @SubResourceDefinition(FogVolumetricDensityComponent)
    def volumetric_density_components(self): pass
    @Getter(FogVolumetricDensityComponent)
    def get_volumetric_density_component(self, id: str): pass
    @SubResourceAdder(FogVolumetricDensityComponent)
    def add_volumetric_density_component(self, name: str, data: dict): pass

    @SubResourceDefinition(FogVolumetricMediaCoefficient)
    def volumetric_media_coefficients(self): pass
    @Getter(FogVolumetricMediaCoefficient)
    def get_volumetric_media_coefficient(self, id: str): pass
    @SubResourceAdder(FogVolumetricMediaCoefficient)
    def add_volumetric_media_coefficient(self, name: str, data: dict): pass

class ItemComponentRP(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "minecraft:item/components",
        attribute = "components",
        getter_attribute = "id"
    )

@format_version()
@identifier("minecraft:item/description/identifier")
class ItemFileRP(JsonFileResource):
    format_version : FormatVersion
    identifier: str
    type_info = TypeInfo(
        filepath = "items",
        attribute = "items",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(ItemComponentRP)
    def components(self): pass
    @Getter(ItemComponentRP)
    def get_component(self, id: str): pass
    @SubResourceAdder(ItemComponentRP)
    def add_component(self, name: str, data: dict): pass

class Material(JsonSubResource):
    """
    Represents a single material, from a .material file
    """

    type_info = TypeInfo(
        jsonpath = "**",
        attribute = "materials",
        getter_attribute = "id"
    )

@format_version(jsonpath="materials/version")
class MaterialFile(JsonFileResource):
    """
    MaterialFile is a class which represents a resource pack's material file.
    Since many materials can be defined in the same file, it is often more useful
    to use the MaterialRP class directly.
    """
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "materials",
        attribute = "material_files",
        getter_attribute = "filepath",
        extension="material"
    )

    @SubResourceDefinition(Material)
    def materials(self): pass
    @Getter(Material)
    def get_material(self, id: str): pass
    @SubResourceAdder(Material)
    def add_material(self, name: str, data: dict): pass

class Cube(JsonSubResource):
    type_info = TypeInfo(
        jsonpath = "cubes",
        attribute = "cubes",
        getter_attribute = "id"
    )

@ClassProperty("name")
class Bone(JsonSubResource):
    name: str
    type_info = TypeInfo(
        jsonpath = "bones",
        attribute = "bones",
        getter_attribute = "name"
    )

    @SubResourceDefinition(Cube)
    def cubes(self): pass
    @Getter(Cube)
    def get_cube(self, id: str): pass
    @SubResourceAdder(Cube)
    def add_cube(self, name: str, data: dict): pass


@identifier("description/identifier")
class Model(JsonSubResource):
    identifier: str
    type_info = TypeInfo(
        jsonpath = "minecraft:geometry",
        attribute = "models",
        getter_attribute = "identifier"
    )

    @SubResourceDefinition(Bone)
    def bones(self): pass
    @Getter(Bone)
    def get_bone(self, id: str): pass
    @SubResourceAdder(Bone)
    def add_bone(self, name: str, data: dict): pass

@format_version()
class ModelFile(JsonFileResource):
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "models",
        attribute = "model_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(Model)
    def models(self): pass
    @Getter(Model)
    def get_model(self, id: str): pass
    @SubResourceAdder(Model)
    def add_model(self, name: str, data: dict): pass

class RenderController(JsonSubResource):
    """
    A JsonSubResource, representing a single Render Controller object, contained
    within a RenderControllerFile.
    """

    type_info = TypeInfo(
        jsonpath = "render_controllers",
        attribute = "render_controllers",
        getter_attribute = "id"
    )

@format_version()
class RenderControllerFile(JsonFileResource):
    format_version : FormatVersion
    type_info = TypeInfo(
        filepath = "render_controllers",
        attribute = "render_controller_files",
        getter_attribute = "filepath"
    )

    @SubResourceDefinition(RenderController)
    def render_controllers(self): pass
    @SubResourceAdder(RenderController)
    def add_render_controller(self, name: str, data: dict): pass
    @Getter(RenderController)
    def get_render_controller(self, id: str): pass


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

class ResourcePack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self._sounds: list[str] = []
        self._textures: list[str] = []

    @ResourceDefinition(ParticleFile)
    def particles(self): pass
    @Getter(ParticleFile)
    def get_particle(self, identifier: str): pass

    @ResourceDefinition(AttachableFileRP)
    def attachables(self): pass
    @Getter(AttachableFileRP)
    def get_attachable(self, identifier:str): pass

    @ResourceDefinition(AnimationControllerFileRP)
    def animation_controller_files(self): pass
    @Getter(AnimationControllerFileRP)
    def get_animation_controller_file(self, filepath:str): pass
    @JsonChildResource(AnimationControllerFileRP, AnimationControllerRP)
    def animation_controllers(self): pass
    @ChildGetter(AnimationControllerFileRP, AnimationControllerRP)
    def get_animation_controller(self, id: str): pass

    @ResourceDefinition(AnimationFileRP)
    def animation_files(self): pass
    @Getter(AnimationFileRP)
    def get_animation_file(self, filepath:str): pass
    @JsonChildResource(AnimationFileRP, AnimationRP)
    def animations(self): pass
    @ChildGetter(AnimationFileRP, AnimationRP)
    def get_animation(self, id: str): pass

    @ResourceDefinition(MaterialFile)
    def material_files(self): pass
    @Getter(MaterialFile)
    def get_material_file(self, filepath:str): pass
    @JsonChildResource(MaterialFile, Material)
    def materials(self): pass
    @ChildGetter(MaterialFile, Material)
    def get_material(self, id: str): pass

    @ResourceDefinition(EntityFileRP)
    def entities(self): pass
    @Getter(EntityFileRP)
    def get_entity(self, identifier:str): pass

    @ResourceDefinition(FogFile)
    def fogs(self): pass
    @Getter(FogFile)
    def get_fog(self, identifier:str): pass

    @ResourceDefinition(ModelFile)
    def model_files(self): pass
    @Getter(ModelFile)
    def get_model_file(self, filepath:str): pass
    @JsonChildResource(ModelFile, Model)
    def models(self): pass
    @ChildGetter(ModelFile, Model)
    def get_model(self, id: str): pass

    @ResourceDefinition(RenderControllerFile)
    def render_controller_files(self): pass
    @Getter(RenderControllerFile)
    def get_render_controller_file(self, filepath:str): pass
    @JsonChildResource(RenderControllerFile, RenderController)
    def render_controllers(self): pass
    @ChildGetter(RenderControllerFile, RenderController)
    def get_render_controller(self, id: str): pass

    @ResourceDefinition(ItemFileRP)
    def items(self): pass
    @Getter(ItemFileRP)
    def get_item(self, identifier:str): pass

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
    def sound_definitions_file(self) -> SoundDefinitionsFile: pass

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