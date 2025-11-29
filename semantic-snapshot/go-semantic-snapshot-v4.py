# -*- coding: utf-8 -*-
"""
go-semantic-snapshot.py
Go 项目语义快照生成器 (v2.0) - 混合策略 (AST + Regex) & 极致 Token 压缩

主要特性：
1. 混合解析策略：优先调用系统 `go` 命令进行 AST 精确解析，失败自动回退到 Regex。
2. 深度语义分析：包含循环复杂度(CCN)、错误处理热点、并发模式(Goroutine/Channel)、泛型支持。
3. 极致 Token 压缩：使用缩写键名 (n, p, r, cx...)，结构紧凑，专为 LLM Context Window 优化。

使用示例：
    python go-semantic-snapshot.py ./my-go-project
    python go-semantic-snapshot.py ./my-go-project -o digest.yaml --graph
"""

from __future__ import unicode_literals, print_function
import os
import re
import sys
import subprocess
import json
import tempfile
import shutil
from collections import defaultdict

try:
    import yaml  # pip install PyYAML
except ImportError:
    print("Error: PyYAML not installed. Please run: pip install PyYAML")
    sys.exit(1)

# Python 2/3 compatibility
if sys.version_info[0] == 2:
    text_type = unicode  # noqa: F821
else:
    text_type = str

