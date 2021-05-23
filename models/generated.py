from __future__ import annotations
from functools import cached_property
from typing import Any
from jsonpath_ng import *
from io import TextIOWrapper
from dataclasses import dataclass
from send2trash import send2trash
from functools import wraps

import os
import json
import glob

# Base exception class
class ReticulatorException(Exception):
    pass

# Called when a "floating" asset attempts to access its parent pack, for example when saving
class FloatingAssetError(ReticulatorException):
    pass

# Called when attempting to access an asset that does not exist, for example getting an entity by name
class AssetNotFoundError(ReticulatorException):
    pass

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

class Resource():
    def __init__(self, pack: Pack, file: JsonResource) -> None:
        # Public
        self.pack = pack
        self.file = file

        # Protected
        self._data = None
        self._dirty = False
    
    def set(self, parse_path: str, new_data: Any):
        json_path = parse(parse_path)
        json_path.update(self.data, new_data)

    def get(self, parse_path: str):
        results : list[DatumInContext] = parse(parse_path).find(self.data)
        # If single, return a single element (or return multiple)
        if len(results) == 1:
            return results[0].value
        else:
            out_results = []
            for result in results:
                out_results.append(result.value)
            return out_results

    @property
    def data(self):
        raise NotImplementedError

    @data.setter
    def data(self, data):
        raise NotImplementedError

    @property
    def dirty(self):
        raise NotImplementedError

    @dirty.setter
    def dirty(self, dirty):
        raise NotImplementedError

class JsonResource(Resource):
    def __init__(self, pack: Pack = None, file_path: str = None, data: dict = None) -> None:
        super().__init__(pack, self)
        self.pack = pack

        self.file_path = file_path

        if file_path:
            self.file_name = os.path.basename(file_path)

        self.__resources = []
        self.__mark_for_deletion: bool = False

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

    def save(self, force=False):
        # Don't allow saving
        if not self.pack:
            raise FloatingAssetError()

        # TODO Should we also delete these files manually from disk?
        # Do not save files that are marked for deletion
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
        self.id = str(datum.path)
        self.__resources: SubResource = []
        self.parent.register_resource(self)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    @property
    def data(self):
        if self._data == None:
            raw_data = self.datum.value
            if isinstance(raw_data, dict):
                self._data = NotifyDict(raw_data, owner=self)
            if isinstance(raw_data, list):
                self._data = NotifyList(raw_data, owner=self)
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
        self.parent.dirty = dirty

    def register_resource(self, resource: SubResource) -> None:
        self.__resources.append(resource)
        
    def _save(self, force=False):
        if self._dirty or force:
            for resource in self.__resources:
                resource._save(force=force)
            self.json_path.set(self.parent.data, self.data)
            self._dirty = False

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

    def get_entity(self, identifier):
        raise NotImplementedError
        
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


class ResourcePack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__animation_files = []
        self.__entities = []
        self.__model_files = []
        
    
    @cached_property
    def animation_files(self) -> list[AnimationFileRP]:
        base_directory = os.path.join(self.input_path, "animations")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_files.append(AnimationFileRP(self, local_path))
            
        return self.__animation_files

    @cached_property
    def entities(self) -> list[EntityRP]:
        base_directory = os.path.join(self.input_path, "entity")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityRP(self, local_path))
            
        return self.__entities

    @cached_property
    def model_files(self) -> list[ModelFile]:
        base_directory = os.path.join(self.input_path, "models")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__model_files.append(ModelFile(self, local_path))
            
        return self.__model_files

    
