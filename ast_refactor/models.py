"""Data models for ast-refactor-cli."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RefactorResult:
    """Outcome of a refactoring operation on a file."""
    file_path: str
    original_code: str
    modified_code: str
    changes_count: int = 0
    diff: str = ""
    error: Optional[str] = None

    @property
    def has_changed(self) -> bool:
        return self.original_code != self.modified_code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "has_changed": self.has_changed,
            "changes_count": self.changes_count,
            "diff": self.diff,
            "error": self.error,
        }


@dataclass
class ExtractionResult:
    """Outcome of extracting a block of code into a function."""
    file_path: str
    original_code: str
    modified_code: str
    extracted_function_name: str
    extracted_code: str
    input_parameters: List[str] = field(default_factory=list)
    output_variables: List[str] = field(default_factory=list)
    diff: str = ""
    error: Optional[str] = None

    @property
    def has_changed(self) -> bool:
        return self.original_code != self.modified_code


@dataclass
class ModernizationRecord:
    """Record of a modernized syntax pattern."""
    rule_name: str
    line: int
    description: str


@dataclass
class EngineSummary:
    """Summary of refactoring across multiple files."""
    total_files: int = 0
    modified_files: int = 0
    total_changes: int = 0
    results: List[RefactorResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "modified_files": self.modified_files,
            "total_changes": self.total_changes,
            "results": [r.to_dict() for r in self.results],
        }