# ---------------------------------------------------------
# 嵌入式 Go AST 解析器源码 (用于精确分析)
# ---------------------------------------------------------
GO_AST_PARSER_SRC = r"""
package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strings"
)

// 压缩键名结构定义
type Node struct {
	Name       string      `json:"n,omitempty"`  // Name
	Type       string      `json:"t,omitempty"`  // Type / Signature
	Params     string      `json:"p,omitempty"`  // Params
	Returns    string      `json:"r,omitempty"`  // Returns
	Receiver   string      `json:"rc,omitempty"` // Receiver
	Fields     []*Node     `json:"fd,omitempty"` // Fields
	Methods    []*Node     `json:"md,omitempty"` // Interface Methods
	Complexity int         `json:"cx,omitempty"` // Cyclomatic Complexity
	IsGeneric  bool        `json:"gn,omitempty"` // Uses Generics
}

type FileSummary struct {
	Package   string             `json:"pk"`
	Imports   []string           `json:"im,omitempty"`
	Structs   []*Node            `json:"st,omitempty"`
	Ifaces    []*Node            `json:"if,omitempty"`
	Funcs     []*Node            `json:"fn,omitempty"`
	Methods   map[string][]*Node `json:"md,omitempty"` // Key: Receiver Type
	Vars      []string           `json:"vr,omitempty"`
	Consts    []string           `json:"cn,omitempty"`
	Comments  []string           `json:"cm,omitempty"` // Sampled comments
	Stats     FileStats          `json:"stat"`
}

type FileStats struct {
	Goroutines int `json:"gr,omitempty"` // count of 'go func'
	Channels   int `json:"ch,omitempty"` // count of channel ops
	Errors     int `json:"er,omitempty"` // count of 'if err != nil'
}

func main() {
	if len(os.Args) < 2 {
		os.Exit(1)
	}
	fset := token.NewFileSet()
	node, err := parser.ParseFile(fset, os.Args[1], nil, parser.ParseComments)
	if err != nil {
		os.Exit(1)
	}

	summary := FileSummary{
		Package: node.Name.Name,
		Methods: make(map[string][]*Node),
	}

	// 提取 Imports
	for _, imp := range node.Imports {
		path := strings.Trim(imp.Path.Value, "\"")
		summary.Imports = append(summary.Imports, path)
	}

	// 访问 AST
	ast.Inspect(node, func(n ast.Node) bool {
		switch x := n.(type) {
		
		// 统计并发与错误处理
		case *ast.GoStmt:
			summary.Stats.Goroutines++
		case *ast.SendStmt:
			summary.Stats.Channels++
		case *ast.IfStmt:
			// 简单的 heuristic 检测 if err != nil
			if binExpr, ok := x.Cond.(*ast.BinaryExpr); ok {
				if x, ok := binExpr.X.(*ast.Ident); ok && x.Name == "err" {
					summary.Stats.Errors++
				}
			}

		case *ast.FuncDecl:
			fnNode := &Node{
				Name:       x.Name.Name,
				Complexity: calcComplexity(x.Body),
				IsGeneric:  x.Type.TypeParams != nil,
			}
			// 参数与返回值签名
			fnNode.Params, fnNode.Returns = extractSig(x.Type)

			if x.Recv == nil {
				summary.Funcs = append(summary.Funcs, fnNode)
			} else {
				// 方法
				recvType := formatType(x.Recv.List[0].Type)
				// 清理指针符号以便分组
				rawRecv := strings.TrimLeft(recvType, "*")
				fnNode.Receiver = recvType
				summary.Methods[rawRecv] = append(summary.Methods[rawRecv], fnNode)
			}

		case *ast.GenDecl:
			if x.Tok == token.TYPE {
				for _, spec := range x.Specs {
					typeSpec := spec.(*ast.TypeSpec)
					tNode := &Node{Name: typeSpec.Name.Name}
					
					// 泛型检测
					if typeSpec.TypeParams != nil {
						tNode.IsGeneric = true
					}

					switch t := typeSpec.Type.(type) {
					case *ast.StructType:
						// 提取 Struct 字段 (限制前10个)
						count := 0
						for _, field := range t.Fields.List {
							if count > 10 { break }
							typeStr := formatType(field.Type)
							if len(field.Names) == 0 {
								// 嵌入字段
								tNode.Fields = append(tNode.Fields, &Node{Type: typeStr})
							} else {
								for _, name := range field.Names {
									tNode.Fields = append(tNode.Fields, &Node{Name: name.Name, Type: typeStr})
								}
							}
							count++
						}
						summary.Structs = append(summary.Structs, tNode)

					case *ast.InterfaceType:
						// 提取 Interface 方法
						for _, method := range t.Methods.List {
							if len(method.Names) > 0 {
								p, r := extractSig(method.Type.(*ast.FuncType))
								tNode.Methods = append(tNode.Methods, &Node{
									Name: method.Names[0].Name, 
									Params: p, 
									Returns: r,
								})
							}
						}
						summary.Ifaces = append(summary.Ifaces, tNode)
					}
				}
			} else if x.Tok == token.VAR {
				for _, spec := range x.Specs {
					vSpec := spec.(*ast.ValueSpec)
					for _, name := range vSpec.Names {
						summary.Vars = append(summary.Vars, name.Name)
					}
				}
			} else if x.Tok == token.CONST {
				for _, spec := range x.Specs {
					cSpec := spec.(*ast.ValueSpec)
					for _, name := range cSpec.Names {
						summary.Consts = append(summary.Consts, name.Name)
					}
				}
			}
		}
		return true
	})
	
	// 通道类型检测补充
	ast.Inspect(node, func(n ast.Node) bool {
		if t, ok := n.(*ast.ChanType); ok {
			_ = t
			summary.Stats.Channels++ // Count definition of channels too
		}
		return true
	})

	// 注释采样 (取 doc)
	if len(node.Comments) > 0 {
		for i, cg := range node.Comments {
			if i >= 5 { break } // limit
			txt := strings.TrimSpace(cg.Text())
			if len(txt) > 5 && !strings.HasPrefix(txt, "TODO") {
				if len(txt) > 100 { txt = txt[:100] + "..." }
				summary.Comments = append(summary.Comments, txt)
			}
		}
	}

	b, _ := json.Marshal(summary)
	fmt.Println(string(b))
}

// 简单的复杂度计算 (McCabe 简化版)
func calcComplexity(body *ast.BlockStmt) int {
	count := 1
	if body == nil { return count }
	ast.Inspect(body, func(n ast.Node) bool {
		switch n.(type) {
		case *ast.IfStmt, *ast.ForStmt, *ast.RangeStmt, *ast.CaseClause:
			count++
		case *ast.BinaryExpr:
			// 统计 && 和 ||
			be := n.(*ast.BinaryExpr)
			if be.Op == token.LAND || be.Op == token.LOR {
				count++
			}
		}
		return true
	})
	return count
}

// 提取函数签名
func extractSig(t *ast.FuncType) (params, returns string) {
	ps := []string{}
	if t.Params != nil {
		for _, f := range t.Params.List {
			typeStr := formatType(f.Type)
			if len(f.Names) == 0 {
				ps = append(ps, typeStr)
			} else {
				for range f.Names {
					ps = append(ps, typeStr) // 简化：只存类型，省 token
				}
			}
		}
	}
	rs := []string{}
	if t.Results != nil {
		for _, f := range t.Results.List {
			rs = append(rs, formatType(f.Type))
		}
	}
	return strings.Join(ps, ","), strings.Join(rs, ",")
}

// 极简类型格式化
func formatType(expr ast.Expr) string {
	switch t := expr.(type) {
	case *ast.Ident: return t.Name
	case *ast.StarExpr: return "*" + formatType(t.X)
	case *ast.SelectorExpr: return formatType(t.X) + "." + t.Sel.Name
	case *ast.ArrayType: return "[]" + formatType(t.Elt)
	case *ast.MapType: return "map[" + formatType(t.Key) + "]" + formatType(t.Value)
	case *ast.InterfaceType: return "interface{}"
	case *ast.ChanType: return "chan " + formatType(t.Value)
	default: return "T"
	}
}
"""

