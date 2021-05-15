from __future__ import annotations
from functools import cached_property
from jsonpath_ng import *
from io import TextIOWrapper
from dataclasses import dataclass
from send2trash import send2trash

import os
import json
import glob
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

class JsonResource(Resource):
    def __init__(self, pack:Pack, file_path:str, data=None) -> None:
        super().__init__(pack, self)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.__resources = []
        self.pack = pack
        self.__mark_for_deletion: bool = False

        if data != None:
            self.data = NotifyDict(data, owner=self)
        else:
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

    def save(self, force=False):
        if self.__mark_for_deletion:
            pass

        elif self.dirty or force:
            self.dirty = False
            for resource in self.__resources:
                resource._save(force=force)
            self.pack.save_json(self.file_path, self.data)
            self.dirty = False

            
    def register_resource(self, resource):
        self.__resources.append(resource)
    
    def delete(self):
        self.__mark_for_deletion = True

class SubResource(Resource):
    def __init__(self, parent: Resource, datum: DatumInContext) -> None:
        super().__init__(parent.pack, parent.file)
        self.parent = parent
        self.datum = datum
        self.json_path = datum.full_path
        self.__data = None
        self.id = str(datum.path)
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
        
    def _save(self, force=False):
        if self._dirty or force:
            for resource in self.__resources:
                resource._save(force=force)
            self.json_path.update(self.parent.data, self.data)
            self._dirty = False

class Component(SubResource):
    def __init__(self, entity: JsonResource, group: ComponentGroup, datum: DatumInContext) -> None:
        super().__init__(entity, datum)
        self.entity = entity
        self.group = group

class Event(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        self.__groups_to_remove = []
        self.__groups_to_add = []
    
    @cached_property
    def groups_to_add(self) -> list[ComponentGroup]:
        component_path = parse("add.component_groups.[*]")
        for match in component_path.find(self.data):
            self.__groups_to_add.append(self.parent.get_component_group(match.value))
        return self.__groups_to_add

    @cached_property
    def groups_to_remove(self) -> list[ComponentGroup]:
        component_path = parse("remove.component_groups.[*]")
        for match in component_path.find(self.data):
            self.__groups_to_remove.append(self.parent.get_component_group(match.value))
        return self.__groups_to_remove

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

    def create_entity(self, new_path, data = None):
        self.__entities.append(EntityBP(self, os.path.join("entities", new_path), data = data))


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
    
    @property
    def identifier(self):
        return self.data["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["description"]["identifier"] = identifier
        
class ModelFile(JsonResource):
    def __init__(self, pack: Pack, file_path, data = None) -> None:
        super().__init__(pack, file_path, data)
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
    def __init__(self, pack, path):
        super().__init__(pack, path)
        self.__animations = []
    
    @property
    def identifier(self):
        return self.data["minecraft:client_entity"]["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["minecraft:client_entity"]["description"]["identifier"] = identifier

    @cached_property
    def animations(self) -> list[AnimationRP]:
        animation_path = parse("$.'minecraft:client_entity'.description.animations.*")
        for match in animation_path.find(self.data):
            self.__animations.append(AnimationRP(self, match))
        return self.__animations


class EntityBP(JsonResource):
    def __init__(self, pack, path, data = None):
        super().__init__(pack, path, data=data)
        self.__components = []
        self.__component_groups = []
        self.__events = []

    # Properties
    @property
    def identifier(self):
        return self.data["minecraft:entity"]["description"]["identifier"]
    
    @identifier.setter
    def identifier(self, identifier):
        self.data["minecraft:entity"]["description"]["identifier"] = identifier

    @cached_property
    def events(self) -> list[Event]:
        component_path = parse("$.'minecraft:entity'.events.*")
        for match in component_path.find(self.data):
            self.__events.append(Event(self, match))
        return self.__events

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

    def get_component_group(self, name:str) -> ComponentGroup:
        for group in self.component_groups:
            if group.id == name:
                return group
        raise AssetNotFoundError

    def get_component(self, name) -> Component:
        for component in self.components:
            if component.id == name:
                return component
        raise AssetNotFoundError        

class RpItem(JsonResource):
    def __init__(self):
        pass

class BPItem(JsonResource):
    def __init__(self):
        pass

class ResourcePack(Pack):
    def __init__(self, input_path, project=None):
        super().__init__(input_path, project=project)
        self.__animations = []
        self.__animation_files = []
        self.__entities = []
        self.__model_files = []
        self.__models = []
    
    @cached_property
    def animations(self) -> list[AnimationRP]:
        for animation_file in self.animation_files:
            for animation in animation_file.animations:
                self.__animations.append(animation)
        return self.__animations
    
    @cached_property
    def animation_files(self) -> list[AnimationFileRP]:
        base_directory = os.path.join(self.input_path, "animations")
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            self.__animation_files.append(AnimationFileRP(self, entity_path))
        return self.__animation_files

    @cached_property
    def entities(self) -> list[EntityRP]:
        base_directory = os.path.join(self.input_path, "entity")
        for entity_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            entity_path = os.path.relpath(entity_path, self.input_path)
            self.__entities.append(EntityRP(self, entity_path))
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

    def get_entity(self, identifier:str) -> EntityRP:
        for entity in self.entities:
            if entity.identifier == identifier:
                return entity
        raise AssetNotFoundError 

    def get_model(self, identifier:str) -> Model:
        for model in self.models:
            if model.identifier == identifier:
                return model
        raise AssetNotFoundError

    def create_model_file(self, new_path, data = None) -> ModelFile:
        new_model_file = ModelFile(self, os.path.join("models", new_path), data = data)
        self.__model_files.append(new_model_file)
        return new_model_file

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