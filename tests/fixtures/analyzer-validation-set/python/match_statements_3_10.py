"""
Test case for Python 3.10+ match statements
"""

def process_data(data):
    """Function using match statement for complexity testing"""
    match data:
        case int() if data > 0:
            return f"Positive integer: {data}"
        case int() if data < 0:
            return f"Negative integer: {data}"
        case int():
            return "Zero"
        case str() if len(data) > 10:
            return f"Long string: {data[:10]}..."
        case str():
            return f"Short string: {data}"
        case list() if len(data) > 5:
            return f"Large list with {len(data)} items"
        case list():
            return f"Small list: {data}"
        case dict():
            return f"Dictionary with {len(data)} keys"
        case _:
            return f"Unknown type: {type(data)}"

def complex_match_with_guards(value):
    """Complex match statement with multiple guards"""
    match value:
        case {"type": "user", "id": user_id} if user_id > 0:
            return f"Valid user: {user_id}"
        case {"type": "user", "id": user_id}:
            return f"Invalid user ID: {user_id}"
        case {"type": "admin", "permissions": perms} if "write" in perms:
            return f"Admin with write access: {perms}"
        case {"type": "admin", "permissions": perms}:
            return f"Admin with limited access: {perms}"
        case {"type": str() as user_type}:
            return f"Unknown user type: {user_type}"
        case _:
            return "Invalid user data"

def nested_match_statements(data):
    """Function with nested match statements"""
    match data:
        case {"category": "A", "items": items}:
            for item in items:
                match item:
                    case {"priority": "high"}:
                        return "High priority item found"
                    case {"priority": "medium"}:
                        return "Medium priority item found"
                    case _:
                        continue
            return "No priority items in category A"
        case {"category": "B"}:
            return "Category B processing"
        case _:
            return "Unknown category"

class DataProcessor:
    """Class with methods using match statements"""
    
    def process_request(self, request):
        """Method with match statement"""
        match request:
            case {"action": "create", "data": data}:
                return self._create_item(data)
            case {"action": "update", "id": item_id, "data": data}:
                return self._update_item(item_id, data)
            case {"action": "delete", "id": item_id}:
                return self._delete_item(item_id)
            case {"action": "list"}:
                return self._list_items()
            case _:
                raise ValueError("Invalid request format")
    
    def _create_item(self, data):
        return f"Created item with data: {data}"
    
    def _update_item(self, item_id, data):
        return f"Updated item {item_id} with data: {data}"
    
    def _delete_item(self, item_id):
        return f"Deleted item {item_id}"
    
    def _list_items(self):
        return "Listed all items"