# ---------------------------------------------------------
# 工具函数
# ---------------------------------------------------------

def ensure_unicode(s):
    if isinstance(s, text_type): return s
    if isinstance(s, bytes): return s.decode('utf-8', errors='ignore')
    return text_type(s)

def get_gitignored_files(repo_path):
    try:
        ignored = subprocess.check_output(
            ["git", "ls-files", "--others", "-i", "--exclude-standard"],
            cwd=repo_path
        ).decode('utf-8', errors='ignore').splitlines()
        return set(ignored)
    except Exception:
        return set()

# ---------------------------------------------------------
# 核心分析器类
# ---------------------------------------------------------

class HybridGoExtractor:
    def __init__(self, filepath, temp_go_parser_path=None):
        self.filepath = filepath
        self.temp_go_parser_path = temp_go_parser_path
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            self.content = f.read()
        
        # 默认空数据结构 (Short Keys)
        self.data = {
            "pk": "unknown", "im": [], "st": [], "if": [], 
            "fn": [], "md": {}, "vr": [], "cn": [], 
            "cm": [], "stat": {"gr": 0, "ch": 0, "er": 0}
        }

    def process(self):
        # 1. 尝试 Go AST 解析
        if self.temp_go_parser_path and self._try_ast_parse():
            return self.data
        
        # 2. 回退到正则解析
        self._regex_parse()
        return self.data

    def _try_ast_parse(self):
        """尝试运行嵌入的 Go AST 解析器"""
        try:
            # 调用 go run parser.go target.go
            cmd = ["go", "run", self.temp_go_parser_path, self.filepath]
            # 设置超时防止卡死
            if sys.version_info[0] >= 3:
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=5)
            else:
                output = subprocess.check_output(cmd, stderr=open(os.devnull, 'w'))
            
            parsed = json.loads(output.decode('utf-8'))
            
            # 映射数据
            self.data = parsed
            # 确保 map 存在
            if not self.data.get("md"): self.data["md"] = {}
            return True
        except Exception:
            return False

    def _regex_parse(self):
        """正则回退模式 (尽可能模拟 AST 输出结构)"""
        c = self.content
        
        # Package
        m = re.search(r'^\s*package\s+(\w+)', c, re.MULTILINE)
        if m: self.data["pk"] = m.group(1)

        # Imports
        self.data["im"] = re.findall(r'import\s+"([^"]+)"', c)
        multi = re.findall(r'import\s+\(\s*([\s\S]*?)\s*\)', c)
        for blk in multi:
            self.data["im"].extend(re.findall(r'"([^"]+)"', blk))
        self.data["im"] = sorted(list(set(self.data["im"])))

        # Functions (func Name(...) ...)
        for m in re.finditer(r'func\s+(\w+)\s*\(([^)]*)\)\s*([^{]*)', c):
            name, params, ret = m.groups()
            # 简单计算复杂度 (count if/for)
            body_start = m.end()
            body_sample = c[body_start:body_start+500]
            cx = body_sample.count("if ") + body_sample.count("for ") + 1
            
            self.data["fn"].append({
                "n": name,
                "p": params[:50], # truncate
                "r": ret.strip()[:30],
                "cx": cx
            })

        # Methods (func (r Type) Name(...) ...)
        for m in re.finditer(r'func\s+\([^)]+\s+\*?(\w+)\)\s+(\w+)', c):
            recv, name = m.groups()
            if recv not in self.data["md"]: self.data["md"][recv] = []
            self.data["md"][recv].append({"n": name})

        # Structs
        for m in re.finditer(r'type\s+(\w+)\s+struct', c):
            self.data["st"].append({"n": m.group(1)})

        # Interfaces
        for m in re.finditer(r'type\s+(\w+)\s+interface', c):
            self.data["if"].append({"n": m.group(1)})

        # Stats Heuristics
        self.data["stat"]["gr"] = c.count("go func")
        self.data["stat"]["ch"] = c.count("chan ") + c.count("<-")
        self.data["stat"]["er"] = c.count("if err != nil")

        # Comments (Doc sampling)
        comments = re.findall(r'//\s*(.+)', c)
        good_comments = [x.strip()[:80] for x in comments if len(x) > 10 and "TODO" not in x]
        self.data["cm"] = good_comments[:3]

# ---------------------------------------------------------
# 项目遍历与生成
# ---------------------------------------------------------

def rglob_go_files(root, include_test=False):
    files = []
    for dp, dn, fns in os.walk(ensure_unicode(root)):
        # 过滤常见无关目录
        dn[:] = [d for d in dn if not d.startswith('.') and d not in ['vendor', 'node_modules', 'testdata']]
        for fn in fns:
            if fn.endswith('.go'):
                if not include_test and fn.endswith('_test.go'): continue
                files.append(os.path.join(dp, fn))
    return files

