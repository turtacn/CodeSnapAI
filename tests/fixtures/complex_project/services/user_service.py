from models.user import User

class UserService:
    def __init__(self):
        self.users = []

    def create_user(self, name):
        user = User(name)
        self.users.append(user)
        return user

    def get_user(self, name):
        for user in self.users:
            if user.name == name:
                return user
        return None

    # 20+ methods to trigger God Class anti-pattern
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass
