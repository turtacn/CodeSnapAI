# -*- coding: utf-8 -*-
"""
py-semantic-snapshot.py (V3.0)
Python 项目语义快照生成器 - 实现极致 Token 压缩与无损理解

主要功能更新 (V3.0):
1. 数据增强：记录常量/变量/类属性的初始值（截断），支持Docstring参数/返回信息提取。
2. 上下文追溯：记录内部 import 语句的行号。
3. 摘要量化：模块级摘要 (sm) 增加平均 CCN 和高 CCN 函数计数。
4. Token控制：新增 CLI 参数控制 Docstring 和参数列表的截断长度。
5. 采样功能：对高 CCN 函数进行代码片段采样 (sample)。

使用示例：
    python3.9 py-semantic-snapshot.py ./project -o digest.yaml --max-doc-len 100 --ccn-threshold 10
"""

from __future__ import unicode_literals
import os
import ast
import re
import subprocess
import sys
import argparse
from collections import defaultdict

try:
    import yaml  # 需要: pip install PyYAML
    import networkx as nx # 需要: pip install networkx
    import matplotlib
    import matplotlib.pyplot as plt # 需要: pip install matplotlib
    
    # 兼容服务器 / 无显示环境
    matplotlib.use("Agg")
    CAN_GRAPH = True
except ImportError:
    print("⚠️ 缺少依赖: PyYAML, networkx, 或 matplotlib。图表功能将跳过。")
    CAN_GRAPH = False


# --- 配置与工具函数 ---
if sys.version_info[0] == 2:
    text_type = unicode
    string_types = (str, unicode)
else:
    text_type = str
    string_types = (str,)

def ensure_unicode(s):
    if isinstance(s, text_type):
        return s
    if isinstance(s, bytes):
        return s.decode("utf-8", errors="ignore")
    return text_type(s)

def get_gitignored_files(repo_path):
    try:
        ignored = subprocess.check_output(
            ["git", "ls-files", "--others", "-i", "--exclude-standard"],
            cwd=repo_path,
        ).decode("utf-8", errors="ignore").splitlines()
        return set(ignored)
    except Exception:
        return set()
    
# --- 复杂度计算辅助函数 ---

def calculate_complexity(node):
    """
    计算简化版的 McCabe 圈复杂度 (CCN)。
    修订：CCN 从 1 开始，并确保能够处理函数体（一个 AST 节点列表）。
    """
    complexity = 1  # 默认复杂度为 1 (函数定义本身)
    
    # AST 节点或节点列表
    nodes_to_walk = node if isinstance(node, (list, tuple)) else [node]
    
    def count_control_flow(n):
        nonlocal complexity
        
        if isinstance(n, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.With, ast.AsyncWith)):
            complexity += 1
        elif isinstance(n, ast.Try):
            # 基础 Try (1) + 每个 Except/Else/Finally 块的附加路径 (这里只算每个 except 处理器)
            complexity += len(n.handlers)
        elif isinstance(n, ast.BoolOp):
            if isinstance(n.op, (ast.And, ast.Or)):
                complexity += len(n.values) - 1
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in n.generators:
                complexity += len(generator.ifs)

    # 遍历所有节点，如果是列表，则遍历列表中的每个根节点
    for root_node in nodes_to_walk:
        if root_node:
            # 正确使用 ast.walk: 遍历节点及其所有子节点
            # 注意: 如果传入的是函数体列表，我们已经在外层 for 循环处理了列表本身
            # 此时 root_node 就是列表中的一个语句节点
            for n in ast.walk(root_node):
                count_control_flow(n) # 对遍历到的每个节点调用计数函数
    
    # 原始代码在 _process_function_or_method 中传入的是 node.body (list)，
    # 因此函数体列表中的节点都需要被遍历。
    # 经过上述修改，如果传入的是列表，我们将遍历列表中的每个元素。
    
    return complexity

# --- AST 语义提取器 (V3.0) ---

