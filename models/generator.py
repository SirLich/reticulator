import json

def title_case(text):
    return text.replace("_", " ").title().replace(" ","")

def make_params(children):
    data = ""
    for child in children:
        name = child["name"]
        data += f"self.{name} = {name}\n        "
    
    return data

def make_subrec_attributes(children):
    data = ""
    for child in children:
        name = child["name"]
        data += "self.__{} = []\n        ".format(name)
    
    return data

def make_subrec_accessor(child):
    name = child["name"]
    class_ = child["class"]
    path = child["path"]
    getter = child.get("getter", f"{class_}(self, match)")

    return f"""
    @cached_property
    def {name}(self) -> list[{class_}]:
        internal_path = parse("{path}")
        for match in internal_path.find(self.data):
            self.__{name}.append({getter})
        return self.__{name}
"""

def make_property_accessor(child):
    print(child)
    name = child["name"]
    path = child["path"]

    return f"""
    @property
    def {name}(self):
        return self.get("{path}")
    
    @{name}.setter
    def {name}(self, {name}):
        self.set("{path}", {name})
""" 
def make_property_accessors(children):
    out = ""
    for child in children:
        out += make_property_accessor(child)
    return out

def make_subrec_accessors(children):
    out = ""
    for child in children:
        out += make_subrec_accessor(child)
    return out

def make_json_resource(model):
    class_ = model.get("class")
    children = model.get("sub_resources", [])
    properties = model.get("properties", [])

    data = f"""
class {class_}(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        {make_subrec_attributes(children)}
    {make_property_accessors(properties)}
    {make_subrec_accessors(children)}
    """

    return data

def make_parameters(model):
    parameters = model.get("parameters", [])
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

    return f"""
class {class_}(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext{make_parameters(model)}) -> None:
        super().__init__(parent, datum)
        {make_params(params)}
        {make_subrec_attributes(children)}
    {make_subrec_accessors(children)}
    """

def generate_models(base, models, generated):
    with open(base, "r") as f:
        base = f.read()

    with open(models, "r") as f:
        data = json.load(f)

    with open(generated, "w") as outfile:
        outfile.write(base)

        for model in data["json_resources"]:
            outfile.write(make_json_resource(model))
        
        for model in data["sub_resources"]:
            outfile.write(make_sub_resource(model))

generate_models("base.py", "models.json", "generated.py")