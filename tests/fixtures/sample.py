import os
import sys
import json
from typing import List, Optional

def decorator(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

@decorator
def decorated_func():
    pass

async def async_func():
    await asyncio.sleep(1)

class MyClass:
    def __init__(self):
        pass

    def method1(self):
        pass

    async def async_method(self):
        pass
