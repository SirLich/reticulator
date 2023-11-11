import sys
import shutil

from typing import *
from pprint import pprint

sys.path.insert(0, '../reticulator')
from reticulator import *

import reticulator as ret

def main():
    bp = BehaviorPack('./content/bp/')

    for entity in bp.entities:
        entity.

main()