IO_CALLS = {
    "open": "File_IO", "read": "File_IO", "write": "File_IO",
    "requests.get": "Network_HTTP", "requests.post": "Network_HTTP",
    "socket.socket": "Network_Socket", 
    "db.connect": "Database_Op", "cursor.execute": "Database_Op",
    "subprocess.run": "IPC_Process", "os.popen": "IPC_Process",
}

class PythonSemanticExtractor(ast.NodeVisitor):
    """使用 AST 提取 Python 代码语义结构 (V3.0, 短键名)"""

    def __init__(self, args):
        self.args = args  # 接收 CLI 参数
        self.info = {
            "im": [],              # imports (带行号)
            "fim": {},             # from_imports: {module: [items]} (带行号)
            "cl": [],              # classes
            "fn": [],              # functions 
            "md": {},              # methods
            "ds": [],              # docstrings (sampled)
            "cv": [],              # constants/vars (带值和类型)
            "cl_attr": [],         # class attributes (新增)
            "dc": [],              # decorators (模块级)
            "th": [],              # type hints (模块级)
            "stat": {
                "async": 0,           
                "th": 0,              
                "io": defaultdict(int),   
                "err": {"total": 0, "generic": 0},  
            },
        }
        self.current_class = None
        # 存储文件内容行，用于代码片段采样 (需求6)
        self.content_lines = [] 
        
    def set_content_lines(self, lines):
        self.content_lines = lines

    # --- Import (新增行号追踪 - 需求2) ---

    def visit_Import(self, node):
        for alias in node.names:
            # 记录 import 语句的行号
            self.info["im"].append({"n": alias.name, "ln": node.lineno})
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        # 记录 import 语句的行号
        items = [{"n": alias.name, "ln": node.lineno} for alias in node.names]
        self.info["fim"].setdefault(module, []).extend(items)
        self.generic_visit(node)

    # --- Class (新增类属性提取 - 需求3a) ---

    def visit_ClassDef(self, node):
        class_info = {
            "n": node.name,
            "ln": node.lineno, 
            "bs": [self._get_name(base) for base in node.bases], 
            "dc": [self._get_name(dec) for dec in node.decorator_list], 
            "attrs": [] # 类属性列表
        }
        
        # Docstring 采样
        docstring = ast.get_docstring(node)
        if docstring and len(docstring) > 10:
            doc_len = min(len(docstring), self.args.max_docstring_len)
            self.info["ds"].append({"t": "cl", "n": node.name, "doc": docstring[:doc_len] + ("..." if doc_len < len(docstring) else "")})

        # 遍历类体，提取类属性（Assignment 在方法定义前出现）
        for item in node.body:
            if isinstance(item, ast.Assign):
                # Class attributes (V3.0)
                value_repr = self._get_annotation(item.value, max_len=self.args.max_assign_len)
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        is_constant = name.isupper() and (name.replace('_', '').isalnum())
                        class_info["attrs"].append({
                            "n": name, 
                            "ln": target.lineno,
                            "const": is_constant,
                            "val": value_repr, 
                        })
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 遇到函数/方法后，停止查找类属性
                break 

        self.info["cl"].append(class_info)

        # 进入类上下文
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    # --- Function/Method (新增 Docstring 参数解析/Arg截断/代码采样 - 需求3b/4/6) ---

    def _parse_docstring_params(self, docstring):
        """简单启发式解析 Docstring 中的参数和返回值 (需求3b)"""
        if not docstring: return None
        
        parsed = {}
        # 匹配 Google/Sphinx 风格的参数和返回
        param_matches = re.findall(r"^\s*(?:Args|Parameters|:param)\s*:\s*(\w+)\s*(?:(?:[ \t]|\([\w,]+\))?:?\s*(.*))?", docstring, re.MULTILINE | re.IGNORECASE)
        return_matches = re.findall(r"^\s*(?:Returns|:returns:)\s*:\s*(.*)", docstring, re.MULTILINE | re.IGNORECASE)

        if param_matches:
            parsed["p"] = [f"{n}: {d.strip()}" for n, d in param_matches if n]
        if return_matches:
            parsed["r"] = [r.strip() for r in return_matches]
        
        return parsed if parsed else None


    def _process_function_or_method(self, node):
        # 传入 node.body 以计算 CCN (因为 CCN = 1 已经在 calculate_complexity 中计算)
        ccn = calculate_complexity(node.body)
        
        # 参数截断 (需求4)
        args_list = [arg.arg for arg in node.args.args]
        if len(args_list) > self.args.max_args_len:
            args_list = args_list[:self.args.max_args_len] + ["..."]

        func_info = {
            "n": node.name,
            "ln": node.lineno,
            "cx": ccn, 
            "args": args_list,
            "dc": [self._get_name(dec) for dec in node.decorator_list],
            "ret": self._get_annotation(node.returns),
            "async": isinstance(node, ast.AsyncFunctionDef),
        }

        if func_info["async"]: self.info["stat"]["async"] += 1
        
        # 代码片段采样 (需求6)
        if ccn >= self.args.ccn_threshold and self.content_lines:
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 5
            
            # 采样 N 行
            sample_end = min(end_line, start_line + self.args.code_sample_lines)
            # AST行号是1-based，列表是0-based。我们想要包含 node.lineno 行，所以从 node.lineno - 1 开始
            # 但是为了获取函数体的行，我们从 start_line 开始（即定义行）
            sample_lines = self.content_lines[start_line - 1 : sample_end]
            
            # 移除公共缩进
            if sample_lines:
                try:
                    # 找到定义行的缩进（第一行）
                    indent = len(sample_lines[0]) - len(sample_lines[0].lstrip())
                    # 对后续行应用相同的缩进移除
                    func_info["sample"] = [line[indent:].rstrip() for line in sample_lines]
                except IndexError:
                    pass # 无法获取缩进

        # Docstring 采样与解析 (需求3b, 4)
        docstring = ast.get_docstring(node)
        if docstring and len(docstring) > 10:
            params_from_doc = self._parse_docstring_params(docstring)
            doc_len = min(len(docstring), self.args.max_docstring_len)

            doc_entry = {
                "t": "md" if self.current_class else "fn",
                "n": node.name, 
                "doc": docstring[:doc_len] + ("..." if doc_len < len(docstring) else "")
            }
            if params_from_doc:
                doc_entry["doc_p"] = params_from_doc
            self.info["ds"].append(doc_entry)

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

    # --- Assign (新增常量/变量信息 - 需求1) ---

    def visit_Assign(self, node):
        # 如果在 ClassDef 外 (模块级变量/常量)
        if self.current_class is None:
            value_repr = self._get_annotation(node.value, max_len=self.args.max_assign_len) 
            
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    is_constant = name.isupper() and (name.replace('_', '').isalnum()) # 启发式判断
                    
                    self.info["cv"].append({
                        "n": name, 
                        "ln": target.lineno,
                        "const": is_constant,
                        "val": value_repr, 
                    })
        
        # 注意: 类属性的提取已移至 visit_ClassDef 中，以避免在方法内赋值也被误判为类属性。
        self.generic_visit(node)
        
    # --- 深度分析：I/O, IPC, Error Handling (V2.0 保留) ---
    
    def visit_Call(self, node):
        call_name = self._get_name(node.func)
        for keyword, category in IO_CALLS.items():
            if keyword in call_name:
                self.info["stat"]["io"][category] += 1
        self.generic_visit(node)
        
    def visit_Try(self, node):
        self.info["stat"]["err"]["total"] += 1
        for handler in node.handlers:
            if handler.type is None or self._get_name(handler.type) in ["Exception", "BaseException"]:
                self.info["stat"]["err"]["generic"] += 1
                if "generic_excepts" not in self.info["stat"]["err"]:
                     self.info["stat"]["err"]["generic_excepts"] = []
                self.info["stat"]["err"]["generic_excepts"].append(handler.lineno)
        self.generic_visit(node)

    # --- 辅助方法 (V3.0 优化 `_get_annotation` 的值捕获) ---

    def _get_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_name(node.value)
            return "{}.{}".format(base, node.attr) if base else node.attr
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""

    def _get_annotation(self, node, max_len=50):
        if node is None:
            return None
        
        # 尝试使用 ast.unparse (Python 3.9+) 获取表达式的字符串表示
        if hasattr(ast, "unparse"):
            try:
                representation = ast.unparse(node).strip()
                if len(representation) > max_len:
                    return representation[:max_len] + "..."
                return representation
            except Exception:
                # Fallback to type names if unparse fails
                pass 

        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            # 捕获字面量类型和值
            val = text_type(node.value)
            type_name = type(node.value).__name__
            # 限制 val 的长度以避免超长 token
            if len(val) > max_len:
                val = val[:max_len] + "..."
            return f"{type_name}({val})"
        if isinstance(node, ast.Subscript):
            value_name = self._get_name(node.value)
            return "{}[...]".format(value_name or "Subscript")
        
        return text_type(node)


# --- 解析入口函数 (适配 V3.0) ---

def extract_python_semantics(filepath, args):
    """对单个 Python 文件做 AST 语义提取 (V3.0)"""
    info = {
        "im": [], "fim": {}, "cl": [], "fn": [], "md": {}, "ds": [], "cv": [], "dc": [], "th": [], "cl_attr": [],
        "stat": {"async": 0, "th": 0, "io": {}, "err": {"total": 0, "generic": 0}},
    }
    content = ""
    content_lines = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        content = ensure_unicode(content)
        # 用于代码采样，保留换行符
        content_lines = content.splitlines(keepends=True) 
        # AST 行号是 1-based，但 for 循环中获取 start_line: sample_end 已经调整，这里用 splitlines() 不保留换行，方便处理缩进
        content_lines = content.splitlines() 
    except Exception:
        return info

    try:
        # Python 3.8+ 支持 end_lineno 和 end_col_offset
        tree = ast.parse(content)
        extractor = PythonSemanticExtractor(args)
        extractor.set_content_lines(content_lines)
        extractor.visit(tree)
        info.update(extractor.info)
        info["stat"]["io"] = dict(info["stat"]["io"])
    except SyntaxError:
        # AST 解析失败时，回退到正则
        print(f"⚠️ 语法错误，文件 {filepath} 使用正则兜底。")
        return extract_python_semantics_fallback(content)
    except Exception as e:
        print(f"❌ 严重错误：解析 {filepath} 失败：{e}。使用正则兜底。")
        return extract_python_semantics_fallback(content)

    return info


