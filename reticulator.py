from __future__ import annotations
from functools import cached_property
from jsonpath_ng import *
from io import TextIOWrapper
from enum import Enum

import os
import json
import glob
import copy
import traceback



# GLOBALS
DEBUG = 0

# EXCEPTIONS
class AssetNotFoundError(Exception):
    pass

# SUGAR
def Override(func):
    return func

# GLOBALS

def debug() -> None:
    if DEBUG == 2:
        print(traceback.format_exc())
    elif DEBUG == 1:
        print("Something went wrong...")
    else:
        pass

def print_dict(d) -> None:
    print(json.dumps(d, indent=2))

def get_nested_json(data: dict, json_path: str) -> dict:
    temp = copy.deepcopy(data)
    jsonpath_expr = parse(json_path)
    results = jsonpath_expr.find(temp)
    if len(results) > 1:
        print("Warning! Ambiguous subresource")

    return results[0]

def save_nested_json(data: dict, json_path: str, snippet: dict) -> None:
    pass
    # current = data
    # for key in path:
    #     current = current[key]

    # current[name] = snippet

def get_json_from_path(path:str) -> dict:
    with open(path, "r") as fh:
        return get_json_from_file(fh, path)

def get_json_from_file(fh:TextIOWrapper, path:str) -> dict:
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
            print("ERROR loading: " + path)
            return {}

"""
A dict, which tells its parent when it is edited/saved.
"""
class NotifyDict(dict):
    def __init__(self, *args, owner=None, **kwargs):
        self.__owner = owner
        self.__dirty = False

        if len(args) > 0:
            for key, value in args[0].items():
                if isinstance(value, dict):
                    args[0][key] = NotifyDict(value, owner=self.__owner)
                if isinstance(value, list):
                    args[0][key] = NotifyList(value, owner=self.__owner)
        super().__init__(*args, **kwargs)

    def __setitem__(self, attr, value):
        if isinstance(value, dict):
            value = NotifyDict(value, owner=self.__owner)
        if isinstance(value, list):
            value = NotifyList(value, owner=self.__owner)
        super().__setitem__(attr, value)
        self.dirty = True
    
    @property
    def dirty(self):
        return self.__dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self.__dirty = dirty
        if(self.__owner != None):
            self.__owner.dirty = dirty

class NotifyList(list):
    def __init__(self, *args, owner=None, **kwargs):
        self.__dirty = False
        self.__owner = owner
        if len(args) > 0:
            for i in range(len(args[0])):
                if isinstance(args[0][i], dict):
                    args[0][i] = NotifyDict(args[0][i], owner=self.__owner)
                if isinstance(args[0][i], list):
                    args[0][i] = NotifyList(args[0][i], owner=self.__owner)
        super().__init__(*args, **kwargs)

    def __setitem__(self, attr, value):
        if isinstance(value, dict):
            value = NotifyDict(value, owner=self.__owner)
        if isinstance(value, list):
            value = NotifyList(value, owner=self.__owner)
        super().__setitem__(attr, value)
        self.dirty = True

    @property
    def dirty(self):
        return self.__dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self.__dirty = dirty
        if(self.__owner != None):
            self.__owner.dirty = dirty


# ENUMS
class TextureType(Enum):
    PNG = 1
    TGA = 2

class PackLocation(Enum):
    PACK = 0
    DEV = 1
    WORLD = 2

class Resource():
    def __init__(self, pack: Pack, file_path: str) -> None:
        self.pack = pack
        self.file_path = file_path
        self.dirty = False
    
    def save(self) -> None:
        raise NotImplementedError

class SubResource():
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        self.parent = parent
        self.datum = datum
        self.json_path = datum.full_path
        self.__data = None
        self.__dirty = False
        self.parent.register_resource(self)
        self.name = str(datum.path)
        self.resources = []
    
    @property
    def data(self):
        raw_data = self.datum.value
        if isinstance(raw_data, dict):
            self.__data = NotifyDict(raw_data, owner=self)
        if isinstance(raw_data, list):
            self.__data = NotifyList(raw_data, owner=self)

        return self.__data

    @data.setter
    def data(self, data):
        self.__data = data

    @property
    def dirty(self):
        return self.__dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self.__dirty = dirty
        self.parent.dirty = dirty

    def __str__(self):
        return json.dumps(self.data, indent=2)

    def register_resource(self, resource):
        self.resources.append(resource)
        
    def save(self):
        if self.__dirty:
            for resource in self.resources:
                resource.save()
            self.datum.full_path.update(self.parent.data, self.data)
            self.__dirty = False
            self.parent.save()


