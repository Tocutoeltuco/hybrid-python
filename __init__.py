from .lua_code_gen import body_to_code as lua_node_to_code
from .lua_code_gen import LuaParser as LuaCodeGenerator
from .parse_python import PythonParser
from .parse_lua import LuaParser
from . import lua_nodes as LuaNodes

import subprocess
import tempfile
import astor
import json
import sys
import os

def get_lua_ast(file, version):
	"""Returns the lua abstract syntax tree of a given file."""
	stdout, stderr = subprocess.Popen(
		["node", "./lua-parser.js", file, version],
		stdout=subprocess.PIPE, stderr=subprocess.PIPE
	).communicate()

	if stderr != b"":
		sys.stderr.write(stderr.decode())
		raise Exception()

	return json.loads(stdout)

def gen_lua_ast(lua_code, version):
	"""Returns the lua abstract syntax tree of a given code."""
	if isinstance(lua_code, bytes):
		mode = "wb"
	elif isinstance(lua_code, str):
		mode = "w"
	else:
		raise TypeError("lua_code must be either a str or bytes object.")
	version = str(version) # Force string.

	file_data = tempfile.mksfile()
	with open(file_data[0], mode) as file:
		file.write(lua_code)

	ast = get_lua_ast(file_data[1], version)
	os.unlink(file_data[1])
	return ast

def gen_py_code(py_ast, *args, **kwargs):
	"""Returns a python code generated from
	a python abstract syntax tree."""
	return astor.code_gen.to_source(py_ast, *args, **kwargs)

def gen_lua_code(lua_ast, indent="  ", generator=None):
	"""Returns a lua code generated from
	a lua abstract syntax tree."""
	generator = generator or LuaCodeGenerator(indent)
	result = generator.visit(lua_ast)

	if not isinstance(result, str):
		result = lua_node_to_code(result, "", indent)

	return generator, result

def lua_to_py_ast(lua_ast, generator=None):
	"""Returns a python abstract syntax tree generated from
	a lua one."""
	generator = generator or LuaParser()
	return generator, generator.visit(lua_ast)

def py_to_lua_ast(py_ast, generator=None):
	"""Returns a lua abstract syntax tree generated from
	a python one."""
	generator = generator or PythonParser()
	return generator, generator.visit(py_ast)