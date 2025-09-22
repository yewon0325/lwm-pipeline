# src/physics_pymunk.py
import pymunk
from typing import Dict, List
from .types import World

def _add_ball(space, obj):
    r = obj.properties.radius or 0.1
    mass = obj.properties.mass or 0.15
    moment = pymunk.moment_for_circle(mass, 0, r)
    body = pymunk.Body(mass, moment, body_type=pymunk.Body.DYNAMIC)
    body.position = tuple(obj.initial_state.position)
    body.velocity = tuple(obj.initial_state.velocity)
    shape = pymunk.Circle(body, r)
    shape.elasticity = obj.properties.restitution or 0.6
    shape.friction = obj.properties.friction or 0.5
    space.add(body, shape)
    return body, shape

def _add_box(space, obj, static=False):
    sx, sy = obj.properties.size or [1.0, 0.1]
    mass = 0 if static else (obj.properties.mass or 1.0)
    if static:
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
    else:
        moment = pymunk.moment_for_box(mass, (sx, sy))
        body = pymunk.Body(mass, moment, body_type=pymunk.Body.DYNAMIC)
    body.position = tuple(obj.initial_state.position)
    body.velocity = tuple(obj.initial_state.velocity)
    shape = pymunk.Poly.create_box(body, (sx, sy))
    shape.elasticity = obj.properties.restitution or 0.2
    shape.friction = obj.properties.friction or 0.8
    space.add(body, shape)
    return body, shape

def _add_plane(space, y=0.0):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    seg = pymunk.Segment(body, (-1000, y), (1000, y), 0.0)
    seg.elasticity = 0.3
    seg.friction = 0.9
    space.add(body, seg)
    return body, seg

def build_space(world: World):
    space = pymunk.Space()
    space.gravity = tuple(world.environment.gravity)
    id2body = {}
    for obj in world.objects:
        if obj.type == "plane":
            _add_plane(space, y=obj.initial_state.position[1])
        elif obj.type == "table" and obj.static:
            body, shape = _add_box(space, obj, static=True)
            id2body[obj.id] = body
        elif obj.type == "ball":
            body, shape = _add_ball(space, obj)
            id2body[obj.id] = body
        elif obj.type == "box" and not obj.static:
            body, shape = _add_box(space, obj, static=False)
            id2body[obj.id] = body
    return space, id2body

def apply_actions(space, id2body, world: World):
    for act in (world.actions or []):
        if act.type in ["push", "apply_force"] and act.target_id in id2body:
            force = tuple(act.params.get("force", [0.0, 0.0]))
            id2body[act.target_id].apply_impulse_at_local_point(force)

def run(world: World):
    space, id2body = build_space(world)
    apply_actions(space, id2body, world)

    dt = world.environment.time_step
    steps = int(world.environment.duration / dt)
    history = {k: [] for k in id2body.keys()}
    for i in range(steps):
        space.step(dt)
        for k, body in id2body.items():
            pos = (float(body.position.x), float(body.position.y))
            vel = (float(body.velocity.x), float(body.velocity.y))
            history[k].append(pos + vel)

    # ▼▼▼ 오류 해결의 핵심 부분 ▼▼▼
    # 시뮬레이션 최종 상태를 생성합니다.
    final_world_state = world.model_copy(deep=True)
    for obj in final_world_state.objects:
        if obj.id in id2body:
            body = id2body[obj.id]
            obj.initial_state.position = list(body.position)
            obj.initial_state.velocity = list(body.velocity)
    final_world_state.actions = [] # 실행된 액션은 초기화

    # history와 함께 final_state를 반환합니다.
    return {"history": history, "final_state": final_world_state.model_dump(), "world": world}