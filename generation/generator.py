"""Generator class for building Reticulator, based on some input structures."""
import json

def title_case(text):
    return text.replace("_", " ").title().replace(" ","")

def make_parameters(children):
    out = ""
    for child in children:
        name = child["name"]
        out += f"self.{name} = {name}\n        "
    
    return out

def convert_json_path_to_list(path: str):
    path = path.replace("'", "")
    elements = path.split('.')
    out = ""
    for element in elements:
        if element != "$" and element != "" and element != "*":
            out += f"['{element}']"
    return out + "[name]"


def make_creator(child):
    """Generate code-block for creating sub-resources"""
    if child.get("creator") is None:
        return ""

    class_ = child["class"]
    name = child["name"]
    creator_name = child["creator"]["name"]
    path = child['json_path']
    path = path.rstrip('.*')

    return (
    f"""
    def {creator_name}(self, name: str, data: dict) -> {class_}:
        self.set_value_at("{path}." + name, data)
        new_object = {class_}(self, "{path}." + name, data)
        self.__{name}.append(new_object)
        return new_object
""")

def make_grandchild_getter(child):
    if child.get("getter") is None:
        return ""

    getter = child["getter"]

    class_ = getter.get("class", child["class"])
    name = child["name"]
    getter_name = getter["name"]
    prop = getter["property"]
    from_child = child.get("from_child")

    return(
    f"""
    def {getter_name}(self, {prop}:str) -> {class_}:
        for file_child in self.{from_child}:
            for child in file_child.{name}:
                if child.{prop} == {prop}:
                    return child
        raise AssetNotFoundError({prop})
""")

def make_getter(child):
    if child.get("getter") is None:
        return ""

    getter = child["getter"]

    class_ = getter.get("class", child["class"])
    name = child["name"]
    getter_name = getter["name"]
    prop = getter["property"]
    from_child = getter.get("from_child")

    if from_child:
        return (
    f"""
    def {getter_name}(self, {prop}:str) -> {class_}:
        for file_child in self.{name}:
            for child in file_child:
                if child.{prop} == {prop}:
                    return child
        raise AssetNotFoundError
""")

    else:
        return (
    f"""
    def {getter_name}(self, {prop}:str) -> {class_}:
        for child in self.{name}:
            if child.{prop} == {prop}:
                return child
        raise AssetNotFoundError({prop})
""")

def make_creators(children):
    out = ""
    for child in children:
        out += make_creator(child)
    return out

def make_grandchild_getters(children):
    out = ""
    for child in children:
        out += make_grandchild_getter(child)
    return out

def make_getters(children):
    out = ""
    for child in children:
        out += make_getter(child)
    return out

def make_attributes(children):
    data = ""

    for child in children:
        name = child["name"]
        data += "self.__{} = []\n        ".format(name)
    

    return data

def make_grandchild_accessor(child):
    name = child["name"]
    class_ = child["class"]
    from_child = child["from_child"]

    return f"""
    @cached_property
    def {name}(self) -> list[{class_}]:
        children = []
        for file in self.{from_child}:
            for child in file.{name}:
                children.append(child)
        return children
"""

def make_resource_accessor(child):
    name = child["name"]
    class_ = child["class"]
    path = child["file_path"]

    return f"""
    @cached_property
    def {name}(self) -> list[{class_}]:
        base_directory = os.path.join(self.input_path, "{path}")
        for local_path in glob.glob(base_directory + "/**/*.json", recursive=True):
            local_path = os.path.relpath(local_path, self.input_path)
            self.__{name}.append({class_}(file_path = local_path, pack = self))
            
        return self.__{name}
"""

def make_subrec_accessor(child):
    name = child["name"]
    class_ = child["class"]
    path = child["json_path"]
    getter = child.get("getter_argument", f"{class_}(self, match)")

    return f"""
    @cached_property
    def {name}(self) -> list[{class_}]:
        for path, data in self.get_data_at("{path}"):
            self.__{name}.append({class_}(parent = self, json_path = path, data = data))
        return self.__{name}
    """

def make_property_accessor(child):
    name = child["name"]
    path = child["json_path"]

    return f"""
    @property
    def {name}(self):
        return self.get_value_at("{path}")
    
    @{name}.setter
    def {name}(self, {name}):
        return self.set_value_at("{path}", {name})
""" 
def make_property_accessors(children):
    out = ""
    for child in children:
        out += make_property_accessor(child)
    return out

def make_grandchild_accessors(children):
    out = ""
    for child in children:
        out += make_grandchild_accessor(child)
    return out

def make_resource_accessors(children):
    out = ""
    for child in children:
        out += make_resource_accessor(child)
    return out

def make_subrec_accessors(children):
    out = ""
    for child in children:
        out += make_subrec_accessor(child)
    return out

def make_pack(model):
    class_ = model.get("class")
    children = model.get("json_resources", [])
    grand_children = model.get("sub_resources", [])

    return f"""
class {class_}(Pack):
    def __init__(self, input_path: str, project: Project = None):
        super().__init__(input_path, project=project)
        {make_attributes(children)}
    {make_resource_accessors(children)}
    {make_grandchild_accessors(grand_children)}
    {make_getters(children)}
    {make_grandchild_getters(grand_children)}
    """
    
def make_json_resource(model):
    class_ = model.get("class")
    children = model.get("sub_resources", [])
    properties = model.get("properties", [])

    data = f"""
class {class_}(JsonFileResource):
    def __init__(self, data: dict = None, file_path: str = None, pack: Pack = None) -> None:
        super().__init__(data = data, file_path = file_path, pack = pack)
        {make_attributes(children)}
    {make_property_accessors(properties)}
    {make_subrec_accessors(children)}
    {make_getters(children)}
    {make_creators(children)}
    """

    return data

def make_params(model):
    parameters = model.get("optional_parameters", [])
    if(len(parameters) == 0):
        return ""
    data = ""
    
    for param in parameters:
        data += f", {param['name']}: {param['class']} = None"
    
    return data

def make_sub_resource(model):
    class_ = model.get("class")
    children = model.get("sub_resources", [])
    params = model.get("parameters", [])
    properties = model.get("properties", [])

    return f"""
class {class_}(JsonSubResource):
    def __init__(self, data: dict = None, parent: Resource = None, json_path: str = None {make_params(model)}) -> None:
        super().__init__(data=data, parent=parent, json_path=json_path)
        {make_parameters(params)}
        {make_attributes(children)}
    {make_subrec_accessors(children)}
    {make_property_accessors(properties)}
    {make_getters(children)}
    {make_creators(children)}
    """

def generate(base, models, generated):
    with open(base, "r") as f:
        base = f.read()

    with open(models, "r") as f:
        data = json.load(f)

    # Write to the output file, 
    with open(generated, "w") as outfile:
        outfile.write(base)

        for model in data["packs"]:
            outfile.write(make_pack(model))

        for model in data["json_resources"]:
            outfile.write(make_json_resource(model))
        
        for model in data["sub_resources"]:
            outfile.write(make_sub_resource(model))

def main():
    generate("base.py", "models.json", "../reticulator.py")

main()