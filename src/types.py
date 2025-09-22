from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

Vec2 = List[float]

class ObjectProps(BaseModel):
    radius: Optional[float] = None
    size: Optional[Vec2] = None
    mass: Optional[float] = 0.0
    restitution: Optional[float] = 0.4
    friction: Optional[float] = 0.5

class InitialState(BaseModel):
    position: Vec2
    velocity: Vec2

class WorldObject(BaseModel):
    id: str
    type: Literal["ball","box","plane","table"]
    properties: Optional[ObjectProps] = ObjectProps()
    initial_state: InitialState
    static: bool = False

class Environment(BaseModel):
    dimensions: Literal["2D"] = "2D"
    gravity: Vec2 = [0.0, -9.81]
    time_step: float = 0.01
    duration: float = 5.0

class Action(BaseModel):
    target_id: Optional[str] = None
    type: Literal["push","drop","apply_force"]
    params: Dict[str, Any] = {}

class World(BaseModel):
    environment: Environment
    objects: List[WorldObject]
    actions: Optional[List[Action]] = []
