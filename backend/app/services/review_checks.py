"""Recalculate explicit numeric arithmetic only; never execute courseware code."""
from __future__ import annotations

import ast
import math
import operator
import re

OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
CLAIM = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?(?:\s*[+*/×÷−-]\s*-?\d+(?:\.\d+)?)+)\s*=\s*(-?\d+(?:\.\d+)?)")


def supports_linear(a: float, b: float, source: str) -> bool:
    """Only enable the numeric affine template when its literal x/y equation is present."""
    source = source.replace("\\cdot", "*").replace("\\times", "*").replace("−", "-")
    for match in re.finditer(r"y\s*=\s*([+-]?\d+(?:\.\d+)?)\s*[*×]?\s*x\s*([+-])\s*(\d+(?:\.\d+)?)", source):
        slope, sign, intercept = match.groups()
        if math.isclose(float(slope), a) and math.isclose(float(intercept) * (-1 if sign == '-' else 1), b):
            return True
    return False


def calculate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -calculate(node.operand)
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        result = OPERATORS[type(node.op)](calculate(node.left), calculate(node.right))
        if not math.isfinite(result):
            raise ValueError("Non-finite arithmetic")
        return result
    raise ValueError("Unsupported arithmetic")


def arithmetic_candidates(pages: list[dict], language: str) -> list[dict]:
    candidates = []
    for page in pages:
        for match in CLAIM.finditer(page["text"]):
            expression, claimed = match.groups()
            if len(expression) > 120:
                continue
            try:
                value = calculate(ast.parse(expression.replace("×", "*").replace("÷", "/").replace("−", "-"), mode="eval").body)
                decimals = len(claimed.split(".")[1]) if "." in claimed else 0
                if math.isclose(value, float(claimed), rel_tol=1e-6, abs_tol=.5 * 10 ** -decimals + 1e-9):
                    continue  # Accept rounding at the precision printed by the teacher.
            except (ValueError, ZeroDivisionError, SyntaxError, OverflowError):
                continue
            chinese = language == "zh-CN"
            candidates.append({"original": match.group(), "correction": f"{expression} = {value:.12g}",
                "reason": "对课件中的显式四则运算重新计算；请检查单位与上下文。" if chinese else "Recalculated an explicit arithmetic expression; check units and context.",
                "impact": "只核对该式；对后续结论的影响需人工确认。" if chinese else "Only this expression was checked; downstream impact requires human review.",
                "evidence": [{"page": page["number"], "quote": match.group(), "origin": "text"}]})
    return candidates
