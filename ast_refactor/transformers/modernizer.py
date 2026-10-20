"""Syntax modernizer for Python and JavaScript codebases."""

import ast
import re
from typing import List, Optional, Set, Tuple

from ast_refactor.differ import generate_diff
from ast_refactor.models import ModernizationRecord, RefactorResult
from ast_refactor.transformers.base import BaseTransformer


class SyntaxModernizer(BaseTransformer):
    """Modernizes legacy syntax idioms to modern standards."""

    @property
    def name(self) -> str:
        return "modernizer"

    def transform(
        self,
        code: str,
        file_path: str,
        rules: Optional[Set[str]] = None,
        color_diff: bool = False,
        **kwargs,
    ) -> RefactorResult:
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        if ext in ("py", "pyw", "pyi"):
            return self._modernize_python(code, file_path, rules=rules, color_diff=color_diff)
        elif ext in ("js", "jsx", "mjs", "cjs", "ts", "tsx"):
            return self._modernize_javascript(code, file_path, rules=rules, color_diff=color_diff)
        else:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
            )

    def _modernize_python(
        self,
        code: str,
        file_path: str,
        rules: Optional[Set[str]],
        color_diff: bool,
    ) -> RefactorResult:
        active_rules = rules or {
            "has_key",
            "isinstance_tuple",
            "open_read_mode",
            "dict_comp",
            "fstrings",
        }

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

        lines = code.splitlines(keepends=True)
        # Slices to replace: (line_idx, start_col, end_col, replacement_str)
        replacements: List[Tuple[int, int, int, str]] = []
        records: List[ModernizationRecord] = []

        # 1. Rule: has_key -> 'k in d'
        if "has_key" in active_rules:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "has_key":
                        if len(node.args) == 1 and hasattr(node, "lineno"):
                            line_idx = node.lineno - 1
                            line_text = lines[line_idx]
                            start_col = node.col_offset
                            end_col = getattr(node, "end_col_offset", None)
                            if end_col is not None:
                                # Extract key code and dict expression
                                d_node = node.func.value
                                k_node = node.args[0]
                                d_str = line_text[d_node.col_offset : getattr(d_node, "end_col_offset", d_node.col_offset)]
                                k_str = line_text[k_node.col_offset : getattr(k_node, "end_col_offset", k_node.col_offset)]
                                if d_str and k_str:
                                    rep = f"{k_str} in {d_str}"
                                    replacements.append((line_idx, start_col, end_col, rep))
                                    records.append(
                                        ModernizationRecord(
                                            rule_name="has_key",
                                            line=node.lineno,
                                            description=f"Replaced dict.has_key(...) with 'in' operator",
                                        )
                                    )

        # 2. Rule: isinstance(x, (T,)) -> isinstance(x, T)
        if "isinstance_tuple" in active_rules:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                        if len(node.args) == 2 and isinstance(node.args[1], ast.Tuple):
                            tup = node.args[1]
                            if len(tup.elts) == 1 and hasattr(tup, "lineno"):
                                line_idx = tup.lineno - 1
                                line_text = lines[line_idx]
                                elt = tup.elts[0]
                                elt_str = line_text[elt.col_offset : getattr(elt, "end_col_offset", elt.col_offset)]
                                start_col = tup.col_offset
                                end_col = getattr(tup, "end_col_offset", None)
                                if end_col is not None and elt_str:
                                    replacements.append((line_idx, start_col, end_col, elt_str))
                                    records.append(
                                        ModernizationRecord(
                                            rule_name="isinstance_tuple",
                                            line=node.lineno,
                                            description="Simplified single-element tuple in isinstance",
                                        )
                                    )

        # 3. Rule: open(..., "r") -> open(...)
        if "open_read_mode" in active_rules:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "open":
                        if len(node.args) == 2 and isinstance(node.args[1], ast.Constant):
                            if node.args[1].value == "r":
                                arg1 = node.args[1]
                                arg0 = node.args[0]
                                line_idx = arg1.lineno - 1
                                line_text = lines[line_idx]
                                # remove , 'r'
                                start_col = getattr(arg0, "end_col_offset", arg0.col_offset)
                                end_col = getattr(arg1, "end_col_offset", arg1.col_offset)
                                match = re.search(r",\s*['\"]r['\"]", line_text[start_col:end_col])
                                if match:
                                    real_start = start_col + match.start()
                                    real_end = start_col + match.end()
                                    replacements.append((line_idx, real_start, real_end, ""))
                                    records.append(
                                        ModernizationRecord(
                                            rule_name="open_read_mode",
                                            line=node.lineno,
                                            description="Removed redundant 'r' default mode in open()",
                                        )
                                    )

        # 4. Rule: dict([(k, v), ...]) -> {k: v, ...}
        if "dict_comp" in active_rules:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "dict":
                        if len(node.args) == 1 and isinstance(node.args[0], ast.ListComp):
                            comp = node.args[0]
                            elt = comp.elt
                            if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) == 2:
                                line_idx = node.lineno - 1
                                line_text = lines[line_idx]
                                start_col = node.col_offset
                                end_col = getattr(node, "end_col_offset", None)
                                k_node, v_node = elt.elts
                                k_str = line_text[k_node.col_offset : getattr(k_node, "end_col_offset", k_node.col_offset)]
                                v_str = line_text[v_node.col_offset : getattr(v_node, "end_col_offset", v_node.col_offset)]
                                # generators part
                                gen = comp.generators[0]
                                target_str = line_text[gen.target.col_offset : getattr(gen.target, "end_col_offset", gen.target.col_offset)]
                                iter_str = line_text[gen.iter.col_offset : getattr(gen.iter, "end_col_offset", gen.iter.col_offset)]
                                if end_col is not None and k_str and v_str and target_str and iter_str:
                                    new_dict_comp = f"{{{k_str}: {v_str} for {target_str} in {iter_str}}}"
                                    replacements.append((line_idx, start_col, end_col, new_dict_comp))
                                    records.append(
                                        ModernizationRecord(
                                            rule_name="dict_comp",
                                            line=node.lineno,
                                            description="Converted dict(list-comprehension) to dict comprehension",
                                        )
                                    )

        # Apply replacements in reverse order
        replacements.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if not replacements:
            return RefactorResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                changes_count=0,
                diff="",
            )

        mod_lines = list(lines)
        for line_idx, start_col, end_col, rep_str in replacements:
            line_val = mod_lines[line_idx]
            mod_lines[line_idx] = line_val[:start_col] + rep_str + line_val[end_col:]

        modified_code = "".join(mod_lines)
        diff = generate_diff(code, modified_code, file_path=file_path, color=color_diff)

        return RefactorResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            changes_count=len(replacements),
            diff=diff,
        )

    def _modernize_javascript(
        self,
        code: str,
        file_path: str,
        rules: Optional[Set[str]],
        color_diff: bool,
    ) -> RefactorResult:
        active_rules = rules or {"var_to_let", "arrow_callbacks"}
        modified = code
        changes = 0

        # 1. var to let (where safe)
        if "var_to_let" in active_rules:
            var_pattern = re.compile(r"\bvar\s+([a-zA-Z_$][a-zA-Z0-9_$]*)")
            new_code, count = var_pattern.subn(r"let \1", modified)
            if count > 0:
                changes += count
                modified = new_code

        # 2. Simple anonymous callback functions function(x) { return y; } -> (x) => y
        if "arrow_callbacks" in active_rules:
            fn_arrow_pattern = re.compile(
                r"function\s*\(\s*([^)]*)\s*\)\s*\{\s*return\s+([^;{}]+);\s*\}"
            )
            new_code, count = fn_arrow_pattern.subn(r"(\1) => \2", modified)
            if count > 0:
                changes += count
                modified = new_code

        diff = generate_diff(code, modified, file_path=file_path, color=color_diff)
        return RefactorResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified,
            changes_count=changes,
            diff=diff,
        )
