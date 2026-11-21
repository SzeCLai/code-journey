"""Static source analysis for loop, condition, and warning metadata."""

from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple


@dataclass(frozen=True)
class LoopInfo:
    loop_id: str
    kind: str
    line_number: int
    end_line: int
    body_start: int
    body_end: int
    header: str
    total_iterations: Optional[int]

    def contains(self, line_number: int) -> bool:
        return self.body_start <= line_number <= self.body_end


@dataclass(frozen=True)
class ConditionInfo:
    condition_id: str
    kind: str
    line_number: int
    body_start: int
    body_end: int
    expression: str

    def body_contains(self, line_number: int) -> bool:
        return self.body_start <= line_number <= self.body_end


@dataclass(frozen=True)
class EducationalWarning:
    code: str
    message: str
    line_number: Optional[int] = None


@dataclass(frozen=True)
class ProgramAnalysis:
    loops: Tuple[LoopInfo, ...]
    conditions: Tuple[ConditionInfo, ...]
    warnings: Tuple[EducationalWarning, ...]

    @property
    def loops_by_line(self) -> Dict[int, LoopInfo]:
        return {loop.line_number: loop for loop in self.loops}

    @property
    def conditions_by_line(self) -> Dict[int, ConditionInfo]:
        return {condition.line_number: condition for condition in self.conditions}


def _block_span(statements: Iterable[ast.stmt]) -> Tuple[int, int]:
    statements = tuple(statements)
    if not statements:
        return 0, -1
    start = min(statement.lineno for statement in statements)
    end = max(getattr(statement, "end_lineno", statement.lineno) for statement in statements)
    return start, end


def _known_iterable_length(node: ast.AST) -> Optional[int]:
    try:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "range":
                args = [ast.literal_eval(argument) for argument in node.args]
                if all(type(argument) is int for argument in args) and 1 <= len(args) <= 3:
                    return len(range(*args))
        value = ast.literal_eval(node)
        if type(value) in (list, tuple, set, dict, str, bytes):
            return len(value)
    except (ValueError, TypeError, MemoryError):
        return None
    return None


