"""
ast-refactor-cli: Fast developer CLI for safe AST-based symbol renaming,
automated function extraction, and syntax modernization across Python and JavaScript codebases.
"""

__version__ = "0.1.0"
__author__ = "slopggobblercobbler81"
__license__ = "MIT"

from ast_refactor.models import RefactorResult
from ast_refactor.engine import RefactorEngine

__all__ = ["__version__", "RefactorResult", "RefactorEngine"]