def extract_python_semantics_fallback(content):
    """AST 解析失败时的兜底：基于正则的粗粒度提取"""
    # ... (V2.0 逻辑保持不变, 无法提供 V3.0 深度信息) ...
    info = {
        "im": [], "fim": {}, "cl": [], "fn": [], "md": {}, "ds": [], "cv": [], "dc": [], "th": [], "cl_attr": [],
        "stat": {"async": 0, "th": 0, "io": {}, "err": {"total": 0, "generic": 0}},
    }

    # 正则提取: 仅提取名称和参数 (无 CCN/ln/val/sample)
    # 这里我们尝试模拟行号，但只能是粗略的近似
    content_lines = content.splitlines()
    
    # Imports
    for i, line in enumerate(content_lines):
        match_import = re.match(r"^\s*import\s+([\w\.]+)", line)
        if match_import:
            info["im"].append({"n": match_import.group(1), "ln": i + 1})
        
        match_from_import = re.match(r"^\s*from\s+([\w\.]+)\s+import\s+(.+)", line)
        if match_from_import:
            module, items_str = match_from_import.groups()
            items_list = [{"n": item.strip(), "ln": i + 1} for item in items_str.split(",")]
            info["fim"].setdefault(module, []).extend(items_list)

    # Classes and Functions (需要更复杂的正则来获取准确的行号和参数)
    for i, line in enumerate(content_lines):
        match_class = re.match(r"^\s*class\s+(\w+)(?:\(([^)]*)\))?:", line)
        if match_class:
            name, bases = match_class.groups()
            info["cl"].append({"n": name, "ln": i + 1, "bs": [b.strip() for b in bases.split(",")] if bases else [], "attrs": []})
        
        match_func = re.match(r"^\s*(async\s+)?def\s+(\w+)\s*\(([^)]*)\)", line)
        if match_func:
            is_async, name, args_str = match_func.groups()
            args = [a.strip() for a in args_str.split(",")] if args_str else []
            func_info = {"n": name, "ln": i + 1, "cx": 1, "args": args, "async": bool(is_async)}
            info["fn"].append(func_info)
            if is_async: info["stat"]["async"] += 1
            
    # 清理 fn/cl 列表中的重复项（正则可能在多行匹配中出错，虽然这里是单行匹配）
    # 由于是兜底，我们接受其粗糙性。
    
    return info


