from __future__ import annotations
import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any

from codesage.analyzers.python_parser import PythonParser
from codesage.semantic_digest.base_builder import BaseLanguageSnapshotBuilder, SnapshotConfig
from codesage.snapshot.models import FileSnapshot

def calculate_complexity(node):
    complexity = 1
    nodes_to_walk = node if isinstance(node, (list, tuple)) else [node]

    def count_control_flow(n):
        nonlocal complexity
        if isinstance(n, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.With, ast.AsyncWith)):
            complexity += 1
        elif isinstance(n, ast.Try):
            complexity += len(n.handlers)
        elif isinstance(n, ast.BoolOp) and isinstance(n.op, (ast.And, ast.Or)):
            complexity += len(n.values) - 1
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in n.generators:
                complexity += len(generator.ifs)

    for root_node in nodes_to_walk:
        if root_node:
            for n in ast.walk(root_node):
                count_control_flow(n)
    return complexity

class PythonSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def __init__(self, root_path: Path, config: SnapshotConfig) -> None:
        super().__init__(root_path, config)
        self.parser = PythonParser()
        self.args = {
            'max_docstring_len': 200,
            'max_args_len': 5,
            'max_assign_len': 30,
            'ccn_threshold': 10,
            'code_sample_lines': 5,
        }

    def build(self) -> Dict[str, Any]:
        files = self._collect_files()
        digest = {
            "root": str(self.root_path),
            "type": "python",
            "files": [],
            "modules": defaultdict(lambda: {
                "f": [], "im": [], "fim": defaultdict(list), "cl": [], "fn": [], "md": {},
                "dc": set(), "ds": [], "cv": [], "cl_attr": [], "stat": {},
            }),
            "deps": defaultdict(set),
            "sum": {},
        }

        all_imports = set()
        total_ccn = 0

        for path in files:
            rel_path = str(path.relative_to(self.root_path))
            digest["files"].append(rel_path)

            semantics = self._extract_semantics(path)

            module_name = rel_path.replace(".py", "").replace("/", ".")
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]

            mod_entry = digest["modules"][module_name]
            mod_entry["f"].append(rel_path)
            mod_entry["im"].extend(semantics.get("im", []))
            mod_entry["cv"].extend(semantics.get("cv", []))
            mod_entry["cl_attr"].extend(semantics.get("cl_attr", []))

            for imp in semantics.get("im", []):
                all_imports.add(imp["n"])
            for module, items in semantics.get("fim", {}).items():
                mod_entry["fim"][module].extend(items)
                all_imports.add(module)

            mod_entry["cl"].extend(semantics.get("cl", []))
            mod_entry["fn"].extend(semantics.get("fn", []))
            for class_name, methods in semantics.get("md", {}).items():
                mod_entry["md"].setdefault(class_name, []).extend(methods)

            mod_entry["dc"].update(semantics.get("dc", []))
            mod_entry["ds"].extend(semantics.get("ds", []))
            mod_entry["stat"].update(semantics.get("stat", {}))

            total_ccn += sum(f.get("cx", 1) for f in semantics.get("fn", []))
            total_ccn += sum(m.get("cx", 1) for methods in semantics.get("md", {}).values() for m in methods)

            for imp in semantics.get("im", []):
                if not imp["n"].startswith(("sys", "os", "re")):
                    digest["deps"][module_name].add(imp["n"])
            for module, _ in semantics.get("fim", {}).items():
                if module and not module.startswith(("sys", "os", "re")):
                    digest["deps"][module_name].add(module)

        self._finalize_digest(digest, total_ccn, all_imports)

        # Convert defaultdicts to dicts for clean output
        final_modules = {}
        for name, data in digest["modules"].items():
            data["fim"] = dict(data["fim"])
            data["dc"] = sorted(list(data["dc"]))
            final_modules[name] = data
        digest["modules"] = final_modules
        digest["deps"] = {mod: sorted(list(deps)) for mod, deps in digest["deps"].items()}


        return digest

    def _collect_files(self) -> List[Path]:
        return [p for p in self.root_path.rglob("*.py") if not any(part.startswith('.') or part in ('__pycache__', 'venv') for part in p.parts)]

    def _extract_semantics(self, file_path: Path) -> Dict[str, Any]:
        try:
            source_code = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source_code)
            extractor = PythonSemanticExtractor(self.args)
            extractor.set_content_lines(source_code.splitlines())
            extractor.visit(tree)
            info = extractor.info
            info["stat"]["io"] = dict(info["stat"]["io"])
            return info
        except (SyntaxError, UnicodeDecodeError):
            return {}

    def _finalize_digest(self, digest: Dict[str, Any], total_ccn: int, all_imports: set) -> None:
        total_functions = 0
        has_async = False
        for module_name, data in digest["modules"].items():
            data["dc"] = sorted(list(data["dc"]))
            if data.get("stat", {}).get("async", 0) > 0:
                has_async = True
            all_cx = [f.get("cx", 1) for f in data["fn"]]
            all_cx.extend(m.get("cx", 1) for methods in data["md"].values() for m in methods)
            count_functions = len(data["fn"]) + sum(len(m) for m in data["md"].values())
            total_functions += count_functions
            avg_ccn = round(sum(all_cx) / max(count_functions, 1), 1)
            high_ccn_count = sum(1 for cx in all_cx if cx >= self.args['ccn_threshold'])

            summary_parts = []
            if data["cl"]: summary_parts.append(f"CLS:{len(data['cl'])}")
            if count_functions > 0:
                summary_parts.append(f"FN:{count_functions}")
                summary_parts.append(f"AVG_CX:{avg_ccn}")
                if high_ccn_count > 0: summary_parts.append(f"HIGH_CX:{high_ccn_count}")
            data["sm"] = "；".join(summary_parts) if summary_parts else "Python Module"
            data["fim"] = dict(data["fim"])

        digest["modules"] = dict(digest["modules"])
        digest["deps"] = {mod: sorted(list(deps)) for mod, deps in digest["deps"].items()}

        std_libs = {"os", "sys", "re", "json", "time", "logging"}
        project_pkgs = set(digest["modules"].keys())
        tech_stack = sorted(list((all_imports - std_libs) - project_pkgs))

        digest["sum"] = {
            "mod_count": len(digest["modules"]),
            "cl_count": sum(len(m["cl"]) for m in digest["modules"].values()),
            "fn_count": total_functions,
            "file_count": len(digest["files"]),
            "total_ccn": total_ccn,
            "tech_stack": tech_stack[:10],
            "config_files": [],
            "has_async": has_async,
            "uses_type_hints": False,
        }
        digest["root"] = str(self.root_path.resolve())


    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        # This method is not used in the new dictionary-based build process,
        # but it's required to satisfy the abstract base class.
        pass