class BehaviorPack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__entities = []
        self.__animation_controller_files = []
        
    
    @cached_property
    def entities(self) -> list[EntityBP]:
        base_directory = os.path.join(self.input_path, "entities")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityBP(self, local_path))
            
        return self.__entities

    @cached_property
    def animation_controller_files(self) -> list[AnimationControllerFile]:
        base_directory = os.path.join(self.input_path, "animation_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_controller_files.append(AnimationControllerFile(self, local_path))
            
        return self.__animation_controller_files

    
class ItemBP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__components = []
        
    
    @property
    def identifier(self):
        return self.get("'minecraft:item'.description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("'minecraft:item'.description.identifier", identifier)

    
    @cached_property
    def components(self) -> list[Component]:
        internal_path = parse("$.'minecraft:item'.components")
        for match in internal_path.find(self.data):
            self.__components.append(Component(self, match))
        return self.__components

    
class EntityRP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__animations = []
        
    
    
    @cached_property
    def animations(self) -> list[AnimationRP]:
        internal_path = parse("$.'minecraft:client_entity'.description.animations.*")
        for match in internal_path.find(self.data):
            self.__animations.append(AnimationRP(self, match))
        return self.__animations

    
class AnimationFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__states = []
        
    
    
    @cached_property
    def states(self) -> list[AnimationControllerState]:
        internal_path = parse("states.*")
        for match in internal_path.find(self.data):
            self.__states.append(AnimationControllerState(self, match))
        return self.__states

    
class EntityBP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__component_groups = []
        self.__components = []
        self.__events = []
        
    
    @property
    def identifier(self):
        return self.get("'minecraft:entity'.description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("'minecraft:entity'.description.identifier", identifier)

    
    @cached_property
    def component_groups(self) -> list[ComponentGroup]:
        internal_path = parse("$.'minecraft:entity'.component_groups.*")
        for match in internal_path.find(self.data):
            self.__component_groups.append(ComponentGroup(self, match))
        return self.__component_groups

    @cached_property
    def components(self) -> list[Component]:
        internal_path = parse("$.'minecraft:entity'.component_groups.*")
        for match in internal_path.find(self.data):
            self.__components.append(Component(self, match))
        return self.__components

    @cached_property
    def events(self) -> list[Event]:
        internal_path = parse("$.'minecraft:entity'.events.*")
        for match in internal_path.find(self.data):
            self.__events.append(Event(self, match))
        return self.__events

    
class ModelFile(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__models = []
        
    
    
    @cached_property
    def models(self) -> list[Model]:
        internal_path = parse("'minecraft:geometry'.[*]")
        for match in internal_path.find(self.data):
            self.__models.append(Model(self, match))
        return self.__models

    
class AnimationControllerFile(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__animation_controllers = []
        
    
    
    @cached_property
    def animation_controllers(self) -> list[AnimationController]:
        internal_path = parse("animation_controllers.*")
        for match in internal_path.find(self.data):
            self.__animation_controllers.append(AnimationController(self, match))
        return self.__animation_controllers

    
class AnimationControllerState(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        
    
    
class Model(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        self.__bones = []
        
    
    @cached_property
    def bones(self) -> list[Bone]:
        internal_path = parse("bones.[*]")
        for match in internal_path.find(self.data):
            self.__bones.append(Bone(self, match))
        return self.__bones

    
class AnimationRP(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        
    
    
class AnimationController(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        self.__states = []
        
    
    @cached_property
    def states(self) -> list[AnimationControllerState]:
        internal_path = parse("states.*")
        for match in internal_path.find(self.data):
            self.__states.append(AnimationControllerState(self, match))
        return self.__states

    
class ComponentGroup(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        self.__components = []
        
    
    @cached_property
    def components(self) -> list[Component]:
        internal_path = parse("*")
        for match in internal_path.find(self.data):
            self.__components.append(Component(self, match))
        return self.__components

    
class Component(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext, component_group: ComponentGroup = None) -> None:
        super().__init__(parent, datum)
        self.component_group = component_group
        
        
    
    
class Event(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        self.__groups_to_add = []
        self.__groups_to_remove = []
        
    
    @cached_property
    def groups_to_add(self) -> list[ComponentGroup]:
        internal_path = parse("add.component_groups.[*]")
        for match in internal_path.find(self.data):
            self.__groups_to_add.append(self.parent.get_component_group(match.value))
        return self.__groups_to_add

    @cached_property
    def groups_to_remove(self) -> list[ComponentGroup]:
        internal_path = parse("remove.component_groups.[*]")
        for match in internal_path.find(self.data):
            self.__groups_to_remove.append(self.parent.get_component_group(match.value))
        return self.__groups_to_remove

    
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

    
class Cube(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        
    
    