"""
Test case for nested async functions
"""
import asyncio
from typing import Callable, Awaitable

async def outer_async_function(data: list) -> dict:
    """Outer async function with nested async functions"""
    
    async def inner_async_processor(item: str) -> str:
        """Inner async function for processing items"""
        await asyncio.sleep(0.1)
        return item.upper()
    
    async def inner_async_validator(item: str) -> bool:
        """Another inner async function for validation"""
        await asyncio.sleep(0.05)
        return len(item) > 0
    
    def sync_helper(item: str) -> str:
        """Sync helper function nested inside async"""
        return item.strip()
    
    results = {}
    for item in data:
        cleaned = sync_helper(item)
        if await inner_async_validator(cleaned):
            processed = await inner_async_processor(cleaned)
            results[item] = processed
    
    return results

def regular_function_with_nested_async():
    """Regular function containing nested async function"""
    
    async def nested_async_in_sync():
        """Async function nested in sync function"""
        await asyncio.sleep(1)
        return "done"
    
    # This would need to be run in an event loop
    return nested_async_in_sync

class AsyncProcessor:
    """Class with async methods"""
    
    async def process_data(self, data: list) -> list:
        """Async method with nested async function"""
        
        async def process_item(item):
            """Nested async function in method"""
            await asyncio.sleep(0.01)
            return item * 2
        
        results = []
        for item in data:
            result = await process_item(item)
            results.append(result)
        
        return results