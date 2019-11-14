def body_to_code(body, indent, add_indent):
	if isinstance(body, tuple):
		body = list(body)

	for index, block in enumerate(body):
		if isinstance(block, str):
			body[index] = f"{indent}{block}"
		else:
			body[index] = body_to_code(block, indent + add_indent, add_indent)

	return "\n".join(body)

class LuaParser:
	def __init__(self, indent="  "):
		self.indent = indent

	def visit(self, node):
		parser = getattr(self, f"visit_{node['type']}", None)
		if parser is None:
			raise TypeError(f"Unknown Lua AST node: {node['type']}")

		return parser(node)

	def visit_expr(self, node):
		value = self.visit(node)

		if isinstance(value, (list, tuple)):
			return "(" + body_to_code(value, "", self.indent).strip("\n") + ")"
		return value

	def visit_LuaBody(self, body):
		new = []

		for child in body:
			obj = self.visit(child)
			if obj is not None:
				if isinstance(obj, tuple):
					new.extend(obj)
				else:
					new.append(obj)

		return new

	def visit_Chunk(self, node):
		return body_to_code(self.visit_LuaBody(node["body"]), "", self.indent)

	# Statements

	def visit_LabelStatement(self, node):
		return "::" + node["label"] + "::"

	def visit_GotoStatement(self, node):
		return "goto " + node["label"]

	def visit_BreakStatement(self, node):
		return "break"

	def visit_ReturnStatement(self, node):
		if len(node["arguments"]) == 0:
			return "return"
		return "return " + (", ".join(map(self.visit_expr, node["arguments"])))

	def visit_AssignmentStatement(self, node):
		return ((", ".join(map(self.visit, node["variables"]))) + " = " +
				(", ".join(map(self.visit_expr, node["init"]))))

	def visit_LocalStatement(self, node):
		return "local " + self.visit_AssignmentStatement(node)

	def visit_IfStatement(self, node):
		retval = []

		for clause in node["clauses"]:
			if clause["type"] == "IfClause":
				retval.append(
					"if " + self.visit(clause["condition"]) + " then"
				)

			elif clause["type"] == "ElseifClause":
				retval.append("")
				retval.append(
					"elseif " + self.visit(clause["condition"]) + " then"
				)

			else:
				retval.append("")
				retval.append("else")

			retval.append(self.visit_LuaBody(clause["body"]))

		retval.append("end\n")
		return tuple(retval) # Tuple so it extends to the body

	def visit_WhileStatement(self, node):
		return (
			"while " + self.visit(node["condition"]) + " do",
			self.visit_LuaBody(node["body"]),
			"end\n"
		)

	def visit_DoStatement(self, node):
		return (
			"do",
			self.visit_LuaBody(node["body"]),
			"end\n"
		)

	def visit_RepeatStatement(self, node):
		return (
			"repeat",
			self.visit_LuaBody(node["body"]),
			"until " + self.visit(node["condition"]) + "\n"
		)

	def visit_CallStatement(self, node):
		return self.visit(node["expression"])

	def visit_ForNumericStatement(self, node):
		return (
			("for " + self.visit(node["variable"]) + " = " +
			self.visit(node["start"]) + ", " + self.visit(node["end"]) + ", " +
			self.visit(node["step"]) + " do"),

			self.visit_LuaBody(node["body"]),
			"end\n"
		)

	def visit_ForGenericStatement(self, node):
		return (
			"for " + (", ".join(map(self.visit, node["variables"]))) +
			" in " + (", ".join(map(self.visit_expr, node["iterators"]))) +
			" do",

			self.visit_LuaBody(node["body"]),
			"end\n"
		)

	def visit_FunctionDeclaration(self, node):
		return (
			(("local " if node["isLocal"] else "") +
			"function" +
			(" " + node["identifier"]
			if node["identifier"] is not None else
			"") + "(" +
			(", ".join(map(self.visit, node["parameters"]))) + ")"),

			self.visit_LuaBody(node["body"]),
			"end\n"
		)

	# Expressions

	def visit_StringLiteral(self, node):
		return node["raw"]

	def visit_NumericLiteral(self, node):
		return node["raw"]

	def visit_BooleanLiteral(self, node):
		return node["raw"]

	def visit_NilLiteral(self, node):
		return node["raw"]

	def visit_VarargLiteral(self, node):
		return node["raw"]

	def visit_Identifier(self, node):
		return node["name"]

	def visit_TableConstructorExpression(self, node):
		table = []

		for field in node["fields"]:
			if field["type"] == "TableValue":
				table.append(self.visit_expr(field["value"]))

			elif field["type"] == "TableKey":
				table.append((
					"[" + self.visit(field["key"]) + "] = " +
					self.visit_expr(field["value"])
				))

			elif field["type"] == "TableKeyString":
				table.append((
					self.visit(field["key"]) + " = " +
					self.visit_expr(field["value"])
				))

		return "({" + (", ".join(table)) + "})"

	def visit_LogicalExpression(self, node):
		return ("(" + self.visit_expr(node["left"]) + " " +
				node["operator"] + " " + self.visit_expr(node["right"]) + ")")

	def visit_UnaryExpression(self, node):
		return ("(" + node["operator"] +
				(" " if node["operator"] == "not" else "") +
				self.visit(node["argument"]) + ")")

	def visit_BinaryExpression(self, node):
		return ("(" + self.visit(node["left"]) + " " +
				node["operator"] + " " + self.visit(node["right"]) + ")")

	def visit_MemberExpression(self, node):
		return (self.visit(node["base"]) + node["indexer"] +
				node["identifier"])

	def visit_IndexExpression(self, node):
		return self.visit(node["base"]) + "[" + self.visit(node["index"]) + "]"

	def visit_CallExpression(self, node):
		return (self.visit_expr(node["base"]) + "(" +
				(", ".join(map(self.visit_expr, node["arguments"]))) +
				")")

	def visit_TableCallExpression(self, node):
		# node["arguments"] must be a TableConstructorExpression
		return self.visit_expr(node["base"]) + self.visit(node["arguments"])

	def visit_StringCallExpression(self, node):
		# node["argument"] must be a StringLiteral
		return self.visit_expr(node["base"]) + self.visit(node["argument"])