import re
import os
import ast
import operator
import subprocess

def copy_to_clipboard(text):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc  = subprocess.Popen(
            ['clip'],
            stdin=subprocess.PIPE,
            shell=False,
            creationflags=flags,
        )
        proc.communicate(input=str(text).encode('utf-16le'))
    except Exception:
        pass

_OPERATORS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Mod:  operator.mod,
    ast.Pow:  operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported operation: {ast.dump(node)}")


def on_search(text):
    results = []
    query = text.strip()

    # Regex acts as a filter: if it doesn't look like math, skip it
    if re.match(r"^[\d\s\+\-\*\/\.\(\)\%\^\*\*]+$", query):

        # Safety: requires at least one math operator and one digit
        if any(c in "+-*/%^" for c in query) and any(c.isdigit() for c in query):
            try:
                eval_query = query.replace('^', '**')

                # Safe AST-based evaluation — no eval(), no builtins access
                result = _safe_eval(ast.parse(eval_query, mode="eval"))

                if isinstance(result, float):
                    result = round(result, 6)  # Clean up float precision

                results.append({
                    "name": f"= {result}",
                    "score": 1000,  # High score to always appear at the top
                    "action": lambda: copy_to_clipboard(str(result)),
                    "icon_type": "calc"
                })
            except Exception:
                pass

    return results
