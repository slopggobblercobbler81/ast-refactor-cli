"""Automated function extraction for Python and JavaScript."""

import ast
import builtins
from typing import Optional, Set

from ast_refactor.differ import generate_diff
from ast_refactor.models import ExtractionResult

BUILTIN_NAMES = set(dir(builtins))


class FunctionExtractor:
    """Extracts a block of code into a standalone helper function."""

    def extract(
        self,
        code: str,
        file_path: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
        color_diff: bool = False,
    ) -> ExtractionResult:
        """
        Extract statements between start_line and end_line (1-based, inclusive)
        into new_function_name.
        """
        ext = file_path.lower().split(".")[-1] if "." in file_path else ""
        if ext in ("py", "pyw", "pyi"):
            return self._extract_python(
                code=code,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                new_function_name=new_function_name,
                color_diff=color_diff,
            )
        else:
            return self._extract_generic(
                code=code,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                new_function_name=new_function_name,
                color_diff=color_diff,
            )

    def _extract_python(
        self,
        code: str,
        file_path: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
        color_diff: bool,
    ) -> ExtractionResult:
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as e:
            return ExtractionResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                extracted_function_name=new_function_name,
                extracted_code="",
                error=f"SyntaxError parsing {file_path}: {e}",
            )

        lines = code.splitlines(keepends=True)
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return ExtractionResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                extracted_function_name=new_function_name,
                extracted_code="",
                error=f"Invalid line range {start_line}-{end_line} (total lines: {len(lines)})",
            )

        # Find enclosing function if any
        enclosing_fn: Optional[ast.FunctionDef] = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_start = node.lineno
                fn_end = getattr(node, "end_lineno", fn_start)
                if fn_start <= start_line and end_line <= fn_end:
                    if enclosing_fn is None or fn_start > enclosing_fn.lineno:
                        enclosing_fn = node

        # Identify variables read and written in the extracted slice
        read_names: Set[str] = set()
        written_names: Set[str] = set()

        # Variables assigned before start_line in enclosing function or module
        assigned_before: Set[str] = set()
        # Variables read after end_line in enclosing function
        read_after: Set[str] = set()

        if enclosing_fn:
            for node in ast.walk(enclosing_fn):
                if not hasattr(node, "lineno"):
                    continue
                ln = node.lineno
                if ln < start_line:
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        assigned_before.add(node.id)
                    elif isinstance(node, ast.arg):
                        assigned_before.add(node.arg)
                elif start_line <= ln <= end_line:
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Load):
                            read_names.add(node.id)
                        elif isinstance(node.ctx, ast.Store):
                            written_names.add(node.id)
                elif ln > end_line:
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        read_after.add(node.id)
        else:
            # Module-level extraction
            for node in ast.walk(tree):
                if not hasattr(node, "lineno"):
                    continue
                ln = node.lineno
                if ln < start_line:
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        assigned_before.add(node.id)
                elif start_line <= ln <= end_line:
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Load):
                            read_names.add(node.id)
                        elif isinstance(node.ctx, ast.Store):
                            written_names.add(node.id)
                elif ln > end_line:
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        read_after.add(node.id)

        # Input parameters: variables loaded in the block that were assigned before
        # (and not builtins)
        input_params = sorted(
            list((read_names & assigned_before) - BUILTIN_NAMES)
        )
        if not input_params and read_names:
            # Fallback: all read names that are not builtins or written locally first
            input_params = sorted(
                list((read_names - written_names) - BUILTIN_NAMES)
            )

        # Output variables: variables written in block that are read after
        output_vars = sorted(list(written_names & read_after))

        # Extract target lines
        target_lines = lines[start_line - 1 : end_line]
        if not target_lines:
            return ExtractionResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                extracted_function_name=new_function_name,
                extracted_code="",
                error="No lines found in range",
            )

        # Determine base indentation of target lines
        first_line = target_lines[0]
        call_indent = first_line[: len(first_line) - len(first_line.lstrip())]

        # Normalize indentation for the extracted function body
        min_indent = min(
            (len(l) - len(l.lstrip()))
            for l in target_lines
            if l.strip()
        )
        body_lines = [
            ("    " + l[min_indent:]) if l.strip() else "\n"
            for l in target_lines
        ]

        # Add return statement if output variables exist
        if output_vars:
            ret_vals = ", ".join(output_vars)
            body_lines.append(f"    return {ret_vals}\n")

        # Build extracted function definition
        params_str = ", ".join(input_params)
        fn_header = f"def {new_function_name}({params_str}):\n"
        extracted_fn_code = fn_header + "".join(body_lines)

        # Build replacement call in the original function
        if output_vars:
            out_str = ", ".join(output_vars)
            call_code = f"{call_indent}{out_str} = {new_function_name}({params_str})\n"
        else:
            call_code = f"{call_indent}{new_function_name}({params_str})\n"

        # Determine where to place the new function
        # Place before enclosing function or before first target line
        insert_idx = (enclosing_fn.lineno - 1) if enclosing_fn else (start_line - 1)

        # Construct modified code
        new_lines = []
        new_lines.extend(lines[:insert_idx])
        new_lines.append(extracted_fn_code + "\n")
        new_lines.extend(lines[insert_idx : start_line - 1])
        new_lines.append(call_code)
        new_lines.extend(lines[end_line:])

        modified_code = "".join(new_lines)
        diff = generate_diff(code, modified_code, file_path=file_path, color=color_diff)

        return ExtractionResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            extracted_function_name=new_function_name,
            extracted_code=extracted_fn_code,
            input_parameters=input_params,
            output_variables=output_vars,
            diff=diff,
        )

    def _extract_generic(
        self,
        code: str,
        file_path: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
        color_diff: bool,
    ) -> ExtractionResult:
        """Generic function extraction for JavaScript / other languages."""
        lines = code.splitlines(keepends=True)
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return ExtractionResult(
                file_path=file_path,
                original_code=code,
                modified_code=code,
                extracted_function_name=new_function_name,
                extracted_code="",
                error=f"Invalid line range {start_line}-{end_line}",
            )

        target_lines = lines[start_line - 1 : end_line]
        first_line = target_lines[0]
        call_indent = first_line[: len(first_line) - len(first_line.lstrip())]

        min_indent = min(
            (len(l) - len(l.lstrip()))
            for l in target_lines
            if l.strip()
        )
        body_lines = [
            ("  " + l[min_indent:]) if l.strip() else "\n"
            for l in target_lines
        ]

        extracted_fn_code = f"function {new_function_name}() {{\n" + "".join(body_lines) + "}\n"
        call_code = f"{call_indent}{new_function_name}();\n"

        new_lines = []
        new_lines.extend(lines[: start_line - 1])
        new_lines.append(call_code)
        new_lines.extend(lines[end_line:])
        new_lines.append("\n" + extracted_fn_code)

        modified_code = "".join(new_lines)
        diff = generate_diff(code, modified_code, file_path=file_path, color=color_diff)

        return ExtractionResult(
            file_path=file_path,
            original_code=code,
            modified_code=modified_code,
            extracted_function_name=new_function_name,
            extracted_code=extracted_fn_code,
            input_parameters=[],
            output_variables=[],
            diff=diff,
        )