# --- 依赖图绘制 (保留 V2.0 逻辑) ---

def generate_dependency_graph(import_graph, output_path_base):
    # ... (V2.0 逻辑保持不变) ...
    if not CAN_GRAPH:
        return

    G = nx.DiGraph()

    for module, deps in import_graph.items():
        if not deps:
            G.add_node(module)
        for dep in deps:
            G.add_edge(module, dep)

    if len(G.nodes) == 0:
        print("ℹ️  依赖图为空，跳过生成。")
        return

    try:
        k = 1.0 / max(len(G.nodes), 1) ** 0.5
        pos = nx.spring_layout(G, k=k, iterations=80)
    except Exception:
        pos = nx.spring_layout(G)

    base_size = max(8, min(20, len(G.nodes) * 0.4))
    plt.figure(figsize=(base_size, base_size * 0.75))

    nx.draw_networkx_nodes(G, pos, node_size=800)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle="-|>", arrowsize=12)
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.axis("off")
    png_path = output_path_base + ".png"
    svg_path = output_path_base + ".svg"

    try:
        plt.tight_layout()
        plt.savefig(png_path, dpi=150)
        plt.savefig(svg_path, dpi=150)
        plt.close()
        print("✅ Dependency graph generated: {}, {}".format(png_path, svg_path))
    except Exception as e:
        print("⚠️  依赖图保存失败: {}".format(ensure_unicode(str(e))))
        plt.close()


# --- 项目遍历 & 摘要生成 (V3.0) ---

CONFIG_FILES = [
    "requirements.txt", "setup.py", "pyproject.toml",
    "Pipfile", "poetry.lock", "tox.ini",
]

def rglob_py_files(root_path):
    # ... (V2.0 逻辑保持不变) ...
    py_files = []
    root_path = ensure_unicode(root_path)
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirpath = ensure_unicode(dirpath)
        dirnames[:] = [
            ensure_unicode(d) for d in dirnames
            if not ensure_unicode(d).startswith(".") and d not in ["__pycache__", "venv", "env", ".venv", "node_modules", "build", "dist", ".tox"]
        ]
        for filename in filenames:
            filename = ensure_unicode(filename)
            if filename.endswith(".py") and not filename.startswith("."):
                py_files.append(os.path.join(dirpath, filename))
    return py_files


