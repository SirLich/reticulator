


class ResourcePack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__animation_controller_files = []
        self.__animation_files = []
        self.__entities = []
        self.__model_files = []
        self.__render_controllers = []
        self.__items = []
        
    
    @cached_property
    def animation_controller_files(self) -> list[AnimationControllerFileRP]:
        base_directory = os.path.join(self.input_path, "animation_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_controller_files.append(AnimationControllerFileRP(self, local_path))
            
        return self.__animation_controller_files

    @cached_property
    def animation_files(self) -> list[AnimationFileRP]:
        base_directory = os.path.join(self.input_path, "animations")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_files.append(AnimationFileRP(self, local_path))
            
        return self.__animation_files

    @cached_property
    def entities(self) -> list[EntityFileRP]:
        base_directory = os.path.join(self.input_path, "entity")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityFileRP(self, local_path))
            
        return self.__entities

    @cached_property
    def model_files(self) -> list[ModelFileRP]:
        base_directory = os.path.join(self.input_path, "models")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__model_files.append(ModelFileRP(self, local_path))
            
        return self.__model_files

    @cached_property
    def render_controllers(self) -> list[RenderControllerFileRP]:
        base_directory = os.path.join(self.input_path, "render_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__render_controllers.append(RenderControllerFileRP(self, local_path))
            
        return self.__render_controllers

    @cached_property
    def items(self) -> list[ItemFileRP]:
        base_directory = os.path.join(self.input_path, "items")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__items.append(ItemFileRP(self, local_path))
            
        return self.__items

    
    @cached_property
    def animation_controllers(self) -> list[AnimationControllerRP]:
        children = []
        for file in self.animation_controller_files:
            for child in file.animation_controllers:
                children.append(child)
        return children

    
    def get_animation_controller_file(self, file_name:str) -> AnimationControllerFileRP:
        for child in self.animation_controller_files:
            if child.file_name == file_name:
                return child
        raise AssetNotFoundError(file_name)

    
    def get_animation_controller(self, id:str) -> AnimationControllerRP:
        for file_child in self.animation_controller_files:
            for child in file_child.animation_controllers:
                if child.id == id:
                    return child
        raise AssetNotFoundError(id)

    
class BehaviorPack(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        self.__spawn_rules = []
        self.__recipes = []
        self.__entities = []
        self.__animation_controller_files = []
        self.__loot_tables = []
        self.__items = []
        
    
    @cached_property
    def spawn_rules(self) -> list[SpawnRuleFile]:
        base_directory = os.path.join(self.input_path, "spawn_rules")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__spawn_rules.append(SpawnRuleFile(self, local_path))
            
        return self.__spawn_rules

    @cached_property
    def recipes(self) -> list[RecipeFile]:
        base_directory = os.path.join(self.input_path, "recipes")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__recipes.append(RecipeFile(self, local_path))
            
        return self.__recipes

    @cached_property
    def entities(self) -> list[EntityFileBP]:
        base_directory = os.path.join(self.input_path, "entities")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__entities.append(EntityFileBP(self, local_path))
            
        return self.__entities

    @cached_property
    def animation_controller_files(self) -> list[AnimationControllerFile]:
        base_directory = os.path.join(self.input_path, "animation_controllers")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__animation_controller_files.append(AnimationControllerFile(self, local_path))
            
        return self.__animation_controller_files

    @cached_property
    def loot_tables(self) -> list[LootTableFile]:
        base_directory = os.path.join(self.input_path, "loot_tables")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__loot_tables.append(LootTableFile(self, local_path))
            
        return self.__loot_tables

    @cached_property
    def items(self) -> list[ItemFileBP]:
        base_directory = os.path.join(self.input_path, "items")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__items.append(ItemFileBP(self, local_path))
            
        return self.__items

    
    
    def get_spawn_rule(self, identifier:str) -> SpawnRuleFile:
        for child in self.spawn_rules:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_recipe(self, identifier:str) -> RecipeFile:
        for child in self.recipes:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    def get_entity(self, identifier:str) -> EntityFileBP:
        for child in self.entities:
            if child.identifier == identifier:
                return child
        raise AssetNotFoundError(identifier)

    
    
class AnimationControllerFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__animation_controllers = []
        
    
    
    @cached_property
    def animation_controllers(self) -> list[AnimationControllerRP]:
        internal_path = parse("$.animation_controllers.*")
        for match in internal_path.find(self.data):
            self.__animation_controllers.append(AnimationControllerRP(self, match))
        return self.__animation_controllers

    
    def get_animation_controller(self, id:str) -> AnimationControllerRP:
        for child in self.animation_controllers:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    
class RecipeFile(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        
    
    @property
    def identifier(self):
        return self.get("$.('minecraft:recipe_shaped'|'minecraft:recipe_shapeless'|'minecraft:recipe_brewing_mix'|'minecraft:recipe_furnace'|'minecraft:recipe_brewing_container').description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("$.('minecraft:recipe_shaped'|'minecraft:recipe_shapeless'|'minecraft:recipe_brewing_mix'|'minecraft:recipe_furnace'|'minecraft:recipe_brewing_container').description.identifier", identifier)

    @property
    def format_version(self):
        return self.get("$.format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        self.set("$.format_version", format_version)

    
    
    
    
class SpawnRuleFile(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        
    
    @property
    def identifier(self):
        return self.get("$.'minecraft:spawn_rules.description'.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("$.'minecraft:spawn_rules.description'.identifier", identifier)

    @property
    def format_version(self):
        return self.get("$.format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        self.set("$.format_version", format_version)

    
    
    
    
class LootTableFile(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__pools = []
        
    
    
    @cached_property
    def pools(self) -> list[LootTablePool]:
        internal_path = parse("$.pools.[*]")
        for match in internal_path.find(self.data):
            self.__pools.append(LootTablePool(self, match))
        return self.__pools

    
    
    
class ItemFileRP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__components = []
        
    
    @property
    def identifier(self):
        return self.get("'minecraft:item'.description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("'minecraft:item'.description.identifier", identifier)

    @property
    def format_version(self):
        return self.get("format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        self.set("format_version", format_version)

    
    @cached_property
    def components(self) -> list[Component]:
        internal_path = parse("$.'minecraft:item'.components.*")
        for match in internal_path.find(self.data):
            self.__components.append(Component(self, match))
        return self.__components

    
    
    
class ItemFileBP(JsonResource):
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

    
    
    
class EntityFileRP(JsonResource):
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
        self.__animations = []
        
    
    @property
    def format_version(self):
        return self.get("$.format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        self.set("$.format_version", format_version)

    
    @cached_property
    def animations(self) -> list[AnimationRP]:
        internal_path = parse("$.animations.*")
        for match in internal_path.find(self.data):
            self.__animations.append(AnimationRP(self, match))
        return self.__animations

    
    
    
class EntityFileBP(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        self.__component_groups = []
        self.__components = []
        self.__events = []
        
    
    @property
    def format_version(self):
        return self.get("$.format_version")
    
    @format_version.setter
    def format_version(self, format_version):
        self.set("$.format_version", format_version)

    @property
    def identifier(self):
        return self.get("$.'minecraft:entity'.description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("$.'minecraft:entity'.description.identifier", identifier)

    
    @cached_property
    def component_groups(self) -> list[ComponentGroup]:
        internal_path = parse("$.'minecraft:entity'.component_groups.*")
        for match in internal_path.find(self.data):
            self.__component_groups.append(ComponentGroup(self, match))
        return self.__component_groups

    @cached_property
    def components(self) -> list[Component]:
        internal_path = "'minecraft:entity'.components.*"
        for path, data in get_data_at(internal_path, self.data):
            self.__components.append(Component(self, path, data))
        return self.__components

    @cached_property
    def events(self) -> list[Event]:
        internal_path = parse("$.'minecraft:entity'.events.*")
        for match in internal_path.find(self.data):
            self.__events.append(Event(self, match))
        return self.__events

    
    def get_component_group(self, id:str) -> ComponentGroup:
        for child in self.component_groups:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    def get_component(self, id:str) -> Component:
        for child in self.components:
            if child.id == id:
                return child
        raise AssetNotFoundError(id)

    
    def create_component_group(self, name: str, data: dict) -> ComponentGroup:
        self.data['minecraft:entity']['component_groups'][name] = data
        internal_path = parse(f"$.'minecraft:entity'.component_groups.'{name}'")
        matches = internal_path.find(self.data)
        if len(matches) > 1:
            raise AmbiguousAssetError(internal_path)
        
        if len(matches) == 0:
            raise AssetNotFoundError(name)
        match = matches[0]
        new_object = ComponentGroup(self, match)
        self.__component_groups.append(new_object)
        return new_object

    def create_component(self, name: str, data: dict) -> Component:
        self.data['minecraft:entity']['components'][name] = data
        internal_path = parse(f"$.'minecraft:entity'.components.'{name}'")
        matches = internal_path.find(self.data)
        if len(matches) > 1:
            raise AmbiguousAssetError(internal_path)
        
        if len(matches) == 0:
            raise AssetNotFoundError(name)
        match = matches[0]
        new_object = Component(self, match)
        self.__components.append(new_object)
        return new_object

    
class ModelFileRP(JsonResource):
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

    
    
    
class AnimationControllerRP(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        
    
    
    
    
    
class LootTablePool(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        
    
    
    
    
    
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

    
    @property
    def identifier(self):
        return self.get("$.description.identifier")
    
    @identifier.setter
    def identifier(self, identifier):
        self.set("$.description.identifier", identifier)

    
    
    
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

    
    
    
    def create_component(self, name: str, data: dict) -> Component:
        self.data[name] = data
        internal_path = parse(f".'{name}'")
        matches = internal_path.find(self.data)
        if len(matches) > 1:
            raise AmbiguousAssetError(internal_path)
        
        if len(matches) == 0:
            raise AssetNotFoundError(name)
        match = matches[0]
        new_object = Component(self, match)
        self.__components.append(new_object)
        return new_object

    
class Component(SubResource):
    def __init__(self, parent: JsonResource, json_path: str, data: dict, component_group: ComponentGroup = None) -> None:
        super().__init__(parent, json_path, data)
        
        
    
    
    
    
    
class Event(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        
        self.__groups_to_add = []
        self.__groups_to_remove = []
        
    
    @cached_property
    def groups_to_add(self) -> list[ComponentGroup]:
        internal_path = parse("add.component_groups.[*]")
        for match in internal_path.find(self.data):
            self.__groups_to_add.append(ComponentGroup(self, match))
        return self.__groups_to_add

    @cached_property
    def groups_to_remove(self) -> list[ComponentGroup]:
        internal_path = parse("remove.component_groups.[*]")
        for match in internal_path.find(self.data):
            self.__groups_to_remove.append(ComponentGroup(self, match))
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
        
        
    
    
    
    
    