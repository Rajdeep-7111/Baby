"""Safe local arithmetic tool."""

import ast
import operator
from typing import Any


class CalculatorTool:
    """Evaluates a restricted set of arithmetic expressions."""

    name = "calculator"
    description = "Safely evaluates basic arithmetic expressions."
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["expression"],
        "properties": {"expression": {"type": "string"}},
    }
    _binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }
    _unary_operators = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        expression = tool_input.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            return {"success": False, "result": None, "error": "'expression' must be a non-empty string."}
        try:
            parsed = ast.parse(expression, mode="eval")
            value = self._evaluate(parsed.body)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as error:
            return {"success": False, "result": None, "error": f"Invalid expression: {error}"}
        return {"success": True, "result": {"value": value}, "error": None}

    def _evaluate(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._binary_operators:
            return self._binary_operators[type(node.op)](self._evaluate(node.left), self._evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._unary_operators:
            return self._unary_operators[type(node.op)](self._evaluate(node.operand))
        raise ValueError("Only numbers and +, -, *, /, %, and parentheses are supported.")
