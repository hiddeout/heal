import asyncio

class Cache:
    def __init__(self):
        self.dict = {}
        self.lock = asyncio.Lock()

    async def get(self, key):
        async with self.lock:
            return self.dict.get(key)

    async def set(self, key, value, timeout=None):
        async with self.lock:
            exist = self.dict.get(key)
            self.dict[key] = value
            if timeout is not None and exist == None:
                asyncio.create_task(self.expire(key, timeout))

    async def remove(self, key):
        async with self.lock:
            if key in self.dict:
                del self.dict[key]

    async def clear(self):
        async with self.lock:
            self.dict.clear()

    async def expire(self, key, timeout):
        await asyncio.sleep(timeout)
        async with self.lock:
            if key in self.dict:
                del self.dict[key]