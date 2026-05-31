from loguru import logger
from typing import Callable,List

class Transition:
    def __init__(self,source:str,event:str,target:str):
        self.source = source
        self.event = event
        self.target = target

class FSM:
    def __init__(self,states:List[str],transitions:List[Transition],initial_state:str):
        self._states = states
        self._transitions = transitions
        self._current_state = initial_state
        self._callbacks:dict[str,list[Callable]] = {}

    @property
    def current_state(self)->str:
        return self._current_state
    
    def trigger(self,event:str)->bool:
        for t in self._transitions:
            if t.source == self._current_state and t.event == event:
                old_state = self._current_state
                self._current_state = t.target
                logger.info(f"状态转移: {old_state} ->{event} -> {self._current_state}")
                for cb in self._callbacks.get(self._current_state,[]):
                    print(cb)
                    cb()
                return True
        logger.warning(f"非法转移: {self._current_state} + {event}")
        return False
    
    def on_enter(self,state:str,callback:Callable):
        if state not in self._callbacks:
            self._callbacks[state] = []
        self._callbacks[state].append(callback)

