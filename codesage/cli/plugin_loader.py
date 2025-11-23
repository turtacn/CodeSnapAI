import importlib.util
import inspect
import os
import sys
import logging
from pathlib import Path
from typing import List, Type

from codesage.core.interfaces import Plugin, Rule, Analyzer

logger = logging.getLogger(__name__)

class PluginManager:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: List[Plugin] = []
        self.rules: List[Rule] = []
        self.analyzers: List[Analyzer] = []

    def load_plugins(self, engine_context=None):
        """
        Scans plugin_dir for .py files and loads them.
        """
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist.")
            return

        logger.info(f"Scanning for plugins in {self.plugin_dir}")
        sys.path.insert(0, str(self.plugin_dir))

        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("__"):
                continue

            try:
                module_name = plugin_file.stem
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check for classes implementing Plugin interface
                found_plugin = False
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                        try:
                            plugin_instance = obj()
                            plugin_instance.register(self)
                            self.loaded_plugins.append(plugin_instance)
                            found_plugin = True
                            logger.info(f"Loaded plugin: {name}")
                        except Exception as e:
                            logger.error(f"Error registering plugin {name}: {e}")

                if not found_plugin:
                    # Fallback: check for a standalone 'register' function
                    if hasattr(module, 'register') and callable(module.register):
                        try:
                            module.register(self)
                            logger.info(f"Loaded plugin from module: {module_name}")
                        except Exception as e:
                            logger.error(f"Error executing register() in {module_name}: {e}")

            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_file.name}: {e}")

    def register_rule(self, rule: Rule):
        self.rules.append(rule)
        logger.debug(f"Registered rule: {rule.id}")

    def register_analyzer(self, analyzer: Analyzer):
        self.analyzers.append(analyzer)
        logger.debug(f"Registered analyzer: {analyzer.id}")

def load_plugins(cli_group):
    # This function is used by main.py to load extra commands from plugins.
    # It seems to be a different usage than PluginManager.load_plugins.
    # We will simulate scanning for CLI extensions.
    pass
