import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Type
from pydantic import BaseModel


class BaseSubscriberNode(ABC):
    def __init__(self, node_id: str):
        self.node_id = node_id
        
        @abstractmethod
        async def connect(self):
            pass
        
        @abstractmethod
        async def disconnect(self):
            pass
        