def generate_snapshot(repo_path, output_path, graph=False, include_test=False):
    repo_path = os.path.abspath(repo_path)
    
    # 1. 准备 AST 解析器临时文件
    temp_dir = tempfile.mkdtemp()
    ast_parser_path = os.path.join(temp_dir, "parser.go")
    has_go = False
    try:
        subprocess.check_call(["go", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(ast_parser_path, "w", encoding="utf-8") as f:
            f.write(GO_AST_PARSER_SRC)
        has_go = True
        print("✅ Go environment detected. Using precise AST analysis.")
    except:
        print("⚠️ Go not found. Falling back to Regex analysis.")
        ast_parser_path = None

    # 2. 初始化摘要结构
    digest = {
        "root": os.path.basename(repo_path),
        "pkgs": {}, # Key: package name
        "graph": {}, # Dependency graph
        "meta": {}
    }
    
    pkg_map = defaultdict(list) # pkg_name -> list of file data
    all_files = rglob_go_files(repo_path, include_test)
    ignored = get_gitignored_files(repo_path)

    print("Processing {} files...".format(len(all_files)))

    # 3. 逐文件分析
    total_cx = 0
    total_err_checks = 0
    
    for fpath in all_files:
        rel_path = os.path.relpath(fpath, repo_path)
        if rel_path in ignored: continue
        
        extractor = HybridGoExtractor(fpath, ast_parser_path if has_go else None)
        data = extractor.process()
        
        pkg_name = data.get("pk", "unknown")
        
        # 移除空字段以压缩 Token
        clean_data = {k: v for k, v in data.items() if v}
        clean_data["f"] = rel_path # 记录文件名
        
        # 统计聚合
        if "stat" in data:
            total_err_checks += data["stat"].get("er", 0)
            # 复杂度累加
            for fn in data.get("fn", []): total_cx += fn.get("cx", 1)
        
        pkg_map[pkg_name].append(clean_data)

        # 构建依赖图 (仅保留非标准库)
        deps = set()
        for imp in data.get("im", []):
            if "." in imp and not imp.startswith("github.com/user/repo"): # 简易过滤
                deps.add(imp)
        if deps:
            if pkg_name not in digest["graph"]: digest["graph"][pkg_name] = []
            digest["graph"][pkg_name].extend(list(deps))

    # 4. 聚合包数据 (Package Level Aggregation)
    # 为了进一步压缩，我们将同一个包下的文件内容合并，或者按文件列表列出
    for pkg, files_data in pkg_map.items():
        digest["pkgs"][pkg] = {
            "files": len(files_data),
            "cx_avg": 0, # 平均复杂度
            "contents": files_data # 这里包含详细的 struct/func
        }
        
        # 去重依赖图
        if pkg in digest["graph"]:
            digest["graph"][pkg] = sorted(list(set(digest["graph"][pkg])))

    # 5. 生成元数据 Summary
    digest["meta"] = {
        "files": len(all_files),
        "pkgs": len(pkg_map),
        "total_complexity": total_cx,
        "error_hotspots": total_err_checks,
        "strategy": "AST" if has_go else "Regex"
    }

    # 清理临时文件
    shutil.rmtree(temp_dir)

    # 6. 写入 YAML
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(digest, f, default_flow_style=False, sort_keys=False, width=120, allow_unicode=True)
    
    print("✅ Snapshot generated: {} ({:.1f}KB)".format(output_path, os.path.getsize(output_path)/1024.0))

    # 7. 图形生成 (可选)
    if graph:
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            G = nx.DiGraph()
            for src, dsts in digest["graph"].items():
                for dst in dsts:
                    # 简化节点名: github.com/a/b -> b
                    short_dst = dst.split('/')[-1]
                    G.add_edge(src, short_dst)
            
            plt.figure(figsize=(12, 12))
            pos = nx.spring_layout(G, k=0.5)
            nx.draw(G, pos, with_labels=True, node_size=1500, node_color="lightblue", font_size=8, arrowsize=15)
            plt.savefig(output_path.replace(".yaml", ".png"))
            print("✅ Graph saved.")
        except ImportError:
            print("⚠️  Skipping graph (networkx/matplotlib missing).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Go Semantic Snapshot Generator v2 (AST+Regex)")
    parser.add_argument("repo", help="Go project path")
    parser.add_argument("-o", "--out", default="go_digest.yaml", help="Output file")
    parser.add_argument("--graph", action="store_true", help="Generate dependency graph")
    parser.add_argument("--no-test", action="store_true", help="Exclude _test.go")
    
    args = parser.parse_args()
    generate_snapshot(args.repo, args.out, args.graph, not args.no_test)

