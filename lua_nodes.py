def Chunk(body):
	return {"type": "Chunk", "body": body, "comments": []}

def BreakStatement():
	return {"type": "BreakStatement"}

def ReturnStatement(arguments):
	return {"type": "ReturnStatement", "arguments": arguments}

def IfStatement(clauses):
	return {"type": "IfStatement", "clauses": clauses}

def IfClause(condition, body):
	return {"type": "IfClause", "condition": condition, "body": body}

def ElseifClause(condition, body):
	return {"type": "ElseifClause", "condition": condition, "body": body}

def ElseClause(body):
	return {"type": "ElseClause", "body": body}

def WhileStatement(condition, body):
	return {"type": "WhileStatement", "condition": condition, "body": body}

def DoStatement(body):
	return {"type": "DoStatement", "body": body}

def RepeatStatement(condition, body):
	return {"type": "RepeatStatement", "condition": condition, "body": body}

def AssignmentStatement(local, variables, init):
	return {
		"type": "LocalStatement" if local else "AssignmentStatement",
		"variables": variables,
		"init": init
	}

def CallStatement(expression):
	return {"type": "CallStatement", "expression": expression}

def CallExpression(base, arguments):
	return {"type": "CallExpression", "base": base, "arguments": arguments}

def FunctionStatement(id, params, body):
	return {
		"type": "FunctionDeclaration",
		"identifier": id,
		"isLocal": False,
		"parameters": params,
		"body": body
	}

def ForNumericStatement(variable, start, end, step, body):
	return {
		"type": "ForNumericStatement",
		"variable": variable,
		"start": start,
		"end": end,
		"step": step,
		"body": body
	}

def ForGenericStatement(variables, iterators, body):
	return {
		"type": "ForGenericStatement",
		"variables": variables,
		"iterators": iterators,
		"body": body
	}

def Identifier(name):
	return {"type": "Identifier", "name": name}

def StringLiteral(s):
	return {"type": "StringLiteral", "value": s, "raw": repr(s)}

def NumericLiteral(n):
	return {"type": "NumericLiteral", "value": n, "raw": str(n)}

def BooleanLiteral(b):
	return {"type": "BooleanLiteral", "value": b, "raw": str(b).lower()}

def NilLiteral():
	return {"type": "NilLiteral", "value": None, "raw": "nil"}

def VarargLiteral():
	return {"type": "VarargLiteral", "value": "...", "raw": "..."}

def Literal(value):
	if isinstance(value, str):
		return StringLiteral(value)
	if isinstance(value, bool):
		return BooleanLiteral(value)
	if isinstance(value, (int, float)):
		return NumericLiteral(value)
	if value is None:
		return NilLiteral()
	return VarargLiteral()

def TableKey(key, value):
	return {
		"type": "TableKey",
		"key": key,
		"value": value
	}

def TableKeyString(key, value):
	return {
		"type": "TableKeyString",
		"key": key,
		"value": value
	}

def TableValue(value):
	return {
		"type": "TableValue",
		"value": value
	}

def TableConstructorExpression(fields):
	return {
		"type": "TableConstructorExpression",
		"fields": fields
	}

def LogicalExpression(operator, left, right):
	return {
		"type": "LogicalExpression",
		"operator": operator,
		"left": left,
		"right": right
	}

def BinaryExpression(operator, left, right):
	return {
		"type": "BinaryExpression",
		"operator": operator,
		"left": left,
		"right": right
	}

def UnaryExpression(operator, argument):
	return {
		"type": "UnaryExpression",
		"operator": operator,
		"argument": argument
	}

def MemberExpression(base, indexer, identifier):
	return {
		"type": "MemberExpression",
		"indexer": indexer,
		"identifier": identifier,
		"base": base
	}

def IndexExpression(base, index):
	return {
		"type": "IndexExpression",
		"base": base,
		"index": index
	}