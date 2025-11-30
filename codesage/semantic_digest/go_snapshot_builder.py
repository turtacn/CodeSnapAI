from __future__ import annotations
import re
import os
import json
import tempfile
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any

from codesage.semantic_digest.base_builder import BaseLanguageSnapshotBuilder, SnapshotConfig
from codesage.snapshot.models import FileSnapshot

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
				for _, name := range f.Names {
					ps = append(ps, name.Name+" "+typeStr)
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

class GoSemanticSnapshotBuilder(BaseLanguageSnapshotBuilder):
    def build(self) -> Dict[str, Any]:
        has_go = False
        try:
            subprocess.check_call(["go", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            has_go = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        digest = {
            "root": self.root_path.name, "pkgs": {}, "graph": {}, "meta": {}
        }

        pkg_map = defaultdict(list)
        all_files = self._collect_files()
        total_cx = 0
        total_err_checks = 0

        for fpath in all_files:
            data = self._extract_semantics(fpath, has_go)
            pkg_name = data.get("pk", "unknown")
            clean_data = {k: v for k, v in data.items() if v}
            clean_data["f"] = str(fpath.relative_to(self.root_path))

            if "stat" in data:
                total_err_checks += data["stat"].get("er", 0)
                clean_data["stat"] = {
                    "gr": data["stat"].get("gr", 0),
                    "ch": data["stat"].get("ch", 0),
                    "er": data["stat"].get("er", 0),
                }

            if "fn" in data:
                total_cx += sum(fn.get("cx", 1) for fn in data["fn"])

            pkg_map[pkg_name].append(clean_data)

            deps = {imp for imp in data.get("im", []) if "." in imp}
            if deps:
                digest["graph"].setdefault(pkg_name, []).extend(list(deps))

        for pkg, files_data in pkg_map.items():
            digest["pkgs"][pkg] = {
                "files": len(files_data),
                "cx_avg": 0,
                "contents": files_data
            }
            if pkg in digest["graph"]:
                digest["graph"][pkg] = sorted(list(set(digest["graph"][pkg])))

        digest["meta"] = {
            "files": len(all_files), "pkgs": len(pkg_map),
            "total_complexity": total_cx, "error_hotspots": total_err_checks,
            "strategy": "AST" if has_go else "Regex"
        }

        return digest

    def _collect_files(self) -> List[Path]:
        return list(self.root_path.rglob("*.go"))

    def _extract_semantics(self, file_path: Path, has_go: bool) -> Dict[str, Any]:
        if has_go:
            with tempfile.TemporaryDirectory() as temp_dir:
                parser_src_path = os.path.join(temp_dir, "parser.go")
                with open(parser_src_path, "w", encoding="utf-8") as f:
                    f.write(GO_AST_PARSER_SRC)

                parser_bin_path = os.path.join(temp_dir, "parser")
                try:
                    build_result = subprocess.run(["go", "build", "-o", parser_bin_path, parser_src_path], capture_output=True, text=True, check=True)
                    cmd = [parser_bin_path, str(file_path)]
                    output = subprocess.check_output(cmd, stderr=subprocess.PIPE, timeout=15)
                    return json.loads(output.decode('utf-8'))
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                    print(f"AST parsing failed for {file_path}: {e}")
                    if isinstance(e, subprocess.CalledProcessError):
                        print(f"Stderr: {e.stderr}")
                        if hasattr(e, 'stdout'):
                            print(f"Stdout: {e.stdout}")

        # Fallback to regex
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        data = {"pk": "unknown", "im": [], "fn": [], "md": {}, "st": [], "if": [],
                "stat": {"gr": 0, "ch": 0, "er": 0}}
        m = re.search(r'^\s*package\s+(\w+)', content, re.MULTILINE)
        if m: data["pk"] = m.group(1)
        data["im"] = re.findall(r'import\s+"([^"]+)"', content)
        data["stat"]["er"] = content.count("if err != nil")
        return data

    def _build_file_snapshot(self, file_path: Path) -> FileSnapshot:
        # This method is not used in the new dictionary-based build process,
        # but it's required to satisfy the abstract base class.
        pass
