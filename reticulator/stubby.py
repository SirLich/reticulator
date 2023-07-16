"""
Simple file which stubs out type hints for a module.

Various assumptions are baked in, which make this unsuitable for non
reticulator projects. 
"""

    # @property
    # def entities(self) -> list[EntityFileBP]: ...
    # def get_component(self, id: str) -> EntityComponentBP: ...
    # def add_component(self, name: str, data: dict) -> EntityComponentBP: ...

import sys
import importlib
import inspect
ret = importlib.import_module("reticulator")

LINES = [
	"from __future__ import annotations",
	"from core import *",
	"from typing import Tuple",
	""
] 
LINES = [x + "\n" for x in LINES]

def getmember(cls_name):
	for member in inspect.getmembers(ret):
		print(member)
		if member[0] == cls_name:
			return member[1]

def generate_decorator(cls_name):
	cls_name = cls_name.strip()
	cls = getmember(cls_name.strip())
	type_info = cls.type_info

	out = [
		f"@property\n",
		f"def {type_info.plural}(self) -> list[{cls_name}]:",
		f"def get_{type_info.attribute}(self, id: str) -> {cls_name}:",
		f"def add_{type_info.attribute}(self, name: str, data: dict) -> {cls_name}:"
	]
		
	return ["    " + x for x in out]

def get_function_from_decorators(decorators):
	out = []
	for decorator in decorators:
		out.extend(generate_decorator(decorator))
	
	return out

def main1():
	try:
		file_name = sys.argv[1]
	except IndexError:
		file_name = "./reticulator.py"

	reading_block_comment = False

	def should_take_line(line: str) -> bool:
		nonlocal reading_block_comment
		if '"""' in line:
			reading_block_comment = not reading_block_comment
			return True
		
		if reading_block_comment:
			return True
		
		strip_line = line.lstrip()
		if strip_line.startswith("class") or strip_line.startswith("def"):
			return True

	def get_indentation(s: str) -> int:
		return len(s)-len(s.lstrip(' '))


	def wants_dots(a: str, b: str) -> bool:
		nonlocal decorator_cache

		if decorator_cache:
			return False

		strip_a = a.lstrip()
		if (strip_a.startswith("class") or strip_a.startswith("def")) and not strip_a.strip().endswith('pass'):
			# Check indentation difference
			return get_indentation(a) >= get_indentation(b)

		else:
			return False

	decorator_cache = []
	is_reading_decorators = False
	with open(file_name, 'r') as f:
		line = "True" # Hmm
		while line:
			line = f.readline()

			if is_reading_decorators:
				if ")" in line:
					is_reading_decorators = False
				else:
					decorator_cache.append(line.strip().strip(",")+ "\n") 

			if should_take_line(line):
				LINES.append(line)

				if line.lstrip().startswith("class"):
					LINES.extend(get_function_from_decorators(decorator_cache))
					decorator_cache = []

			if line.lstrip().startswith("@ImplementsResource("):
				is_reading_decorators = True

	# Add .... where required
	for i in range(len(LINES)):
		try:
			a = LINES[i]
			b = LINES[i + 1]

			if wants_dots(a, b):
				LINES[i] = a.rstrip() + " ...\n"
			
		except Exception:
			continue

	with open('reticulator.pyi', 'w') as f:
		f.writelines(LINES)

def get_classes(lines: str):
	classes = []

	current_class = []
	for i in range(len(lines)):
		if i 

def main():
	in_file  = "./reticulator.py"
	out_file = "./reticulator.pyi"
	
	with open(in_file, 'r') as f:
		lines = f.readlines()
		
	classes = get_classes(lines)

	with open(out_file, 'w') as f:
		f.write(data)
	
main()