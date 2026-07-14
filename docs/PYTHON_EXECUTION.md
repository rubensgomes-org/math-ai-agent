# How Python Code Is Executed

## How a Computer Executes Code

A CPU only understands **machine code**: binary instructions (1s and 0s) specific to its architecture (x86, ARM, etc.). Assembly language is a human-readable representation of those binary instructions, and a program called an **assembler** converts assembly into machine code.

So the question becomes: how does a high-level language like Python eventually become 1s and 0s?

There are two broad strategies:

### 1. Compilation (e.g., C, Go, Rust)

The **entire** source code is translated **ahead of time** into machine code by a **compiler**. The result is a native binary executable that the CPU runs directly. The compilation pipeline typically looks like:

```
Source code → Compiler → Assembly → Assembler → Machine code (binary)
```

### 2. Interpretation (e.g., early BASIC, shell scripts)

An **interpreter** reads source code line by line (or statement by statement), parses it, and executes it immediately — the interpreter itself is a compiled program running on the CPU, and it decides what machine instructions to run based on what it reads.

### 3. Python's Hybrid Approach — Compilation + Interpretation

Python does **both**. This is where it gets interesting.

**Step 1 — Parsing and compilation to bytecode:**

When Python encounters your source file (e.g., `server.py`), the CPython interpreter:

1. **Lexing/Tokenizing** — Breaks the source text into tokens: keywords (`from`, `import`), identifiers (`Request`), operators, etc.
2. **Parsing** — Builds an **Abstract Syntax Tree (AST)** — a tree structure representing the grammatical structure of your code.
3. **Compiling** — Walks the AST and generates **bytecode** — a set of low-level instructions, but for a *virtual machine*, not the physical CPU.

This bytecode is what gets stored in `__pycache__/*.pyc` files. You can actually inspect it:

```python
import dis
dis.dis("from starlette.requests import Request")
```

Which produces something like:

```
  0 LOAD_CONST    0 (0)
  2 LOAD_CONST    1 (('Request',))
  4 IMPORT_NAME   0 (starlette.requests)
  6 IMPORT_FROM   1 (Request)
  8 STORE_NAME    1 (Request)
 10 POP_TOP
```

**Step 2 — Execution by the Python Virtual Machine (PVM):**

The **PVM** is a loop inside the CPython interpreter (written in C, compiled to machine code) that reads each bytecode instruction and executes it. This is often called a **bytecode interpreter** or **eval loop**. For each bytecode instruction, the PVM runs the corresponding C code, which ultimately results in real CPU instructions.

So the full chain is:

```
Python source (.py)
  → Lexer/Parser → AST
  → Compiler → Bytecode (.pyc)
  → PVM (C program, compiled to machine code) interprets bytecode
  → CPU executes the PVM's machine instructions
```

## What Happens When a Statement Is Executed

Taking an import as a concrete example:

```python
from starlette.requests import Request
```

When the PVM executes this bytecode:

1. **`IMPORT_NAME starlette.requests`** — The PVM calls Python's import machinery, which:
   - Checks `sys.modules` cache (already imported?)
   - If not cached, finds the module file on disk (`sys.path`)
   - Reads, parses, compiles, and executes that module's code (recursively)
   - Creates a module object and caches it in `sys.modules`

2. **`IMPORT_FROM Request`** — Looks up the name `Request` in the module object's namespace (its `__dict__`).

3. **`STORE_NAME Request`** — Binds the name `Request` in the current module's local namespace so you can use it.

Each of these bytecode operations triggers C functions inside CPython, which the OS runs as native machine code on your CPU.

## Why Not Just Compile Python to Machine Code?

A few reasons Python uses interpretation rather than ahead-of-time compilation:

- **Dynamic typing** — Python doesn't know the type of a variable until runtime, so it can't make the same optimizations a C compiler can.
- **Dynamic features** — `eval()`, `exec()`, `getattr()`, monkey-patching, metaclasses — these require a runtime that can interpret code on the fly.
- **Portability** — Bytecode runs on any platform that has a CPython interpreter, without recompilation.

That said, projects like **PyPy** (JIT compiler), **Cython** (compiles Python-like code to C), and **Nuitka** (compiles Python to C) do attempt to bridge this gap for performance-critical code.

## Summary

| Layer | What it does |
|---|---|
| **Python source** | Human-readable code |
| **Lexer/Parser** | Tokenizes and builds an AST |
| **Bytecode compiler** | Translates AST to bytecode |
| **PVM (interpreter)** | A C program that executes bytecode |
| **Machine code** | The compiled PVM running on the CPU |
| **CPU** | Executes binary 1s and 0s |

The CPU only processes bits. Python adds several layers of abstraction between your source code and those bits, with the CPython interpreter (a compiled C program) acting as the bridge.
