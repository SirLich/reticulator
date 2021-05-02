from __future__ import annotations
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
    DEV = 1
    WORLD = 2
    PACK = 0

# CLASSES
class Resource():
    def __init__(self, pack: Pack, path: str) -> None:
        self.pack = pack
        self.path = path
    
    def save(self) -> None:
        raise NotImplementedError

class SubResource():
    def __init__(self, parent:JsonResource, path:str, name:str) -> None:
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
    def __init__(self, parent, path, name):
        super().__init__(parent, path, name)
        self.components = self.__load_components()
        
    def __load_components(self) -> list[Component]:
        components = []
        for key in get_nested_json(self.parent.data, self.path, self.name):
            childpath = copy.deepcopy(self.path)
            childpath.append(self.name)
            components.append(Component(self.parent, self, childpath, key))
        
        return components

class Component(SubResource):
    def __init__(self, entity, group, path, name):
        super().__init__(entity, path, name)
        self.entity = entity
        self.group = group


class JsonResource(Resource):
    def __init__(self, pack, path):
        super().__init__(pack, path)
        self.resources = []
        self.pack = pack
        self.data = self.pack.load_json(self.path)
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
        self.entities = self.__load_entities()

    def __load_entities(self) -> list[EntityBP]:
        base_directory = os.path.join(self.input_path, "entities")
        entities = []
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            
            
            entities.append(EntityBP(self, entity_path))
            
        
        return entities

    def get_entities(self) -> list[EntityBP]:
        return self.entities
    
    def get_entity(self, identifier:str) -> EntityBP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 

class EntityBP(JsonResource):
    def get_identifier(self):
        return self.identifier

    def get_group(self, name:str) -> ComponentGroup:
        for group in self.groups:
            if group.name == name:
                return group
        raise AssetNotFoundError


    def get_component(self, name) -> Component:
        for component in self.get_components():
            if component.name == name:
                return component
        raise AssetNotFoundError

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

    def __init__(self, pack, path):
        super().__init__(pack, path)

        self.identifier = self.data["minecraft:entity"]["description"]["identifier"]
        self.components = self.__load_components()
        self.component_groups = self.__load_component_groups()

class RpItem(JsonResource):
    def __init__(self):
        pass

class Texture(FilePathResource):
    def __init__(self):
        pass

    def get_texture_type(self):
        pass

class BpItem(JsonResource):
    def __init__(self):
        pass

class ResourcePack(Pack):
    def __init__(self):
        pass

    def get_items():
        pass

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

    def load_resource_pack_from_path(self):
        pass

    def get_resource_packs(self):
        pass

    def get_behavior_packs(self):
        pass

def _test():
    assert 1 == 1

if __name__ == '__main__':
    _test()