from setuptools import setup, find_packages

setup(
    name="ast-refactor-cli",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "ast-refactor = ast_refactor.cli:main",
        ],
    },
    python_requires=">=3.8",
)
