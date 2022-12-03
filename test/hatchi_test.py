import sys
import shutil

sys.path.insert(0, '../reticulator')
from reticulator import *

def setup_output_dir():
    try:
        shutil.rmtree('./out/')
    except:
        pass

    os.mkdir('./out/')

def main():
    # Load project
    setup_output_dir()

    bp = BehaviorPack('./content/bp/')
    bp.output_directory = './out/bp/' 

    for entity in bp.entities:
        print(entity.components)
        for event in entity.events:
            command = f"/Say {entity.identifier}: {event.id}"
            event.append_jsonpath('run_command/command', command)

    bp.save()


main()
