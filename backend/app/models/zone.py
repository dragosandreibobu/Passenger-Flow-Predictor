from typing import List
from pydantic import BaseModel

class Zone(BaseModel):
    id: str
    name: str
    camera_id: str
    type: str  # entrance, checkin, bag_drop, security, boarding, other
    polygon: List[List[float]]
