from typing import Dict, List, Optional, Set
from codesage.analyzers.semantic.symbol_table import SymbolTable, Symbol, Scope
from codesage.analyzers.semantic.models import CodeLocation

class ReferenceResolver:
    def __init__(self, project_symbols: Dict[str, SymbolTable]):
        """
        Initialize the ReferenceResolver with a map of file path to SymbolTable.
        """
        self.project_symbols = project_symbols
        # Global map: symbol_name -> List[(file_path, Symbol)]
        # This is a simplified global index for quick lookup.
        self.global_index: Dict[str, List[tuple[str, Symbol]]] = {}
        self._build_global_index()

    def _build_global_index(self):
        """
        Builds a global index of all exported symbols.
        """
        for file_path, table in self.project_symbols.items():
            for symbol in table.get_all_definitions():
                # We primarily index exported symbols or those at module level for cross-file resolution
                if symbol.scope == Scope.MODULE or symbol.is_exported:
                    if symbol.name not in self.global_index:
                        self.global_index[symbol.name] = []
                    self.global_index[symbol.name].append((file_path, symbol))

    def resolve(self):
        """
        Resolves references across all files.
        Iterates through all symbols in all tables, and for those that represent usage (like imports)
        or implicit usage (which we don't have fully detailed in Symbol yet, but we can link Imports),
        we establish links.

        Since our current Symbol structure captures definitions (Functions, Classes, Imports),
        we can currently only link 'Import' symbols to their definitions.

        Future work: If we had a list of 'UnresolvedReference' or 'Usage' nodes, we would link those too.
        For now, we link Import symbols to the defined Symbol in the target file.
        """
        for file_path, table in self.project_symbols.items():
            for symbol in table.get_all_definitions():
                if symbol.type == "import":
                    self._resolve_import(symbol, file_path)

    def _resolve_import(self, import_symbol: Symbol, current_file_path: str):
        """
        Tries to find the definition for an import symbol.
        import_symbol.name contains the path (e.g., "os.path" or "codesage.utils").
        """
        target_path = import_symbol.name

        # Simplified resolution logic:
        # 1. Check if the import path matches a known file path (module import)
        # 2. Check if the last part of the import path matches a symbol in a file matching the rest of the path

        # Case 1: Direct module import matching a file
        # e.g. import codesage.utils -> codesage/utils.py
        # We convert dot notation to path
        potential_path_suffix = target_path.replace('.', '/') + ".py"

        found_target = False

        for file_path, table in self.project_symbols.items():
            if file_path.endswith(potential_path_suffix):
                # We found the file being imported.
                # We can link the import symbol to the module (conceptually)
                # But our SymbolTable doesn't have a 'Module' symbol usually.
                # We can tag it as resolved to that file.
                import_symbol.references.append(CodeLocation(file=file_path, start_line=0, end_line=0))
                found_target = True
                break

        if found_target:
            return

        # Case 2: Import from (from x import y)
        # In our parser, `from x import y` results in an ImportNode with path `x.y`.
        # We need to split it.
        if "." in target_path:
            module_part, symbol_part = target_path.rsplit(".", 1)
            module_path_suffix = module_part.replace('.', '/') + ".py"

            for file_path, table in self.project_symbols.items():
                if file_path.endswith(module_path_suffix):
                    # Found the module, look for the symbol inside it
                    target_symbol = table.lookup(symbol_part, Scope.MODULE)
                    # Also check classes or functions
                    if not target_symbol:
                        # Try to find any symbol with that name
                        # This is a simplification
                        candidates = table._symbols.get(symbol_part, [])
                        if candidates:
                            target_symbol = candidates[0]

                    if target_symbol:
                        import_symbol.references.append(target_symbol.location)
                        target_symbol.references.append(import_symbol.location)
                        found_target = True
                    break
