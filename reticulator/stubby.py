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
		if member[0] == cls_name:
			return member[1]



class DecoratorManager():
	def __init__(self, name):
		self.name = name
		self.cache = []
		self.is_tracking = False

	def process_line(self, line):
		if line.startswith(self.name):
			self.is_tracking = True

		elif self.is_tracking:
			if ")" in line:
				self.is_tracking = False
			else:
				self.cache.append(line.strip().strip(",")+ "\n")

	def render(self):
		out = self.render_internal(self.cache)
		self.cache = []
		return out
	
	def render_internal(elements):
		pass
	

class ImplementResourceManager(DecoratorManager):
	def generate_decorator(self, cls_name):
		cls_name = cls_name.strip()
		cls = getmember(cls_name.strip())
		type_info = cls.type_info

		out = [
			f"@property\n",
			f"def {type_info.plural}(self) -> list[{cls_name}]:",
			f"def get_{type_info.attribute}(self, id: str) -> {cls_name}:",
			f"def add_{type_info.attribute}(self, name: str, data: dict) -> {cls_name}:"
		]

		# Handle special case for child classes
		child_cls = type_info.child_cls
		if child_cls != None:
			child_type_info = child_cls.type_info
			child_cls_name = child_cls.__name__

			out.extend([
				f"@property\n",
				f"def {child_type_info.plural}(self) -> list[{child_cls_name}]:",
				f"def get_{child_type_info.attribute}(self, id: str) -> {child_cls_name}:"
			])
			
		return ["    " + x for x in out]

	def render_internal(self, elements):
		out = []
		for element in elements:
			out.extend(self.generate_decorator(element))
		
		return out
	
class ImplementSubResourceManager(DecoratorManager):
	def generate_decorator(self, cls_name):

		cls_name = cls_name.strip()

		cls = getmember(cls_name)
		type_info = cls.type_info

		out = [
			f"@property\n",
			f"def {type_info.plural}(self) -> list[{cls_name}]:",
			f"def get_{type_info.attribute}(self, id: str) -> {cls_name}:",
			f"def add_{type_info.attribute}(self, name: str, data: dict) -> {cls_name}:"
		]
			
		return ["    " + x for x in out]

	def render_internal(self, elements):
		out = []
		for element in elements:
			out.extend(self.generate_decorator(element))
		
		return out
	
class ImplementSingleResourceManager(DecoratorManager):
	def generate_decorator(self, cls_name):

		cls_name = cls_name.strip()
		cls = getmember(cls_name)
		type_info = cls.type_info

		out = [
			f"@property\n",
			f"def {type_info.attribute}(self) -> list[{cls_name}]:",
		]
			
		return ["    " + x for x in out]

	def render_internal(self, elements):
		out = []
		for element in elements:
			out.extend(self.generate_decorator(element))
		
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
		# nonlocal decorator_cache

		# if decorator_cache:
		# 	return False

		strip_a = a.lstrip()
		if (strip_a.startswith("class") or strip_a.startswith("def")) and not strip_a.strip().endswith('pass'):
			# Check indentation difference
			return get_indentation(a) >= get_indentation(b)
		else:
			return False

	
	resource_manager = ImplementResourceManager("@ImplementResource(")
	sub_resource_manager = ImplementSubResourceManager("@ImplementSubResource(")
	single_manager = ImplementSingleResourceManager("@ImplementSingleResource(")

	with open(file_name, 'r') as f:
		line = "True" # Hmm
		while line:
			line = f.readline()

			resource_manager.process_line(line)
			sub_resource_manager.process_line(line)
			single_manager.process_line(line)

			if should_take_line(line):
				LINES.append(line)

				if line.lstrip().startswith("class"):
					LINES.extend(resource_manager.render())
					LINES.extend(sub_resource_manager.render())
					LINES.extend(single_manager.render())


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
	
main1()