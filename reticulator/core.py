from __future__ import annotations


"""
Module which handles core Reticulator functions. This class is generic, 
and could theoretically be split into it's own class.
"""

import os
import json
import glob
import functools 

from pathlib import Path
from functools import cached_property
from typing import Union, TypeVar, Any

import dpath

NO_ARGUMENT = object()
TEXTURE_EXTENSIONS = ["png", "jpg", "jpeg", "tga"]
SOUND_EXTENSIONS = ["wav", "fsb", "ogg"]

T = TypeVar('T')

class TypeInfo:
    """
    Class for encapsulating the arguments that are passed to sub-resource based
    decorators.

    :jsonpath: The jsonpath, from where this resource can be located
    :child_cls: The class of the resource which can be accessed from this resource
        For example `AnimationRP` can be accessed from `AnimationFileRP`
    """
    
    def __init__(self, *, jsonpath="", filepath="", attribute="", getter_attribute="", extension=".json", plural=None, child_cls=None):
        self.jsonpath = jsonpath
        self.filepath = filepath
        self.attribute = attribute

        if plural == None:
            self.plural = attribute + "s"
        else:
            self.plural = plural
        self.child_cls = child_cls
        self.getter_attribute = getter_attribute
        self.extension = extension

    def __repr__(self) -> str:
        return "TypeInfo: " +  str(vars(self))

def convert_to_notify_structure(data: Union[dict, list], parent: Resource) -> Union[NotifyDict, NotifyList]:
    """
    Converts a dict or list to a notify structure.
    """
    if isinstance(data, dict):
        return NotifyDict(data, owner=parent)

    if isinstance(data, list):
        return NotifyList(data, owner=parent)

    return data


def ImplementsResource(*args : JsonFileResource):
    def inner(parent_cls):
        for sub_cls in args:
            cls_type_info : TypeInfo = sub_cls.type_info

            attribute = cls_type_info.attribute
            plural = cls_type_info.plural

            @ResourceDefinition(sub_cls)
            def x(parent_cls): pass
            setattr(parent_cls, plural, x)
            x.__set_name__(parent_cls, plural) # See: CachedProperty docs.

            @Getter(sub_cls)
            def get_x(parent_cls, id: str): pass
            setattr(parent_cls, f"get_{attribute}", get_x)

            @ResourceAdder(sub_cls)
            def add_x(parent_cls, filepath: str, data: dict): pass
            setattr(parent_cls, f"add_{attribute}", add_x)

            child_cls = cls_type_info.child_cls
            if child_cls != None:
                @JsonChildResource(sub_cls, child_cls)
                def child_x(self): pass
                setattr(parent_cls, child_cls.type_info.plural, child_x)

                @ChildGetter(sub_cls, child_cls)
                def get_child_x(self, id: str): pass
                setattr(parent_cls, f"get_{child_cls.type_info.attribute}", get_child_x)

        return parent_cls

    return inner


def ImplementsSubResource(*args : JsonSubResource):
    """
    Class Decorator which interjects functions to deal with subresources.
    """

    def inner(parent_cls):
        for sub_cls in args:
            cls_type_info : TypeInfo = sub_cls.type_info

            attribute = cls_type_info.attribute
            plural = cls_type_info.plural

            @SubResourceDefinition(sub_cls)
            def components(parent_cls): pass
            setattr(parent_cls, plural, components)
            components.__set_name__(parent_cls, plural)

            @Getter(sub_cls)
            def get_x(parent_cls, id: str): pass
            setattr(parent_cls, f"get_{attribute}", get_x)

            @SubResourceAdder(sub_cls)
            def add_x(parent_cls, name: str, data: dict): pass
            setattr(parent_cls, f"add_{attribute}", add_x)

        return parent_cls

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
    
    parent_attribute = parent_cls.type_info.plural
    child_attribute = child_cls.type_info.plural

    def decorator(func) -> cached_property[list[T]]:
        @property
        @functools.wraps(func)
        def wrapper(self) -> list[T]:
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
    attribute_plural = cls.type_info.plural

    def decorator(func) -> cached_property[list[T]]:
        @cached_property
        @functools.wraps(func)
        def wrapper(self) -> list[T]:
            setattr(self, attribute_plural, [])
            for path, data in self.get_data_at(jsonpath):
                getattr(self, attribute_plural).append(cls(parent = self, json_path = path, data = data))
            return getattr(self, attribute_plural)
        return wrapper
    return decorator


def Getter(cls : T):
    """
    Decorator which allows you to get a resource. For example getting a component
    from an entity.
    """
    attribute_plural = cls.type_info.plural
    getter_attribute = cls.type_info.getter_attribute
    def decorator(func) -> T:
        @functools.wraps(func)
        def wrapper(self, compare):
            for child in getattr(self, attribute_plural):
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
    parent_attribute = parent_cls.type_info.plural
    child_attribute = child_cls.type_info.plural
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

def ResourceAdder(cls : Resource):
    """
    This decorator allows you to inject SubResources into your Resources.
    """
    base_filepath = cls.type_info.filepath
    attribute = cls.type_info.plural

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, filepath, data):
            new_filepath = base_filepath + "/" + filepath
            new_object = cls(data=data, pack=self, filepath=new_filepath)

            if new_object:
                getattr(self, attribute).append(new_object)
                return new_object
            else:
                raise ReticulatorException()

        return wrapper
    return decorator

def SubResourceAdder(cls : Resource):
    """
    This decorator allows you to inject SubResources into your Resources.
    """
    jsonpath = cls.type_info.jsonpath
    attribute = cls.type_info.plural

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