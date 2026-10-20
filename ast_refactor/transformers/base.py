"""Base class for AST code transformers."""

from abc import ABC, abstractmethod

from ast_refactor.models import RefactorResult


class BaseTransformer(ABC):
    """Abstract base transformer."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the transformer."""
        pass

    @abstractmethod
    def transform(self, code: str, file_path: str, **kwargs) -> RefactorResult:
        """Apply transformation and return RefactorResult."""
        pass
