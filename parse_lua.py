import ast
import random
import string

python_reserved = [
	"class", "finally", "is", "return",
	"continue", "for", "lambda", "trye",
	"def", "from", "nonlocal", "while",
	"and", "del", "global", "not", "with",
	"as", "elif", "if", "or", "yield",
	"assert", "else", "import", "pass",
	"break", "except", "in", "raise",
	"async", "await"
]
compare_operators = {
	"==": ast.Eq, "~=": ast.NotEq,
	"<": ast.Lt, "<=": ast.LtE,
	">": ast.Gt, ">=": ast.GtE
}
binary_operators = {
	"+": ast.Add, "-": ast.Sub,
	"*": ast.Mult, "/": ast.Div,
	"%": ast.Mod, "^": ast.Pow,
	"<<": ast.LShift, ">>": ast.RShift,
	"|": ast.BitOr, "^^": ast.BitXor,
	"&": ast.BitAnd
}
valid_random = string.ascii_letters + "_"

def check_reserved(word):
	if word in python_reserved:
		return "_" + word
	return word

def gen_random_text(length):
	return "hybridpython_var_" + ("".join(random.choices(valid_random, k=length)))

class LuaParser:
	def __init__(self, py38=False):
		self.py38 = py38

	def get_obj(self, obj):
		if self.py38:
			return ast.Constant(obj)
		if isinstance(obj, str):
			return ast.Str(obj)
		if isinstance(obj, (int, float)):
			return ast.Num(obj)
		if obj is True or obj is False or obj is None:
			return ast.NameConstant(obj)
		raise TypeError(
			"Can not generate object of type {} (not supported).".format(
				type(obj).__name__
			)
		)

	def parse_values(self, values, body):
		if len(values) == 0:
			return None
		if len(values) == 1:
			return self.visit(values[0], body)
		return ast.Tuple([self.visit(value, body) for value in values], ast.Load())

	def visit(self, node, body):
		parser = getattr(self, f"visit_{node['type']}", None)
		if parser is None:
			raise TypeError(f"Unknown Lua AST node: {node['type']}")

		return parser(node, body)

	def visit_LuaBody(self, body): # Not really a lua node.
		new = []

		for child in body:
			obj = self.visit(child, new)
			if obj is not None:
				if isinstance(obj, ast.expr):
					new.append(ast.Expr(obj))
				else:
					new.append(obj)

		if len(new) == 0:
			new.append(ast.Pass())

		return new

	def visit_Chunk(self, node, body):
		return ast.Module([ast.FunctionDef(
			"LUA_CONCAT",
			ast.arguments(
				posonlyargs=[],
				args=[
					ast.arg("x", None),
					ast.arg("y", None)
				],
				kwonlyargs=[],
				kw_defaults=[],
				defaults=[],
				kwarg=None,
				vararg=None
			),
			[
				ast.Return(
					ast.BinOp(
						ast.Name("x", ast.Load()),
						ast.Add(),
						ast.Name("y", ast.Load())
					)
				)
			],
			[]
		)] + self.visit_LuaBody(node["body"]))

	# Statements

	def visit_LabelStatement(self, node, body):
		raise NotImplementedError("Lua labels and goto statements \
are not supported.")

	def visit_GotoStatement(self, node, body):
		raise NotImplementedError("Lua labels and goto statements \
are not supported.")

	def visit_BreakStatement(self, node, body):
		return ast.Break()

	def visit_ReturnStatement(self, node, body):
		values = self.parse_values(node["arguments"], body)
		if isinstance(values, ast.Tuple):
			for index, value in enumerate(values.elts):
				if isinstance(value, ast.Starred):
					values.elts[index] = ast.Call(
						ast.Attribute(
							ast.Name("table", ast.Load()),
							"unpack",
							ast.Load()
						),
						[value.value],
						[]
					)

		return ast.Return(values)

	def visit_AssignmentStatement(self, node, body):
		targets = self.parse_values(node["variables"], body)
		values = self.parse_values(node["init"], body)
		targets.ctx = ast.Store()

		len_init, len_vars = len(node["init"]), len(node["variables"])
		if len_init != len_vars:
			if len_init == 0:
				values = ast.Tuple([], ast.Load())
			elif len_init == 1:
				values = ast.Tuple([values], ast.Load())

			for index in range(len_init, len_vars):
				values.elts.append(self.get_obj(None))

		return ast.Assign([targets], values)

	def visit_LocalStatement(self, node, body):
		return self.visit_AssignmentStatement(node, body)

	def visit_IfStatement(self, node, body):
		clause = node["clauses"].pop(0)

		return ast.If(
			self.visit(clause["condition"], body),
			self.visit_LuaBody(clause["body"]),

			# No more clauses
			[]
			if len(node["clauses"]) == 0 else

			# Elseif clause is next
			[self.visit_IfStatement(node, body)]
			if node["clauses"][0]["type"] == "ElseifClause" else

			# Else clause is next
			self.visit_LuaBody(node["clauses"][0]["body"])
		)

	def visit_WhileStatement(self, node, body):
		return ast.While(
			self.visit(node["condition"], body),
			self.visit_LuaBody(node["body"]),
			[]
		)

	def visit_DoStatement(self, node, body):
		return ast.If(
			self.get_obj(True),
			self.visit_LuaBody(node["body"]),
			[]
		)

	def visit_RepeatStatement(self, node, body):
		repeat_body = self.visit_LuaBody(node["body"])
		repeat_body.append(ast.If(
			self.visit(node["condition"], body),
			[ast.Break()],
			[]
		))

		return ast.While(
			self.get_obj(True),
			repeat_body,
			[]
		)

	def visit_CallStatement(self, node, body):
		return self.visit(node["expression"], body)

	def visit_ForNumericStatement(self, node, body):
		if node["step"] is None:
			step = self.get_obj(1)
		else:
			step = self.visit(node["step"], body)
		target = self.visit(node["variable"], body)
		target.ctx = ast.Store()

		return ast.For(
			target,
			ast.Call(
				ast.Name("range", ast.Load()),
				[
					self.visit(node["start"], body),
					ast.BinOp(
						self.visit(node["end"], body),
						ast.Add(),
						self.get_obj(1)
					),

					# Implicit step (for x = 1, 10 do)
					self.get_obj(1)
					if node["step"] is None else

					# Explicit step (for x = 1, 10, 2 do)
					self.visit(node["step"], body)
				],
				[]
			),
			self.visit_LuaBody(node["body"]),
			[]
		)

	def visit_FunctionDeclaration(self, node, body):
		arguments, vararg = [], None
		for parameter in node["parameters"]:
			if parameter["type"] == "VarargLiteral":
				vararg = ast.arg("LUA_VARARG", None)
			else:
				arguments.append(
					ast.arg(
						check_reserved(parameter["name"]),
						None
					)
				)

		args = ast.arguments(
			posonlyargs=[],
			args=arguments,
			kwonlyargs=[],
			kw_defaults=[],
			defaults=[],
			kwarg=None,
			vararg=vararg
		)

		# obj = function()
		if node["identifier"] is None:
			function_name = gen_random_text(30)

			body.append(ast.FunctionDef(
				function_name,
				args,
				self.visit_LuaBody(node["body"]),
				[]
			))

			return ast.Name(function_name, ast.Load())

		# some.thing = function()
		if node["identifier"]["type"] == "MemberExpression":
			function_name = gen_random_text(30)

			body.append(ast.FunctionDef(
				function_name,
				args,
				self.visit_LuaBody(node["body"]),
				[]
			))

			target = self.visit(node["identifier"], body)
			target.ctx = ast.Store()
			return ast.Assign([target], ast.Name(function_name, ast.Load()))

		# function obj()
		return ast.FunctionDef(
			# We assume it is an identifier object.
			node["identifier"]["name"],
			args,
			self.visit_LuaBody(node["body"]),
			[]
		)

	def visit_ForGenericStatement(self, node, body):
		if len(node["iterators"]) == 1:
			iterator = self.visit(node["iterators"][0], body)
			if (isinstance(iterator, ast.Call) and
				isinstance(iterator.func, ast.Name) and
				iterator.func.id in ("pairs", "ipairs")):
				iterator.func = ast.Name("enumerate", ast.Load())

		elif (len(node["iterators"]) == 2 and
			  node["iterators"][0]["type"] == "Identifier" and
			  node["iterators"][0]["name"] == "next"):
			iterator = ast.Call(
				ast.Name("enumerate", ast.Load()),
				[self.visit(node["iterators"][1], body)],
				[]
			)

		else:
			raise TypeError("Can not make a generic for with more \
than one iterator (besides next and a table).")

		return ast.For(
			self.parse_values(node["variables"], body),
			iterator,
			self.visit_LuaBody(node["body"]),
			[]
		)

	# Expressions

	def visit_StringLiteral(self, node, body):
		return self.get_obj(node["value"])

	def visit_NumericLiteral(self, node, body):
		return self.get_obj(node["value"])

	def visit_BooleanLiteral(self, node, body):
		return self.get_obj(node["value"])

	def visit_NilLiteral(self, node, body):
		return self.get_obj(node["value"])

	def visit_VarargLiteral(self, node, body):
		return ast.Starred(
			ast.Name("LUA_VARARG", ast.Load()),
			ast.Load()
		)

	def visit_Identifier(self, node, body):
		if node["name"] == "LUA_VARARG" or node["name"] == "LUA_CONCAT":
			print("[WARNING] You lua input has a variable called {}. \
This might cause a lot of trouble since we give it a special behaviour. \
We highly recommend you to rename it.".format(node["name"]))
		return ast.Name(check_reserved(node["name"]), ast.Load())

	def visit_TableConstructorExpression(self, node, body):
		new = ast.Dict([], [])

		# Make python "tables" start from 1
		lastIndex = 0
		has_starred = False

		for field in node["fields"]:
			if field["type"] == "TableValue":
				lastIndex += 1
				key = self.get_obj(lastIndex)

			elif field["type"] == "TableKey":
				key = self.visit(field["key"], body)

			elif field["type"] == "TableKeyString":
				# We assume field["key"] is an identifier and
				# it needs to be interpreted as string.
				key = self.get_obj(check_reserved(field["key"]["name"]))

			value = self.visit(field["value"], body)
			if isinstance(value, ast.Starred):
				value = value.value
				has_starred = True

			new.keys.append(key)
			new.values.append(value)

		if lastIndex == 1 and has_starred and len(new.keys) == 1:
			return new.values[0]
		return new

	def visit_LogicalExpression(self, node, body):
		return ast.BoolOp(
			ast.And() if node["operator"] == "and" else ast.Or(),
			[self.visit(node["left"], body), self.visit(node["right"], body)]
		)

	def visit_UnaryExpression(self, node, body):
		if node["operator"] == "#":
			return ast.Call(
				ast.Name("len", ast.Load()),
				[self.visit(node["argument"], body)],
				[]
			)

		return ast.UnaryOp(
			ast.USub() if node["operator"] == "-" else
			ast.Invert() if node["operator"] == "~" else
			ast.Not(), # if node["operator"] == "not"
			self.visit(node["argument"], body)
		)

	def visit_BinaryExpression(self, node, body):
		if node["operator"] == "..":
			return ast.Call(
				ast.Name("LUA_CONCAT", ast.Load()),
				[
					self.visit(node["left"], body),
					self.visit(node["right"], body)
				],
				[]
			)
		if node["operator"] in compare_operators:
			return ast.Compare(
				self.visit(node["left"], body),
				[ compare_operators[ node["operator"] ]() ],
				[self.visit(node["right"], body)]
			)

		return ast.BinOp(
			self.visit(node["left"], body),
			binary_operators[ node["operator"] ](),
			self.visit(node["right"], body)
		)

	def visit_MemberExpression(self, node, body):
		return ast.Attribute(
			self.visit(node["base"], body),
			check_reserved(node["identifier"]["name"]),
			ast.Load(),

			# This attribute is for the parser
			is_colon_call=node["indexer"] == ":"
		)

	def visit_IndexExpression(self, node, body):
		index = self.visit(node["index"], body)
		if isinstance(index, ast.Starred):
			index = ast.Subscript(
				index.value,
				ast.Index(self.get_obj(1)),
				ast.Load()
			)

		return ast.Subscript(
			self.visit(node["base"], body),
			ast.Index(index),
			ast.Load()
		)

	def visit_CallExpression(self, node, body):
		arguments = []
		for argument in node["arguments"]:
			arguments.append(self.visit(argument, body))

		base = self.visit(node["base"], body)
		if isinstance(base, ast.Attribute) and base.is_colon_call:
			arguments.insert(0, base)
		elif isinstance(base, ast.Name) and base.id == "assert":
			return ast.Assert(
				test=arguments[0],
				msg=arguments[1] if len(arguments) > 1 else None
			)

		return ast.Call(
			base,
			arguments,
			[]
		)

	def visit_TableCallExpression(self, node, body):
		node["arguments"] = [node["arguments"]]
		return self.visit_CallExpression(node, body)

	def visit_StringCallExpression(self, node, body):
		node["arguments"] = [node["argument"]]
		return self.visit_CallExpression(node, body)