def generate_semantic_digest(repo_path, output_path, args):
    """生成 Python 项目的语义摘要（V3.0）"""
    repo_path = ensure_unicode(os.path.abspath(repo_path))
    ignored = get_gitignored_files(repo_path)

    digest = {
        "root": repo_path,
        "type": "python",
        "files": [],                       
        "modules": defaultdict(
            lambda: {
                "f": [],                    
                "im": [],                   # list of dicts (name, ln)
                "fim": defaultdict(list),   # dict of lists (name, ln)
                "cl": [],                   
                "fn": [],                   
                "md": {},                   
                "dc": set(),                
                "ds": [],                   
                "cv": [],                   # module vars/consts
                "cl_attr": [],              # class attributes
                "stat": {},                 
            }
        ),
        "deps": defaultdict(set),           
        "sum": {},                          
    }
    
    found_config_files = [f for f in CONFIG_FILES if os.path.exists(os.path.join(repo_path, f))]
    all_imports = set()
    total_ccn = 0
    
    for path in rglob_py_files(repo_path):
        path = ensure_unicode(path)
        rel_path = ensure_unicode(os.path.relpath(path, repo_path))

        if any(skip in rel_path for skip in ["test_", "_test.py", "/tests/", "/venv/", "/env/", "/.venv/", "/build/", "/dist/", "/__pycache__/", "/site-packages/"]):
            continue
        if rel_path in ignored:
            continue

        semantics = extract_python_semantics(path, args) # 传入 args

        module_parts = rel_path.replace(".py", "").replace(os.sep, ".").split(".")
        if module_parts and module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        module_name = ".".join(module_parts) if module_parts else "root"

        mod_entry = digest["modules"][module_name]
        mod_entry["f"].append(rel_path)
        digest["files"].append(rel_path)

        # 聚合结构
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
        
        # 累加 CCN
        total_ccn += sum(f.get("cx", 1) for f in semantics.get("fn", []))
        total_ccn += sum(m.get("cx", 1) for methods in semantics.get("md", {}).values() for m in methods)

        # 构建依赖图 (使用导入名，不使用行号)
        for imp in semantics.get("im", []):
            # 过滤掉常见的标准库（它们通常不构成项目内部依赖图）
            if not imp["n"].startswith(("sys", "os", "re", "json", "time", "datetime", "logging", "collections", "io", "abc", "math", "random", "unittest", "zipfile")):
                digest["deps"][module_name].add(imp["n"])
        for module, _items in semantics.get("fim", {}).items():
            if module and not module.startswith(("sys", "os", "re", "json", "time", "datetime", "logging", "collections", "io", "abc", "math", "random", "unittest", "zipfile")):
                digest["deps"][module_name].add(module)


    # --- 收尾：清理、聚合、生成项目总结 (V3.0) ---

    total_functions = 0
    total_mod_ccn = 0
    
    # 1. 模块级清理和总结
    for module_name, data in digest["modules"].items():
        data["im"] = sorted(data["im"], key=lambda x: x["n"])
        data["dc"] = sorted(list(data["dc"]))

        # 精简 docstrings
        unique_docs = []
        seen = set()
        for doc in data["ds"]:
            key = (doc.get("t"), doc.get("n"))
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)
        data["ds"] = unique_docs[:5]

        # CCN Metrics (用于 sm 摘要 - 需求5)
        all_cx = [f.get("cx", 1) for f in data["fn"]]
        all_cx.extend(m.get("cx", 1) for methods in data["md"].values() for m in methods)
        
        count_functions = len(data["fn"]) + sum(len(m) for m in data["md"].values())
        total_functions += count_functions
        
        total_module_ccn = sum(all_cx)
        total_mod_ccn += total_module_ccn
        
        avg_ccn = round(total_module_ccn / max(count_functions, 1), 1)
        high_ccn_count = sum(1 for cx in all_cx if cx >= args.ccn_threshold)

        # 模块级简短 summary (sm) - V3.0
        summary_parts = []
        if data["cl"]: summary_parts.append("CLS:{}".format(len(data["cl"])))
        if count_functions > 0: 
            summary_parts.append("FN:{}".format(count_functions))
            summary_parts.append("AVG_CX:{}".format(avg_ccn)) # 需求5
            if high_ccn_count > 0:
                 summary_parts.append("HIGH_CX:{}".format(high_ccn_count)) # 需求5
        if data["stat"].get("async"): summary_parts.append("ASYNC")
        if data["stat"].get("th"): summary_parts.append("TH")
        if any(v > 0 for v in data["stat"].get("io", {}).values()): summary_parts.append("IO/IPC")
        if data["stat"].get("err", {}).get("generic") > 0: summary_parts.append("GenericErr:{}".format(data["stat"]["err"]["generic"]))

        data["sm"] = "；".join(summary_parts) if summary_parts else "Python Module"

    digest["modules"] = dict(digest["modules"])

    # 2. 依赖图 dict 化
    dep_graph_dict = {}
    for mod, deps in digest["deps"].items():
        dep_graph_dict[mod] = sorted(list(deps))
    digest["deps"] = dep_graph_dict

    # 3. 项目级 summary (sum)
    total_modules = len(digest["modules"])
    total_classes = sum(len(m["cl"]) for m in digest["modules"].values())

    std_libs = {"os", "sys", "re", "json", "time", "logging", "datetime", "abc", "collections", "io", "math", "random", "unittest", "zipfile"}
    project_pkgs = set(digest["modules"].keys())
    # 筛选出非标准库且非项目内部模块的导入，作为技术栈
    tech_stack = sorted(list((all_imports - std_libs) - project_pkgs))

    digest["sum"] = {
        "mod_count": total_modules,
        "cl_count": total_classes,
        "fn_count": total_functions,
        "file_count": len(digest["files"]),
        "total_ccn": total_mod_ccn,
        "config_files": found_config_files, 
        "tech_stack": tech_stack[:10], 
        "has_async": any(m.get("stat", {}).get("async") > 0 for m in digest["modules"].values()),
        # 注意: 无法准确统计 type hints，保持原字段但依赖 AST 结构 (这里简单保持 V2.0 逻辑)
        "uses_type_hints": False, 
    }

    output_path = ensure_unicode(output_path)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml_content = yaml.dump(
                digest,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120,
            )
            f.write(yaml_content)

        print("✅ Semantic project digest generated: {}".format(output_path))
        print(
            "   📊 Stats (V3.0): {} modules, {} classes, {} functions, Total CCN: {}".format(
                total_modules, total_classes, total_functions, total_mod_ccn
            )
        )

        try:
            graph_base = output_path.replace(".yaml", "_dependency_graph")
            generate_dependency_graph(digest["deps"], graph_base)
        except Exception as e:
            print("⚠️  生成依赖图时出错: {}".format(ensure_unicode(str(e))))
            
    except Exception as e:
        print("❌ 写入输出文件时发生错误: {}".format(ensure_unicode(str(e))))


