import unittest
from codesage.analyzers.go_parser import GoParser
from codesage.analyzers.ast_models import FunctionNode, ClassNode, VariableNode

class TestGoParser(unittest.TestCase):
    def setUp(self):
        self.parser = GoParser()

    def test_parse_struct_methods(self):
        code = """
        package main

        type Person struct {
            Name string
            Age  int
        }

        func (p *Person) Greet() string {
            return "Hello " + p.Name
        }
        """
        self.parser.parse(code)
        structs = self.parser.extract_structs()
        self.assertEqual(len(structs), 1)
        self.assertEqual(structs[0].name, "Person")
        self.assertEqual(len(structs[0].fields), 2)
        self.assertEqual(structs[0].fields[0].name, "Name")

        functions = self.parser.extract_functions()
        # Should have 1 function (method)
        self.assertEqual(len(functions), 1)
        self.assertEqual(functions[0].name, "Greet")
        self.assertIn("*Person", functions[0].receiver)

    def test_parse_interfaces(self):
        code = """
        package main

        type Greeter interface {
            Greet(name string) string
            SayBye()
        }
        """
        self.parser.parse(code)
        interfaces = self.parser.extract_interfaces()
        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].name, "Greeter")
        self.assertEqual(len(interfaces[0].methods), 2)
        self.assertEqual(interfaces[0].methods[0].name, "Greet")
        self.assertEqual(interfaces[0].methods[1].name, "SayBye")

    def test_parse_imports(self):
        code = """
        package main
        import (
            "fmt"
            alias "strings"
        )
        """
        self.parser.parse(code)
        imports = self.parser.extract_imports()
        self.assertEqual(len(imports), 2)
        self.assertEqual(imports[0].path, "fmt")
        self.assertIsNone(imports[0].alias)
        self.assertEqual(imports[1].path, "strings")
        self.assertEqual(imports[1].alias, "alias")

    def test_complexity(self):
        code = """
        package main
        func complex(n int) {
            if n > 0 {
                for i := 0; i < n; i++ {
                    if i % 2 == 0 {
                        fmt.Println(i)
                    }
                }
            } else {
                switch n {
                case 0:
                    return
                default:
                    return
                }
            }
        }
        """
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        self.assertEqual(len(functions), 1)
        # Complexity:
        # Base = 1
        # if n > 0 (+1)
        # for (+1)
        # if i % 2 (+1)
        # else (not counted usually, but let's see implementation. `else` is not in GO_COMPLEXITY_NODES)
        # switch (+1)
        # case 0 (+1)
        # default (+1)
        # Total = 1 + 1 + 1 + 1 + 1 + 1 + 1 = 7
        self.assertEqual(functions[0].complexity, 7)
