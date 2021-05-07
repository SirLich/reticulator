from __future__ import annotations
# from cached_property import cached_property

from functools import cached_property

from io import TextIOWrapper
import os
import json
import glob
import copy
import traceback

from enum import Enum

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

def get_nested_json(data: dict, path: list, name: str) -> dict:
    temp = copy.deepcopy(data)
    temp_path = copy.deepcopy(path)
    temp_path.append(name)

    for child in temp_path:
        temp = temp[child]

    return temp

def save_nested_json(data: dict, path: list, name: str, snippet: dict) -> None:
    current = data
    for key in path:
        current = current[key]

    current[name] = snippet

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
    
    def save(self) -> None:
        raise NotImplementedError

class SubResource():
    def __init__(self, parent: JsonResource, path: str, name: str) -> None:
        self.parent = parent
        self.path = path
        self.name = name
        self.data = get_nested_json(parent.data, path, name)
        self.parent.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    def save(self):
        save_nested_json(self.parent.data, self.path, self.name, self.data)

class ComponentGroup(SubResource):
    # Init
    def __init__(self, parent, path, name):
        super().__init__(parent, path, name)
        self.components = []
    
    # Properties
    @cached_property
    def components(self):
        return self.__load_components()
    
    # Private loaders
    def __load_components(self) -> list[Component]:
        components = []
        for key in get_nested_json(self.parent.data, self.path, self.name):
            childpath = copy.deepcopy(self.path)
            childpath.append(self.name)
            components.append(Component(self.parent, self, childpath, key))
        
        return components

class Component(SubResource):
    # Init
    def __init__(self, entity, group, path, name):
        super().__init__(entity, path, name)
        self.entity = entity
        self.group = group

class JsonResource(Resource):
    # Init
    def __init__(self, pack:Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.resources = []
        self.pack = pack
        self.data = self.pack.load_json(self.file_path)
        self.pack.register_resource(self)

    def register_resource(self, resource):
        self.resources.append(resource)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @Override
    def save(self):
        for resource in self.resources:
            resource.save()
        self.pack.save_json(self.path, self.data)


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
    def __init__(self, input_path: str):
        self.resources = []
        self.input_path = input_path
        self.output_path = input_path
        self.manifest = self.__get_manifest()

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
    def __init__(self, input_path):
        super().__init__(input_path)
        self._entities = []

    # Properties
    @cached_property
    def entities(self) -> list[EntityBP]:
        self._entities = self.__load_entities()
        return self._entities
    
    # Methods
    def get_entity(self, identifier:str) -> EntityBP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 
    
    # Private loaders
    def __load_entities(self) -> list[EntityBP]:
        base_directory = os.path.join(self.input_path, "entities")
        entities = []
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            
            
            entities.append(EntityBP(self, entity_path))
            
        return entities

class AnimationFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.__animations = []

    @cached_property
    def animations(self):
        self.__load_animations()
        return self.__animations

    def __load_animations(self) -> list[AnimationRP]:
        for key in self.data.get("animations", {}).keys():
            self.__animations.append(AnimationRP(self, ["animations"], key))
            

class AnimationRP(SubResource):
    def __init__(self, parent: JsonResource, path: str, name: str) -> None:
        super().__init__(parent, path, name)

class EntityRP(JsonResource):
    # Init
    def __init__(self, pack, path):
        super().__init__(pack, path)
        self.__animations = []
    
    # Properties
    @cached_property
    def animations(self) -> list[AnimationRP]:
        self.__load_animations()
        return self.__animations
    
    # Properties
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

        self._identifier = ""
        self._components = []
        self._component_groups = []

    # Properties
    @property
    def identifier(self):
        return self.data["minecraft:entity"]["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["minecraft:entity"]["description"]["identifier"] = identifier

    @cached_property
    def components(self):
        return self.__load_components()
    
    @cached_property
    def component_groups(self):
        return self.__load_component_groups()

    # Methods
    def get_identifier(self):
        return self.identifier

    def get_component_group(self, name:str) -> ComponentGroup:
        for group in self.component_groups:
            if group.name == name:
                return group
        raise AssetNotFoundError

    def get_component(self, name) -> Component:
        for component in self.get_components():
            if component.name == name:
                return component
        raise AssetNotFoundError

    # Private loaders
    def __load_component_groups(self) -> list[ComponentGroup]:
        component_groups = []
        for key in self.data.get("minecraft:entity", {}).get("component_groups", {}).keys():
            component_groups.append(ComponentGroup(self, ["minecraft:entity", "component_groups"], key))

        return component_groups

    def __load_components(self) -> list[Component]:
        components = []
        for key in self.data.get("minecraft:entity", {}).get("components", {}).keys():
            components.append(Component(self, None, ["minecraft:entity", "components"], key))
        
        return components

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
    def __init__(self, input_path):
        super().__init__(input_path)
        self.__animations = []
        self.__animation_files = []
        self.__entities = []
    
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

    # Methods
    def get_entity(self, identifier:str) -> EntityRP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 

    # Loaders
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
            

class Reticulator():
    def __init__(self, username=None):
        username = username if username != None else os.getlogin()
        self.path = "C:\\Users\\{}\\AppData\\Local\\Packages\\Microsoft.MinecraftUWP_8wekyb3d8bbwe\\LocalState\\games\\com.mojang".format(username)

    def load_behavior_pack_from_path(self, input_path):
        return BehaviorPack(input_path)
    
    def load_behavior_pack_from_folder_name(self, pack_name):
        search_location = os.path.join(self.path, "development_behavior_packs");
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