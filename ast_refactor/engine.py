"""Orchestrator engine for ast-refactor-cli."""

import os
from pathlib import Path
from typing import List, Optional, Set

from ast_refactor.models import EngineSummary, ExtractionResult, RefactorResult
from ast_refactor.transformers.extractor import FunctionExtractor
from ast_refactor.transformers.modernizer import SyntaxModernizer
from ast_refactor.transformers.renamer import SymbolRenamer

DEFAULT_IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    ".egg-info",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".pyw",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
}


class RefactorEngine:
    """Dispatches refactoring operations across files and directories."""

    def __init__(self, color_diff: bool = False):
        self.color_diff = color_diff
        self.renamer = SymbolRenamer()
        self.extractor = FunctionExtractor()
        self.modernizer = SyntaxModernizer()

    def discover_files(self, paths: List[str]) -> List[str]:
        """Discover all supported source files in target paths."""
        found: List[str] = []
        seen: Set[str] = set()

        for target in paths:
            p = Path(target)
            if not p.exists():
                continue

            if p.is_file():
                if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    resolved = str(p.resolve())
                    if resolved not in seen:
                        seen.add(resolved)
                        found.append(str(p))
            elif p.is_dir():
                for root, dirs, files in os.walk(str(p)):
                    dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
                    for f in files:
                        _, ext = os.path.splitext(f)
                        if ext.lower() in SUPPORTED_EXTENSIONS:
                            full_path = os.path.join(root, f)
                            resolved = str(Path(full_path).resolve())
                            if resolved not in seen:
                                seen.add(resolved)
                                found.append(full_path)

        found.sort()
        return found

    def rename_symbol(
        self,
        paths: List[str],
        old_name: str,
        new_name: str,
        scope: Optional[str] = None,
        rename_attributes: bool = False,
        in_place: bool = False,
    ) -> EngineSummary:
        """Rename an identifier across discovered files."""
        files = self.discover_files(paths)
        results: List[RefactorResult] = []
        modified_count = 0
        total_changes = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                results.append(
                    RefactorResult(
                        file_path=file_path,
                        original_code="",
                        modified_code="",
                        error=f"Could not read {file_path}: {e}",
                    )
                )
                continue

            res = self.renamer.transform(
                code=code,
                file_path=file_path,
                old_name=old_name,
                new_name=new_name,
                scope=scope,
                rename_attributes=rename_attributes,
                color_diff=self.color_diff,
            )

            if res.has_changed:
                modified_count += 1
                total_changes += res.changes_count
                if in_place:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(res.modified_code)

            results.append(res)

        return EngineSummary(
            total_files=len(files),
            modified_files=modified_count,
            total_changes=total_changes,
            results=results,
        )

    def extract_function(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        new_function_name: str,
        in_place: bool = False,
    ) -> ExtractionResult:
        """Extract a statement block into a new function."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            return ExtractionResult(
                file_path=file_path,
                original_code="",
                modified_code="",
                extracted_function_name=new_function_name,
                extracted_code="",
                error=f"Could not read {file_path}: {e}",
            )

        res = self.extractor.extract(
            code=code,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            new_function_name=new_function_name,
            color_diff=self.color_diff,
        )

        if in_place and res.has_changed and not res.error:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(res.modified_code)

        return res

    def modernize_syntax(
        self,
        paths: List[str],
        rules: Optional[Set[str]] = None,
        in_place: bool = False,
    ) -> EngineSummary:
        """Modernize syntax across discovered files."""
        files = self.discover_files(paths)
        results: List[RefactorResult] = []
        modified_count = 0
        total_changes = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception as e:
                results.append(
                    RefactorResult(
                        file_path=file_path,
                        original_code="",
                        modified_code="",
                        error=f"Could not read {file_path}: {e}",
                    )
                )
                continue

            res = self.modernizer.transform(
                code=code,
                file_path=file_path,
                rules=rules,
                color_diff=self.color_diff,
            )

            if res.has_changed:
                modified_count += 1
                total_changes += res.changes_count
                if in_place:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(res.modified_code)

            results.append(res)

        return EngineSummary(
            total_files=len(files),
            modified_files=modified_count,
            total_changes=total_changes,
            results=results,
        )