# --- CLI 入口 (V3.0 新增参数) ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "生成 Python 项目的语义摘要（YAML）和依赖关系图（PNG/SVG），"
            "用于大模型理解项目结构 & 大幅减少 token (V3.0)."
        ),
        epilog=(
            "示例:\n"
            "  python3.9 py-semantic-snapshot.py ./project -o digest.yaml --max-doc-len 100 --ccn-threshold 10"
        ),
    )
    parser.add_argument("repo_path", help="本地 Python 项目路径")
    parser.add_argument(
        "-o",
        "--output",
        default="python_semantic_digest.yaml",
        help="输出 YAML 文件路径",
    )
    # V3.0 新增 Token 控制和采样参数 (需求4, 6)
    parser.add_argument(
        "--max-doc-len",
        type=int,
        default=200,
        dest="max_docstring_len",
        help="Docstring 采样最大长度 (Token 优化).",
    )
    parser.add_argument(
        "--max-args-len",
        type=int,
        default=5,
        dest="max_args_len",
        help="函数参数列表最大数量，超出则截断 (Token 优化).",
    )
    parser.add_argument(
        "--max-assign-len",
        type=int,
        default=30,
        dest="max_assign_len",
        help="常量/变量/属性初始值表达式的最大长度 (Token 优化).",
    )
    parser.add_argument(
        "--ccn-threshold",
        type=int,
        default=10,
        dest="ccn_threshold",
        help="CCN 阈值。高于此值的函数，其代码片段将被采样 (需求6) 并在摘要中标记 (需求5).",
    )
    parser.add_argument(
        "--code-sample-lines",
        type=int,
        default=5,
        dest="code_sample_lines",
        help="高 CCN 函数的代码采样行数 (需求6).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.repo_path):
        print("❌ Error: Path '{}' does not exist".format(args.repo_path))
        sys.exit(1)

    generate_semantic_digest(args.repo_path, args.output, args)
