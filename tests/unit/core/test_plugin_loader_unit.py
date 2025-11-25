import os
import pytest
from codesage.cli.plugin_loader import PluginManager
from codesage.core.interfaces import Plugin, Rule, CodeIssue

class MockRule(Rule):
    id = "mock-rule"
    description = "Mock rule"

    def check(self, file_path, content, context):
        return []

class MockPlugin(Plugin):
    def register(self, engine):
        engine.register_rule(MockRule())

def test_plugin_manager_load(tmp_path):
    # Create a dummy plugin file
    plugin_file = tmp_path / "test_plugin.py"
    content = """
from codesage.core.interfaces import Plugin, Rule

class TestRule(Rule):
    id = "test-rule"
    description = "Test rule"
    def check(self, f, c, ctx): return []

class TestPlugin(Plugin):
    def register(self, engine):
        engine.register_rule(TestRule())
"""
    plugin_file.write_text(content)

    manager = PluginManager(str(tmp_path))
    manager.load_plugins()

    assert len(manager.loaded_plugins) == 1
    assert len(manager.rules) == 1
    assert manager.rules[0].id == "test-rule"
