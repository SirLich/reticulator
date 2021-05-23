
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

    
class Event(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        self.__groups_to_add = []self.__groups_to_remove = []
    
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
        
    
    