# ast-refactor-cli

[![CI](https://github.com/slopggobblercobbler81/ast-refactor-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/ast-refactor-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](pyproject.toml)

> A lightning-fast, zero-dependency developer CLI for **safe AST-based symbol renaming**, **automated function extraction**, and **syntax modernization** across Python and JavaScript / TypeScript codebases.

---

## Why ast-refactor-cli?

Text-based `find-and-replace` or regex refactoring is error-prone:
- It accidentally edits strings or comments containing the same word.
- It mangles partial word substrings (e.g. replacing `count` also breaks `counter` or `account`).
- It has no concept of lexical scopes, function boundaries, or argument passing.

`ast-refactor` analyzes real AST tokens and structural bounds:
1. **100% Safe Symbol Renaming**: Accurately targets identifier symbols, function definitions, parameters, and classes without touching string contents or comments.
2. **Automated Function Extraction**: Select any range of lines and automatically extract them into a new helper function, correctly calculating parameters, return values, and call-site assignments.
3. **Syntax Modernization**: Automatically upgrades legacy syntax patterns to modern, cleaner idioms.
4. **Instant Diff Preview**: Preview refactoring changes with colorful unified diffs before applying in-place.

---

## Features

- **Multi-Language**: Native AST parsing for Python (`.py`, `.pyw`, `.pyi`) and lexical AST token analysis for JavaScript/TypeScript (`.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`).
- **Scope-Constrained Renaming**: Rename variables only within a specific function (`--scope my_func`) without touching identically-named variables elsewhere.
- **Smart Function Extraction**:
  - Automatically identifies variables read in the extracted block that originate from outer scope (`input_parameters`).
  - Automatically identifies variables modified in the extracted block that are read later (`output_variables`).
  - Rewrites the call site and places the new function cleanly.
- **Syntax Modernization Rules**:
  - `has_key`: Upgrades `d.has_key(k)` to `k in d`.
  - `isinstance_tuple`: Simplifies `isinstance(x, (int,))` to `isinstance(x, int)`.
  - `open_read_mode`: Removes redundant `"r"` mode in `open(..., "r")`.
  - `dict_comp`: Converts `dict([(k, v) for ...])` to `{k: v for ...}`.
  - `var_to_let`: Modernizes JavaScript `var` declarations to `let`.
  - `arrow_callbacks`: Converts anonymous functions to modern arrow syntax.
- **CI Mode (`--check`)**: Returns non-zero exit code if pending refactorings or modernizations exist.

---

## Installation

```bash
git clone https://github.com/slopggobblercobbler81/ast-refactor-cli.git
cd ast-refactor-cli
pip install -e .
```

---

## CLI Usage Guide

### 1. Safe Symbol Renaming (`rename`)

#### Dry-run preview of renaming:
```bash
ast-refactor rename src/ --from old_name --to new_name
```

#### Apply rename in-place (`-w` or `--write`):
```bash
ast-refactor rename src/ --from old_name --to new_name -w
```

#### Limit renaming to a specific function or class scope:
```bash
ast-refactor rename app.py --from x --to counter --scope process_data -w
```

#### Also rename matching object attributes and methods:
```bash
ast-refactor rename src/ --from calc --to compute --rename-attributes -w
```

---

### 2. Automated Function Extraction (`extract`)

Extract lines 15 to 25 of `service.py` into a new helper function named `calculate_tax`:

```bash
# Preview diff
ast-refactor extract service.py --lines 15-25 --name calculate_tax

# Apply in-place
ast-refactor extract service.py --lines 15-25 --name calculate_tax -w
```

#### What happens:
```python
# Before
def invoice(total, rate):
    tax = total * rate
    discount = 5.0
    final_amount = total + tax - discount
    return final_amount

# After: ast-refactor extract invoice.py --lines 2-4 --name calculate_total -w
def calculate_total(rate, total):
    tax = total * rate
    discount = 5.0
    final_amount = total + tax - discount
    return final_amount

def invoice(total, rate):
    final_amount = calculate_total(rate, total)
    return final_amount
```

---

### 3. Syntax Modernization (`modernize`)

#### Preview modernizations across your project:
```bash
ast-refactor modernize src/
```

#### Apply all modernizations in-place:
```bash
ast-refactor modernize src/ -w
```

#### Apply specific modernization rules:
```bash
ast-refactor modernize src/ --rules has_key,isinstance_tuple -w
```

---

## Command-Line Options Reference

| Command | Argument / Flag | Description |
|---------|-----------------|-------------|
| `rename` | `paths` | Files or directories to process |
| | `--from SYMBOL` | Symbol name to rename (required) |
| | `--to SYMBOL` | New symbol name (required) |
| | `--scope NAME` | Restrict rename to specific function/class |
| | `--rename-attributes` | Rename matching attribute accesses |
| | `-w`, `--write` | Write changes in-place to files |
| | `--check` | Exit 1 if matches are found (CI mode) |
| `extract` | `file` | Target source file (required) |
| | `--lines START-END`| Line numbers to extract (e.g. 10-25) |
| | `--name FUNC_NAME` | Name for newly created function |
| | `-w`, `--write` | Apply extraction to file |
| `modernize` | `paths` | Files or directories to modernize |
| | `--rules RULE,...` | Comma-separated rule names to run |
| | `-w`, `--write` | Apply modernizations to files |
| | `--check` | Exit 1 if modernizations are available |

---

## Running Tests

```bash
python -m unittest discover -s tests -v
```

---

## License

This project is licensed under the [MIT License](LICENSE).
