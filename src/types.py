from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class InitialState(BaseModel):
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    mass: float = 1.0
    orientation: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])  # ✅ 기본 회전값 (쿼터니언)


class WorldObject(BaseModel):
    id: str
    type: Literal["ball", "box", "plane", "table", "sphere"] = "ball"
    initial_state: InitialState

class Environment(BaseModel):
    gravity: List[float] = [0.0, 0.0, -9.81]
    wind: dict = Field(default_factory=lambda: {"direction": [1.0, 0.0, 0.0], "strength": 0.0})
    time_step: float = 0.01
    duration: float = 5.0

class World(BaseModel):
    objects: List[WorldObject]
    environment: Environment
    
class WorldEnvironment(BaseModel):
    gravity: List[float] = Field(default_factory=lambda: [0.0, 0.0, -9.81])
    wind: dict = Field(default_factory=lambda: {"direction": [0, 0, 0], "strength": 0.0})
    temperature: float = 25.0
    humidity: float = 0.5
    air_density: float = 1.225  # kg/m³, default Earth atmosphere
    drag_coefficient: float = 0.47  # default sphere drag coefficient
    time_step: float = 0.01
    duration: float = 5.0