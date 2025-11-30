class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(f"Hello, {self.name}!")

def main():
    greeter = Greeter("world")
    greeter.greet()

if __name__ == "__main__":
    main()
