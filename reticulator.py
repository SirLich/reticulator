from __future__ import annotations
from functools import cached_property
from jsonpath_ng import *
from io import TextIOWrapper
from enum import Enum

import os
import json
import glob
import copy
import sys
import traceback

# GLOBALS
DEBUG = 0

# EXCEPTIONS
class AssetNotFoundError(Exception):
    pass

# GLOBALS

def debug() -> None:
    if DEBUG == 2:
        print(traceback.format_exc())
    elif DEBUG == 1:
        print("Something went wrong...")
    else:
        pass

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

#TODO: Add notify string, int, etc

class NotifyDict(dict):
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
    def __init__(self, *args, owner: Resource = None, **kwargs):
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

        if self.__getitem__(attr) != value:
            if(self.__owner != None):
                self.__owner.dirty = True
        
        super().__setitem__(attr, value)


class Resource():
    def __init__(self, pack: Pack, file: JsonResource) -> None:
        self.pack = pack
        self.file = file
        self._dirty = False

    @property
    def dirty(self):
        raise NotImplementedError

    @dirty.setter
    def dirty(self, dirty):
        raise NotImplementedError       

class SubResource(Resource):
    def __init__(self, parent: Resource, datum: DatumInContext) -> None:
        # print("Making {}: {}".format(str(self.__class__.__name__) , str(datum.path)))
        super().__init__(parent.pack, parent.file)
        self.parent = parent
        self.datum = datum
        self.json_path = datum.full_path
        self.__data = None
        self.name = str(datum.path)
        self.__resources: SubResource = []
        self.parent.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @property
    def data(self):
        if self.__data == None:
            raw_data = self.datum.value
            if isinstance(raw_data, dict):
                self.__data = NotifyDict(raw_data, owner=self)
            if isinstance(raw_data, list):
                self.__data = NotifyList(raw_data, owner=self)
        return self.__data

    @data.setter
    def data(self, data):
        self.dirty = True
        self.__data = data

    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty
        self.parent.dirty = dirty

    def register_resource(self, resource: SubResource) -> None:
        self.__resources.append(resource)
        
    def _save(self):
        if self._dirty:
            for resource in self.__resources:
                resource._save()
            self.json_path.update(self.parent.data, self.data)
            self._dirty = False
            # print("Saving...", self.__class__.__name__, self.name)

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
            self.__components.append(Component(self, self, match))
        return self.__components

        
class JsonResource(Resource):
    def __init__(self, pack:Pack, file_path:str) -> None:
        super().__init__(pack, self)
        self.file_path = file_path
        self.__resources = []
        self.pack = pack
        self.data = NotifyDict(self.pack.load_json(self.file_path), owner=self)
        self.pack.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @property
    def dirty(self):
        return self._dirty
    
    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty


    def save(self):
        if self.dirty:
            self.dirty = False
            for resource in self.__resources:
                resource._save()
            self.pack.save_json(self.file_path, self.data)
            self.dirty = False
            # print("Saving...", self.__class__.__name__, self.file_path)

            
    def register_resource(self, resource):
        self.__resources.append(resource)


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

class Cube(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)

class Bone(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        self.__cubes = []
    
    @cached_property
    def cubes(self) -> list[Cube]:
        internal_path = parse("cubes[*]")
        for match in internal_path.find(self.data):
            self.__cubes.append(Cube(self, match))
        return self.__cubes

class Model(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        self.__bones = []
        self.__cubes = []
    
    @cached_property
    def cubes(self) -> list[Cube]:
        for bone in self.bones:
            for cube in bone.cubes:
                self.__cubes.append(cube)
        return self.__cubes

    @cached_property
    def bones(self) -> list[Bone]:
        internal_path = parse("bones.[*]")
        for match in internal_path.find(self.data):
            self.__bones.append(Bone(self, match))
        return self.__bones
        
class ModelFile(JsonResource):
    def __init__(self, pack: Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.__models = []
    
    @cached_property
    def models(self) -> list[Model]:
        model_path = parse("'minecraft:geometry'.[*]")
        for match in model_path.find(self.data):
            self.__models.append(Model(self, match))
        return self.__models

class AnimationFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path) -> None:
        super().__init__(pack, file_path)
        self.__animations = []

    @cached_property
    def animations(self):
        animation_path = parse("animations.*")
        for match in animation_path.find(self.data):
            self.__animations.append(AnimationRP(self, match))
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
        base_directory = os.path.join(self.input_path, "models")
        for model_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            model_path = os.path.relpath(model_path, self.input_path)
            self.__model_files.append(ModelFile(self, model_path))
        return self.__model_files
    
    @cached_property
    def models(self) -> list[Model]:
        for model_file in self.model_files:
            for model in model_file.models:
                self.__models.append(model)   
        return self.__models

    # Methods
    def get_entity(self, identifier:str) -> EntityRP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 

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