import json

def title_case(text):
    return text.replace("_", " ").title().replace(" ","")

def make_properties(children):
    data = ""
    for child in children:
        name = child["name"]
        data += "self.__{} = []".format(name)
    
    return data

def make_property_getter(child):
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

def make_property_getters(children):
    out = ""
    for child in children:
        out += make_property_getter(child)
    return out

def make_json_resource(model):
    class_ = model.get("class")
    children = model.get("sub_resources", [])

    data = f"""
class {class_}(JsonResource):
    def __init__(self, pack: Pack, file_path: str, data: dict = None) -> None:
        super().__init__(pack, file_path, data)
        {make_properties(children)}
    {make_property_getters(children)}
    """

    return data

def make_sub_resource(model):
    class_ = model.get("class")
    children = model.get("sub_resources", [])

    return f"""
class {class_}(SubResource):
    def __init__(self, parent: JsonResource, datum: DatumInContext) -> None:
        super().__init__(parent, datum)
        {make_properties(children)}
    {make_property_getters(children)}
    """

    return data

def generate_models(inc, outc):
    with open(inc, "r") as f:
        data = json.load(f)

    with open(outc, "w") as outfile:
        for model in data["json_resources"]:
            outfile.write(make_json_resource(model))
        
        for model in data["sub_resources"]:
            outfile.write(make_sub_resource(model))

generate_models("models.json", "out.py")