class PythonSemanticExtractor(ast.NodeVisitor):
    def __init__(self, args):
        self.args = args
        self.info = {
            "im": [], "fim": defaultdict(list), "cl": [], "fn": [], "md": {}, "ds": [], "cv": [],
            "cl_attr": [], "dc": [], "th": [],
            "stat": {"async": 0, "th": 0, "io": defaultdict(int), "err": {"total": 0, "generic": 0}},
        }
        self.current_class = None
        self.content_lines = []

    def set_content_lines(self, lines):
        self.content_lines = lines

    def visit_Import(self, node):
        for alias in node.names:
            self.info["im"].append({"n": alias.name, "ln": node.lineno})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        items = [{"n": alias.name, "ln": node.lineno} for alias in node.names]
        self.info["fim"].setdefault(module, []).extend(items)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_info = {
            "n": node.name, "ln": node.lineno,
            "bs": [self._get_name(base) for base in node.bases],
            "dc": [self._get_name(dec) for dec in node.decorator_list], "attrs": []
        }
        for item in node.body:
            if isinstance(item, ast.Assign):
                value_repr = self._get_annotation(item.value, max_len=self.args['max_assign_len'])
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info["attrs"].append({"n": target.id, "ln": target.lineno, "val": value_repr})
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        self.info["cl"].append(class_info)
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def _process_function_or_method(self, node):
        ccn = calculate_complexity(node.body)
        args_list = [arg.arg for arg in node.args.args]
        if len(args_list) > self.args['max_args_len']:
            args_list = args_list[:self.args['max_args_len']] + ["..."]

        func_info = {
            "n": node.name, "ln": node.lineno, "cx": ccn, "args": args_list,
            "dc": [self._get_name(dec) for dec in node.decorator_list],
            "ret": self._get_annotation(node.returns),
            "async": isinstance(node, ast.AsyncFunctionDef),
        }

        if ccn >= self.args['ccn_threshold'] and self.content_lines:
            start_line = node.lineno
            end_line = getattr(node, 'end_lineno', start_line + 5)
            sample_end = min(end_line, start_line + self.args['code_sample_lines'])
            sample_lines = self.content_lines[start_line - 1 : sample_end]
            if sample_lines:
                indent = len(sample_lines[0]) - len(sample_lines[0].lstrip())
                func_info["sample"] = [line[indent:].rstrip() for line in sample_lines]

        if self.current_class:
            self.info["md"].setdefault(self.current_class, []).append(func_info)
        else:
            self.info["fn"].append(func_info)

    def visit_FunctionDef(self, node):
        self._process_function_or_method(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._process_function_or_method(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        if self.current_class is None:
            value_repr = self._get_annotation(node.value, max_len=self.args['max_assign_len'])
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    is_constant = name.isupper() and (name.replace('_', '').isalnum())
                    self.info["cv"].append({
                        "n": name, "ln": target.lineno, "const": is_constant, "val": value_repr,
                    })
        self.generic_visit(node)

    def _get_name(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute):
            base = self._get_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""

    def _get_annotation(self, node, max_len=50):
        if node is None: return None
        if hasattr(ast, "unparse"):
            try:
                rep = ast.unparse(node).strip()
                return rep[:max_len] + "..." if len(rep) > max_len else rep
            except Exception: pass
        return str(type(node).__name__)