class _Analyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.loops = []
        self.conditions = []
        self.warnings = []
        self._loop_number = 0
        self._condition_number = 0
        self._warning_keys = set()

    def _warn(self, code: str, message: str, line_number: Optional[int]) -> None:
        key = code, line_number
        if key not in self._warning_keys:
            self._warning_keys.add(key)
            self.warnings.append(EducationalWarning(code, message, line_number))

    def _add_loop(self, node: ast.AST, kind: str, header: str, total: Optional[int]) -> None:
        body = getattr(node, "body", ())
        body_start, body_end = _block_span(body)
        line_number = node.lineno
        self._loop_number += 1
        loop_id = f"loop-{self._loop_number}"
        loop = LoopInfo(
            loop_id=loop_id,
            kind=kind,
            line_number=line_number,
            end_line=getattr(node, "end_lineno", line_number),
            body_start=body_start,
            body_end=body_end,
            header=header,
            total_iterations=total,
        )
        self.loops.append(loop)
        for statement in body:
            self.visit(statement)

        iterated_name = None
        if kind == "for" and isinstance(node, ast.For):
            if isinstance(node.iter, ast.Name):
                iterated_name = node.iter.id
            elif (
                isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id in {"enumerate", "iter", "reversed"}
                and node.iter.args
                and isinstance(node.iter.args[0], ast.Name)
            ):
                iterated_name = node.iter.args[0].id
        if iterated_name is not None:
            for statement in ast.walk(node):
                if statement is node:
                    continue
                mutation_name = None
                if isinstance(statement, ast.Call) and isinstance(statement.func, ast.Attribute):
                    if statement.func.attr in {"append", "extend", "insert", "pop", "remove", "clear", "sort", "reverse"}:
                        if isinstance(statement.func.value, ast.Name):
                            mutation_name = statement.func.value.id
                elif isinstance(statement, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
                    if isinstance(statement, (ast.Assign, ast.Delete)):
                        targets = statement.targets
                    else:
                        targets = [getattr(statement, "target", None)]
                    for target in targets:
                        for item in ast.walk(target) if target is not None else ():
                            if isinstance(item, ast.Subscript) and isinstance(item.value, ast.Name):
                                mutation_name = item.value.id
                            elif (
                                isinstance(statement, ast.AugAssign)
                                and isinstance(item, ast.Name)
                                and item is target
                            ):
                                mutation_name = item.id
                if mutation_name == iterated_name:
                    self._warn(
                        "list-mutated-during-iteration",
                        f"'{iterated_name}' may be changed while it is being iterated over.",
                        getattr(statement, "lineno", line_number),
                    )

        for statement in ast.walk(node):
            if statement is node:
                continue
            if isinstance(statement, ast.Break):
                self._warn(
                    "break-first-iteration",
                    "This loop can stop with `break` during its first iteration.",
                    statement.lineno,
                )
            elif isinstance(statement, ast.Return):
                self._warn(
                    "return-first-iteration",
                    "This function can return during a loop's first iteration.",
                    statement.lineno,
                )

        for statement in getattr(node, "orelse", ()):
            self.visit(statement)

    def visit_For(self, node: ast.For) -> None:
        self._add_loop(node, "for", f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}", _known_iterable_length(node.iter))

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._add_loop(node, "for", f"async for {ast.unparse(node.target)} in {ast.unparse(node.iter)}", None)

    def visit_While(self, node: ast.While) -> None:
        self._add_loop(node, "while", f"while {ast.unparse(node.test)}", None)
        self._add_condition(node, "while", node.test, node.body)

    def visit_If(self, node: ast.If) -> None:
        self._add_condition(node, "if", node.test, node.body)
        for statement in node.body:
            self.visit(statement)
        for statement in node.orelse:
            self.visit(statement)

    def _add_condition(
        self,
        node: ast.AST,
        kind: str,
        expression: ast.AST,
        body: Iterable[ast.stmt],
    ) -> None:
        body_start, body_end = _block_span(body)
        self._condition_number += 1
        self.conditions.append(
            ConditionInfo(
                condition_id=f"condition-{self._condition_number}",
                kind=kind,
                line_number=node.lineno,
                body_start=body_start,
                body_end=body_end,
                expression=ast.unparse(expression),
            )
        )

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Param)) and node.id in vars(builtins):
            self._warn(
                "builtin-shadowing",
                f"'{node.id}' shadows a Python built-in name.",
                node.lineno,
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in vars(builtins):
            self._warn(
                "builtin-shadowing",
                f"'{node.name}' shadows a Python built-in name.",
                node.lineno,
            )
        arguments = (
            node.args.posonlyargs
            + node.args.args
            + node.args.kwonlyargs
            + ([node.args.vararg] if node.args.vararg is not None else [])
            + ([node.args.kwarg] if node.args.kwarg is not None else [])
        )
        for argument in arguments:
            if argument.arg in vars(builtins):
                self._warn(
                    "builtin-shadowing",
                    f"'{argument.arg}' shadows a Python built-in name.",
                    argument.lineno if hasattr(argument, "lineno") else node.lineno,
                )
        for statement in node.body:
            self.visit(statement)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        for imported in node.names:
            name = imported.asname or imported.name.split(".", 1)[0]
            if name in vars(builtins):
                self._warn(
                    "builtin-shadowing",
                    f"'{name}' shadows a Python built-in name.",
                    node.lineno,
                )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for imported in node.names:
            name = imported.asname or imported.name
            if name in vars(builtins):
                self._warn(
                    "builtin-shadowing",
                    f"'{name}' shadows a Python built-in name.",
                    node.lineno,
                )

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name in vars(builtins):
            self._warn(
                "builtin-shadowing",
                f"'{node.name}' shadows a Python built-in name.",
                node.lineno,
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in vars(builtins):
            self._warn("builtin-shadowing", f"'{node.name}' shadows a Python built-in name.", node.lineno)
        for statement in node.body:
            self.visit(statement)


def analyze_source(source: str) -> ProgramAnalysis:
    tree = ast.parse(source)
    analyzer = _Analyzer()
    analyzer.visit(tree)
    return ProgramAnalysis(
        loops=tuple(analyzer.loops),
        conditions=tuple(analyzer.conditions),
        warnings=tuple(analyzer.warnings),
    )
