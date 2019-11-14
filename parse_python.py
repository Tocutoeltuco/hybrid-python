import ast
import lua_nodes as lua

python_reserved = [
	"_class", "_finally", "_is", "_return",
	"_continue", "_for", "_lambda", "_trye",
	"_def", "_from", "_nonlocal", "_while",
	"_and", "_del", "_global", "_not", "_with",
	"_as", "_elif", "_if", "_or", "_yield",
	"_assert", "_else", "_import", "_pass",
	"_break", "_except", "_in", "_raise",
	"_async", "_await"
]
compare_operators = {
	ast.Eq: "==", ast.NotEq: "~=",
	ast.Lt: "<", ast.LtE: "<=",
	ast.Gt: ">", ast.GtE: ">="
}
binary_operators = {
	ast.Add: "+", ast.Sub: "-",
	ast.Mult: "*", ast.Div: "/",
	ast.Mod: "%", ast.Pow: "^",
	ast.LShift: "<<", ast.RShift: ">>",
	ast.BitOr: "|", ast.BitXor: "^^",
	ast.BitAnd: "&"
}

def check_reserved(word):
	if word in python_reserved:
		return word[1:]
	return word

class PythonParser:
	def __init__(self):
		self.hybrid_vars = {}

	def unpack_values(self, value, body):
		if isinstance(value, ast.Tuple):
			elements = []

			for element in value.elts:
				elements.append(self.visit(element, body))

			return elements

		return [self.visit(value, body)]

	def visit(self, node, body):
		parser = getattr(self, f"visit_{node.__class__.__name__}", None)
		if parser is None:
			raise TypeError(f"Unknown Python AST node: {node.__class__.__name__}")

		return parser(node, body)

	def visit_PyBody(self, body): # Not really a python node.
		new = []

		for child in body:
			obj = self.visit(child, new)
			if obj is not None:
				new.append(obj)

		return new

	def visit_Module(self, node, body):
		return lua.Chunk(self.visit_PyBody(node.body))

	def visit_Expr(self, node, body):
		return self.visit(node.value, body)

	def visit_Break(self, node, body):
		return lua.BreakStatement()

	def visit_Return(self, node, body):
		return lua.ReturnStatement(
			self.unpack_values(
				node.value,
				body
			) if node.value is not None else []
		)

	def visit_Assign(self, node, body):
		return lua.AssignmentStatement(
			False,
			self.unpack_values(node.targets[0], body),
			self.unpack_values(node.value, body)
		)

	def visit_Assert(self, node, body):
		return lua.CallStatement(
			lua.CallExpression(
				lua.Identifier("assert"),

				[self.visit(node.test, body)]
				if node.msg is None else
				[self.visit(node.test, body), self.visit(node.msg, body)]
			)
		)

	def visit_If(self, node, body, as_clause=False, as_if=False):
		if not as_clause:
			clauses = self.visit_If(
				node,
				body,
				as_clause=True,
				as_if=True
			)
			if (len(clauses) == 1 and
				clauses[0]["condition"]["type"] == "BooleanLiteral"
				and clauses[0]["condition"]["value"]):
				return lua.DoStatement(clauses[0]["body"])
			return lua.IfStatement(clauses)

		generator = lua.IfClause if as_if else lua.ElseifClause
		clauses = [
			generator(
				self.visit(node.test, body),
				self.visit_PyBody(node.body)
			)
		]

		if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
			clauses.extend(self.visit_If(node.orelse[0], body, as_clause=True))

		elif len(node.orelse) > 0:
			clauses.append(lua.ElseClause(self.visit_PyBody(node.orelse)))

		return clauses

	def visit_While(self, node, body):
		condition = self.visit(node.test, body)
		while_body = self.visit_PyBody(node.body)

		# while True:
		# 	...
		# 	if some condition:
		# 		break
		if (condition["type"] == "BooleanLiteral" and
			condition["value"] and
			while_body[-1]["type"] == "IfStatement" and
			len(while_body[-1]["clauses"]) == 1 and
			len(while_body[-1]["clauses"][0]["body"]) == 1 and

			while_body[-1]["clauses"][0]["body"][0]["type"] ==
			"BreakStatement"):

			until = while_body.pop()
			return lua.RepeatStatement(
				until["clauses"][0]["condition"],
				while_body
			)
		return lua.WhileStatement(condition, while_body)

	def visit_Call(self, node, body):
		arguments = []
		for argument in node.args:
			arguments.append(self.visit(argument, body))

		fnc = self.visit(node.func, body)
		if fnc["type"] == "Identifier":
			if fnc["name"] == "len" and len(arguments) == 1:
				return lua.UnaryExpression("#", *arguments)
			if fnc["name"] == "LUA_CONCAT" and len(arguments) == 2:
				return lua.BinaryExpression("..", *arguments)

		return lua.CallStatement(
			lua.CallExpression(fnc, arguments)
		)

	def visit_For(self, node, body):
		target = self.unpack_values(node.target, body)

		if (isinstance(node.iter, ast.Call) and
			isinstance(node.iter.func, ast.Name)):
			if node.iter.func.id == "enumerate":
				node.iter.func.id = "pairs"

			elif node.iter.func.id == "range":
				arguments = []
				for arg in node.iter.args:
					arguments.append(self.visit(arg, body))

				if len(arguments) == 1:
					start = lua.NumericLiteral(1)
					end = lua.BinaryExpression(
						"-",
						arguments[0],
						lua.NumericLiteral(1)
					)
					step = lua.NumericLiteral(1)

				elif len(arguments) == 2:
					start = arguments[0]
					end = lua.BinaryExpression(
						"-",
						arguments[1],
						lua.NumericLiteral(1)
					)
					step = lua.NumericLiteral(1)

				else:
					start = arguments[0]
					end = lua.BinaryExpression(
						"-",
						arguments[1],
						lua.NumericLiteral(1)
					)
					step = arguments[2]

				return lua.ForNumericStatement(
					target[0],
					start,
					end,
					step,
					self.visit_PyBody(node.body)
				)

		return lua.ForGenericStatement(
			target,
			[self.visit(node.iter, body)],
			self.visit_PyBody(node.body)
		)

	def visit_FunctionDef(self, node, body):
		if node.name == "LUA_CONCAT":
			return

		parameters = [
			lua.Identifier(check_reserved(argument.arg))
			for argument in node.args.args
		]
		if node.args.vararg is not None:
			parameters.append(lua.VarargLiteral())
		body = self.visit_PyBody(node.body)

		if node.name.startswith("hybridpython_var_"):
			self.hybrid_vars[node.name] = lua.FunctionStatement(
				None,
				parameters,
				body
			)
			return
		return lua.FunctionStatement(node.name, parameters, body)

	def visit_Name(self, node, body):
		if (isinstance(node.ctx, ast.Load) and
			node.id.startswith("hybridpython_var_")):
			return self.hybrid_vars[node.id]
		if node.id == "LUA_VARARG":
			return lua.TableConstructorExpression([
				lua.TableValue(
					lua.VarargLiteral()
				)
			])
		return lua.Identifier(check_reserved(node.id))

	def visit_Pass(self, node, body):
		return

	def visit_Starred(self, node, body):
		if isinstance(node.value, ast.Name) and node.value.id == "LUA_VARARG":
			return lua.VarargLiteral()
		return lua.CallStatement(
			lua.CallExpression(
				lua.MemberExpression(
					lua.Identifier("table"),
					".",
					"unpack"
				),
				[node]
			)
		)

	def visit_Constant(self, node, body):
		return lua.Literal(node.value)

	def visit_Str(self, node, body):
		return lua.StringLiteral(node.s)

	def visit_Num(self, node, body):
		return lua.NumericLiteral(node.n)

	def visit_NameConstant(self, node, body): # py3.7 boolean, none
		return lua.Literal(node.value)

	def visit_Dict(self, node, body):
		fields = []

		for key, value in zip(node.keys, node.values):
			fields.append(lua.TableKey(
				self.visit(check_reserved(key), body),
				self.visit(value, body)
			))

		return lua.TableConstructorExpression(fields)

	def visit_BoolOp(self, node, body):
		operator = "and" if isinstance(node.op, ast.And) else "or"
		expression = self.visit(node.values[0], body)

		for index, value in enumerate(node.values):
			if index == 0:
				continue

			expression = lua.LogicalExpression(
				operator,
				expression,
				self.visit(value, body)
			)
		return expression

	def visit_Compare(self, node, body):
		for operator_class, symbol in compare_operators.items():
			if isinstance(node.ops[0], operator_class):
				expression = lua.BinaryExpression(
					symbol,
					self.visit(node.left, body),
					self.visit(node.comparators[0], body)
				)
				break

		for index, operator in enumerate(node.ops):
			if index == 0:
				continue

			for operator_class, symbol in compare_operators.items():
				if isinstance(operator, operator_class):
					expression = lua.LogicalExpression(
						"and",
						expression,
						lua.BinaryExpression(
							symbol,
							self.visit(node.comparators[index - 1], body),
							self.visit(node.comparators[index], body)
						)
					)
					break

		return expression

	def visit_BinOp(self, node, body):
		for operator_class, symbol in binary_operators.items():
			if isinstance(node.op, operator_class):
				return lua.BinaryExpression(
					symbol,
					self.visit(node.left, body),
					self.visit(node.right, body)
				)

	def visit_UnaryOp(self, node, body):
		if isinstance(node.op, ast.UAdd): # +1
			return self.visit(node.operand, body)
		return lua.UnaryExpression(
			"~" if isinstance(node.op, ast.Invert) else # ~1
			"-" if isinstance(node.op, ast.USub) else # -1
			"not", # if isinstance(node.op, ast.Not) # not True
			self.visit(node.operand, body)
		)

	def visit_Attribute(self, node, body):
		return lua.MemberExpression(
			self.visit(node.value, body),
			".",
			check_reserved(node.attr)
		)

	def visit_Subscript(self, node, body):
		if not isinstance(node.slice, ast.Index):
			raise TypeError("Lua doesn't support item slicing.")
		return lua.IndexExpression(
			self.visit(node.value, body),
			self.visit(node.slice.value, body)
		)