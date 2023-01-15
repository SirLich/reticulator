import sys
import shutil

from typing import *
from pprint import pprint

sys.path.insert(0, '../reticulator')
from reticulator import *

import reticulator as ret

def main():
    bp = BehaviorPack('./content/bp/')
    # pprint(get_type_hints(getattr(getattr(ret, "EntityFileBP"), "get_component")))

    for entity in bp.entities:
        print(entity.identifier)

main()