class Component(SubResource):
    def __init__(self, entity: JsonResource, group: ComponentGroup, datum: DatumInContext) -> None:
        super().__init__(entity, datum)
        self.entity = entity
        self.group = group

class ComponentGroup(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        self.__components = []
    
    @cached_property
    def components(self) -> list[Component]:
        component_path = parse("*")
        for match in component_path.find(self.data):
            self.__components.append(Component(self.parent, self, match))
        return self.__components
        
class JsonResource(Resource):
    def __init__(self, pack:Pack, file_path:str) -> None:
        super().__init__(pack, file_path)
        self.resources = []
        self.pack = pack
        self.__dirty = False
        self.data = NotifyDict(self.pack.load_json(self.file_path))
        self.pack.register_resource(self)

    def register_resource(self, resource):
        self.resources.append(resource)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @property
    def dirty(self):
        return self.__dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self.__dirty = dirty

    @Override
    def save(self):
        if self.dirty:
            self.dirty = False
            print("Saving: " + self.file_path)
            for resource in self.resources:
                resource.save()
            self.pack.save_json(self.file_path, self.data)


class Manifest(JsonResource):
    def __init__(self, pack, path):
        super().__init__(pack, path)

    def get_uuid(self):
        self.data.get("header",{}).get("uuid","")
    
    def set_uuid(self, uuid):
        self.data["header"]["uuid"] = uuid

    def get_dependencies(self):
        pass

class Pack():
    def __init__(self, input_path: str, project=None):
        self.resources = []
        self.__project = project
        self.input_path = input_path
        self.output_path = input_path
        self.manifest = self.__get_manifest()

    @cached_property
    def project(self) -> Project:
        return self.__project

    def set_output_location(self, output_path: str) -> None:
        self.output_path = output_path

    def __get_manifest(self) -> Manifest:
        return Manifest(self, "manifest.json")

    def load_json(self, local_path):
        return self.__load_json(os.path.join(self.input_path, local_path))

    def save_json(self, local_path, data):
        return self.__save_json(os.path.join(self.output_path, local_path), data)

    def save(self):
        for resource in self.resources:
            resource.save()

    def register_resource(self, resource):
        self.resources.append(resource)

    def get_entity(self, identifier):
        raise NotImplementedError
        
    # Static Methods
    @staticmethod
    def __load_json(file_path):
        if not os.path.exists(file_path):
            print("Bad filepath: " + file_path)
            return {}
        return get_json_from_path(file_path)
    
    @staticmethod
    def __save_json(file_path, data):
        dir_name = os.path.dirname(file_path)

        if not os.path.exists(dir_name):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w+") as f:
            return json.dump(data, f, indent=2)


class FilePathResource(Resource):
    def __init__(self):
        pass

class BehaviorPack(Pack):
    def __init__(self, input_path, project=None):
        super().__init__(input_path, project=project)
        self.__entities = []

    # Properties
    @cached_property
    def entities(self) -> list[EntityBP]:
        base_directory = os.path.join(self.input_path, "entities")
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            self.__entities.append(EntityBP(self, entity_path))
            
        return self.__entities

    # Methods
    def get_entity(self, identifier:str) -> EntityBP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError

class Model(SubResource):
    def __init__(self, parent: JsonResource, path: str, name: str) -> None:
        super().__init__(parent, path, name)

class ModelFile(JsonResource):
    def __init__(self, pack: Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.__models = []
    
    @cached_property
    def models(self):
        for key in self.data.get("minecraft:geometry", []):
            self.__models.append(Model(self, ["minecraft:geometry"], key))
        return self.__models

class AnimationFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.__animations = []

    @cached_property
    def animations(self):
        for key in self.data.get("animations", {}).keys():
            self.__animations.append(AnimationRP(self, ["animations"], key))
        return self.__animations        
            
class AnimationRP(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)

class EntityRP(JsonResource):
    # Init
    def __init__(self, pack, path):
        super().__init__(pack, path)
        self.__animations = []
        self.__entityBP = None
    
    # Properties
    @cached_property
    def animations(self) -> list[AnimationRP]:
        animation_path = parse("$.'minecraft:client_entity'.description.animations.*")
        for match in animation_path.find(self.data):
            self.__animations.append(AnimationRP(self, match))
        return self.__animations
    
    @cached_property
    def entityBP(self) -> EntityBP:
        self.__entityBP = self.pack.project.behavior_pack.get_entity(self.identifier)
        return self.__entityBP

    @property
    def identifier(self):
        return self.data["minecraft:client_entity"]["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["minecraft:client_entity"]["description"]["identifier"] = identifier

    # Loaders
    def __load_animations(self) -> None:
        for key in self.data.get("minecraft:client_entity", {}).get("description", {}).get("animations", {}).keys():
            name = self.data.get("minecraft:client_entity", {}).get("description", {}).get("animations", {}).get(key)
            for animation in self.pack.animations:
                if animation.name == name:
                    self.__animations.append(animation)

class EntityBP(JsonResource):
    def __init__(self, pack, path):
        super().__init__(pack, path)
        self.__components = []
        self.__component_groups = []

    # Properties
    @property
    def identifier(self):
        return self.data["minecraft:entity"]["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["minecraft:entity"]["description"]["identifier"] = identifier

    @cached_property
    def components(self) -> list[Component]:
        component_path = parse("$.'minecraft:entity'.components.*")
        for match in component_path.find(self.data):
            self.__components.append(Component(self, None, match))
        return self.__components
    
    @cached_property
    def component_groups(self) -> list[ComponentGroup]:
        group_path = parse("$.'minecraft:entity'.component_groups.*")
        for match in group_path.find(self.data):
            self.__component_groups.append(ComponentGroup(self, match))
        return self.__component_groups

    # Methods
    def get_identifier(self):
        return self.identifier

    def get_component_group(self, name:str) -> ComponentGroup:
        for group in self.component_groups:
            if group.name == name:
                return group
        raise AssetNotFoundError

    def get_component(self, name) -> Component:
        for component in self.components:
            if component.name == name:
                return component
        raise AssetNotFoundError        

class RpItem(JsonResource):
    def __init__(self):
        pass

class Texture(FilePathResource):
    def __init__(self):
        pass

    def get_texture_type(self):
        pass

class BPItem(JsonResource):
    def __init__(self):
        pass

class ResourcePack(Pack):
    # Init
    def __init__(self, input_path, project=None):
        super().__init__(input_path, project=project)
        self.__animations = []
        self.__animation_files = []
        self.__entities = []
        self.__model_files = []
        self.__models = []
    
    # Properties
    @cached_property
    def animations(self) -> list[AnimationRP]:
        self.__load_animations()
        return self.__animations
    
    @cached_property
    def animation_files(self) -> list[AnimationFileRP]:
        self.__load_animation_files()
        return self.__animation_files

    @cached_property
    def entities(self) -> list[EntityRP]:
        self.__load_entities()
        return self.__entities

    @cached_property
    def model_files(self) -> list[ModelFile]:
        self.__load_model_files()
        return self.__model_files
    
    @cached_property
    def models(self) -> list[Model]:
        self.__load_models()
        return self.__models

    # Methods
    def get_entity(self, identifier:str) -> EntityRP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 

    # Loaders
    def __load_models(self) -> None:
        for model_file in self.model_files:
            for model in model_file.models:
                self.__models.append(model)

    def __load_model_files(self) -> None:
        base_directory = os.path.join(self.input_path, "models")
        for model_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            model_path = os.path.relpath(model_path, self.input_path)
            self.__model_files.append(ModelFile(self, model_path))

    def __load_animation_files(self) -> None:
        base_directory = os.path.join(self.input_path, "animations")
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            self.__animation_files.append(AnimationFileRP(self, entity_path))

    def __load_entities(self) -> None:
        base_directory = os.path.join(self.input_path, "entity")
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            self.__entities.append(EntityRP(self, entity_path))

    def __load_animations(self) -> None:
        for animation_file in self.animation_files:
            for animation in animation_file.animations:
                self.__animations.append(animation)

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

    def save(self):
        self.__behavior_pack.save()
        self.__resource_pack.save()

class Reticulator():
    def __init__(self, username=None):
        self.username = username if username != None else os.getlogin()
        self.com_mojang_path = "C:\\Users\\{}\\AppData\\Local\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang".format(username)

    def load_project_from_path(self, input_path) -> Project:
        return Project(input_path)

    def load_behavior_pack_from_path(self, input_path) -> BehaviorPack:
        return BehaviorPack(input_path)
    
    def load_behavior_pack_from_folder_name(self, pack_name):
        search_location = os.path.join(self.com_mojang_path, "development_behavior_packs");
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

def _test():
    assert 1 == 1

if __name__ == '__main__':
    _test()