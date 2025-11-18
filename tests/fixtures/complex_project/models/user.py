class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def get_name(self) -> str:
        return self.name
