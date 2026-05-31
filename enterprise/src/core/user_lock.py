import asyncio
class UserLockManager:
    def __init__(self):
        self._locks:dict[str,asyncio.Lock] = {}
    
    def get_lock(self,learn_id:str)-> asyncio.Lock:
        if learn_id not in self._locks:
            self._locks[learn_id] = asyncio.Lock()
        return self._locks[learn_id]
    
user_lock_manager = UserLockManager()