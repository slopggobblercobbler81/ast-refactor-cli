"""Safe AST-based symbol renaming for Python and JavaScript."""

import ast
import re
from typing import List, Optional, Tuple

from ast_refactor.differ import generate_diff
from ast_refactor.models import RefactorResult
from ast_refactor.transformers.base import BaseTransformer


class SymbolRenamer(BaseTransformer):
    """AST-based symbol renamer that preserves formatting and comments."""

    @property
    def name(self) -> str:
        return "renamer"

    def transform(
        self,
        code: str,
        file_path: str,
        old_name: str,
        new_name: str,
        scope: Optional[str] = None,
        rename_attributes: bool = False,
        color_diff: bool = False,
        **kwargs,
    ) -> RefactorResult:
        if not old_name or not new_name or old_name == new_name:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
            )

        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        if ext in ("py", "pyw", "pyi"):
            return self._rename_python(
                code=code,
                file_path=file_path,
                old_name=old_name,
                new_name=new_name,
                scope=scope,
                rename_attributes=rename_attributes,
                color_diff=color_diff,
            )
        elif ext in ("js", "jsx", "mjs", "cjs", "ts", "tsx"):
            return self._rename_javascript(
                code=code,
                file_path=file_path,
                old_name=old_name,
                new_name=new_name,
                scope=scope,
                color_diff=color_diff,
            )
        else:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
                error=f"Unsupported file extension: .{ext}",
            )

    def _rename_python(
        self,
        code: str,
        file_path: str,
        old_name: str,
        new_name: str,
        scope: Optional[str],
        rename_attributes: bool,
        color_diff: bool,
    ) -> RefactorResult:
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as e:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                error=f"SyntaxError parsing {file_path}: {e}",
            )

        # Locate scope root if specified
        target_root: ast.AST = tree
        if scope:
            found = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == scope:
                        found = node
                        break
            if found is None:
                return RefactorResult(
                    file_path=file_path,
                    original_code=code,
                    modified_code=code,
                    changes_count=0,
                    error=f"Scope '{scope}' not found in {file_path}",
                )
            target_root = found

        lines = code.splitlines(keepends=True)
        # Slices to replace: (line_idx, start_col, end_col)
        replacements: List[Tuple[int, int, int]] = []

        # Walk target subtree
        for node in ast.walk(target_root):
            # 1. Variables and references
            if isinstance(node, ast.Name) and node.id == old_name:
                line_idx = node.lineno - 1
                start_col = node.col_offset
                end_col = getattr(node, "end_col_offset", start_col + len(old_name))
                replacements.append((line_idx, start_col, end_col))

            # 2. Function definitions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == old_name:
                line_idx = node.lineno - 1
                line_text = lines[line_idx]
                match = re.search(rf"\bdef\s+({re.escape(old_name)})\b", line_text)
                if match:
                    start_col = match.start(1)
                    end_col = match.end(1)
                    replacements.append((line_idx, start_col, end_col))

            # 3. Class definitions
            elif isinstance(node, ast.ClassDef) and node.name == old_name:
                line_idx = node.lineno - 1
                line_text = lines[line_idx]
                match = re.search(rf"\bclass\s+({re.escape(old_name)})\b", line_text)
                if match:
                    start_col = match.start(1)
                    end_col = match.end(1)
                    replacements.append((line_idx, start_col, end_col))

            # 4. Function arguments
            elif isinstance(node, ast.arg) and node.arg == old_name:
                line_idx = node.lineno - 1
                start_col = node.col_offset
                end_col = getattr(node, "end_col_offset", start_col + len(old_name))
                replacements.append((line_idx, start_col, end_col))

            # 5. Attributes (if requested)
            elif rename_attributes and isinstance(node, ast.Attribute) and node.attr == old_name:
                line_idx = node.lineno - 1
                line_text = lines[line_idx]
                end_col = getattr(node, "end_col_offset", None)
                if end_col is not None:
                    start_col = end_col - len(old_name)
                    replacements.append((line_idx, start_col, end_col))
                else:
                    match = re.search(rf"\.({re.escape(old_name)})\b", line_text)
                    if match:
                        replacements.append((line_idx, match.start(1), match.end(1)))

            # 6. Global / nonlocal
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                if old_name in node.names:
                    line_idx = node.lineno - 1
                    line_text = lines[line_idx]
                    for m in re.finditer(rf"\b({re.escape(old_name)})\b", line_text):
                        replacements.append((line_idx, m.start(1), m.end(1)))

            # 7. Import alias
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name == old_name or alias.asname == old_name:
                        line_idx = node.lineno - 1
                        line_text = lines[line_idx]
                        for m in re.finditer(rf"\b({re.escape(old_name)})\b", line_text):
                            replacements.append((line_idx, m.start(1), m.end(1)))

        # Deduplicate and sort replacements in reverse order (bottom to top, right to left)
        unique_reps = sorted(list(set(replacements)), key=lambda x: (x[0], x[1]), reverse=True)
        changes_count = len(unique_reps)

        if changes_count == 0:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
            )

        # Apply replacements to lines
        modified_lines = list(lines)
        for line_idx, start_col, end_col in unique_reps:
            current = modified_lines[line_idx]
            # Verify the slice matches old_name to be 100% safe
            if current[start_col:end_col] == old_name:
                modified_lines[line_idx] = current[:start_col] + new_name + current[end_col:]

        modified_code = "".join(modified_lines)
        diff = generate_diff(code, modified_code, file_path=file_path, color=color_diff)

        return RefactorResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            changes_count=changes_count,
            diff=diff,
        )

    def _rename_javascript(
        self,
        code: str,
        file_path: str,
        old_name: str,
        new_name: str,
        scope: Optional[str],
        color_diff: bool,
    ) -> RefactorResult:
        # Determine scope boundaries
        start_bound = 0
        end_bound = len(code)

        if scope:
            fn_match = re.search(
                rf"(?:function\s+{re.escape(scope)}\s*\([^)]*\)|(?:const|let|var)\s+{re.escape(scope)}\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)\s*\{{",
                code,
            )
            if not fn_match:
                return RefactorResult(
                    file_path=file_path,
                    original_code=code,
                    modified_code=code,
                    changes_count=0,
                    error=f"Scope '{scope}' not found in {file_path}",
                )
            start_bound = fn_match.end() - 1
            # Find matching closing brace
            depth = 0
            for i in range(start_bound, len(code)):
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end_bound = i + 1
                        break

        # Identify strings and comments so they are excluded
        excluded_spans: List[Tuple[int, int]] = []
        n = len(code)
        i = 0
        while i < n:
            c = code[i]
            nxt = code[i + 1] if i + 1 < n else ""

            if c == "/" and nxt == "/":
                start = i
                while i < n and code[i] != "\n":
                    i += 1
                excluded_spans.append((start, i))
                continue

            if c == "/" and nxt == "*":
                start = i
                i += 2
                while i < n - 1 and not (code[i] == "*" and code[i + 1] == "/"):
                    i += 1
                i = min(i + 2, n)
                excluded_spans.append((start, i))
                continue

            if c in ("'", '"', "`"):
                quote = c
                start = i
                i += 1
                while i < n:
                    if code[i] == "\\" and i + 1 < n:
                        i += 2
                        continue
                    if code[i] == quote:
                        i += 1
                        break
                    i += 1
                excluded_spans.append((start, i))
                continue

            i += 1

        def is_in_excluded(offset: int) -> bool:
            for s, e in excluded_spans:
                if s <= offset < e:
                    return True
            return False

        # Find identifier matches
        pattern = re.compile(rf"\b{re.escape(old_name)}\b")
        matches = []
        for m in pattern.finditer(code):
            if start_bound <= m.start() < end_bound:
                if not is_in_excluded(m.start()):
                    matches.append((m.start(), m.end()))

        changes_count = len(matches)
        if changes_count == 0:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
            )

        # Apply replacements in reverse offset order
        chars = list(code)
        for s, e in sorted(matches, reverse=True):
            chars[s:e] = list(new_name)

        modified_code = "".join(chars)
        diff = generate_diff(code, modified_code, file_path=file_path, color=color_diff)

        return RefactorResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            changes_count=changes_count,
            diff=diff,
        )
