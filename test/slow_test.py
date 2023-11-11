import sys
import shutil

from time import time
from functools import wraps

def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('func:%r args:[%r, %r] took: %2.4f sec' % \
          (f.__name__, args, kw, te-ts))
        return result
    return wrap

sys.path.insert(0, '../reticulator')
from reticulator import *

def setup_output_dir():
	try:
		shutil.rmtree('./out/')
	except:
		pass

	os.mkdir('./out/')

@timing
def main():
	# Load project
	setup_output_dir()
	
	project = Project('C:/liam/projects/vanilla/bp_18/', 'C:/liam/projects/vanilla/rp_18/')
	rp, bp = project.resource_pack, project.behavior_pack
	
	rp.output_directory = './out/rp/'
	bp.output_directory = './out/bp/'

	for entity in bp.entities:
		entity.identifier = entity.identifier + 'a'
	
	project.save()

main()
