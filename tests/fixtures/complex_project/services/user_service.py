from models.user import User

class UserService:
    def __init__(self):
        self.users = []

    def add_user(self, name: str, email: str) -> User:
        user = User(name, email)
        self.users.append(user)
        return user

async def send_welcome_email(user: User):
    print(f"Sending welcome email to {user.email}")
