# src/motion_mapper.py
import math

def map_action_to_physics(action: dict, obj: dict) -> dict:
    """
    자연어로 표현된 행동(action)을 물리 파라미터(속도, 회전 등)로 변환한다.
    """
    t = (action.get("type") or "").lower()
    mag = float(action.get("magnitude", 1.0))
    dx, dy, dz = [float(d) for d in action.get("direction", [0, 0, 0])]

    cross_section = obj.get("cross_section", 0.0314)  # 구체 기준 (r ≈ 0.1)
    r = math.sqrt(max(cross_section, 1e-6) / math.pi)

    if t == "throw":  # 던짐
        return {
            "velocity": [dx * mag * 5.0, dy * mag * 5.0, dz * mag * 5.0],
            "angular_velocity": [dy * 2.0, -dx * 2.0, 0.0],
            "restitution": 0.6,
        }

    elif t == "roll":  # 굴림
        vx, vy = dx * mag * 2.0, dy * mag * 2.0
        return {
            "velocity": [vx, vy, 0.0],
            "angular_velocity": [0.0, (vx / r) if r > 0 else 0.0, 0.0],
            "rolling_friction": 0.02,
        }

    elif t == "bounce":  # 튕김
        return {"velocity": [dx, dy, abs(dz) + mag * 3.0], "restitution": 0.9}

    elif t == "stop":  # 정지
        return {"velocity": [0.0, 0.0, 0.0], "angular_velocity": [0.0, 0.0, 0.0]}

    elif t == "lift":  # 위로 들기
        return {"velocity": [0.0, 0.0, mag * 3.0]}

    elif t == "collide":  # 충돌
        return {"restitution": 0.5, "friction": 0.5}

    return {}
