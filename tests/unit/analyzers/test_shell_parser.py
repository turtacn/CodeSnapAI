import unittest
from codesage.analyzers.shell_parser import ShellParser

class TestShellParser(unittest.TestCase):
    def setUp(self):
        self.parser = ShellParser()

    def test_extract_commands(self):
        code = """
        #!/bin/bash
        tar -czf archive.tar.gz /path
        echo "Done"
        git status
        """
        self.parser.parse(code)
        commands = self.parser.extract_external_commands()
        self.assertIn("tar", commands)
        self.assertIn("git", commands)
        self.assertNotIn("echo", commands) # Builtin

    def test_variable_scope(self):
        code = """
        global_var="hello"

        my_func() {
            local local_var="world"
            other_var="global_implied"
        }
        """
        self.parser.parse(code)
        vars = self.parser.extract_variables()

        # Verify global_var
        global_vars = [v for v in vars if v.name == "global_var"]
        self.assertEqual(len(global_vars), 1)
        self.assertEqual(global_vars[0].kind, "global")

        # Verify local_var
        local_vars = [v for v in vars if v.name == "local_var"]
        self.assertEqual(len(local_vars), 1)
        self.assertEqual(local_vars[0].kind, "local")

        # Verify other_var (inside func but no local keyword -> global)
        other_vars = [v for v in vars if v.name == "other_var"]
        self.assertEqual(len(other_vars), 1)
        self.assertEqual(other_vars[0].kind, "global")

    def test_functions(self):
        code = """
        function my_func {
            echo "1"
        }
        other_func() {
            echo "2"
        }
        """
        self.parser.parse(code)
        funcs = self.parser.extract_functions()
        self.assertEqual(len(funcs), 2)
        names = {f.name for f in funcs}
        self.assertIn("my_func", names)
        self.assertIn("other_func", names)
