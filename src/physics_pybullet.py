# src/physics_pybullet.py
import pybullet as p
import pybullet_data
import time, math, random
from .types import World

def run_simulation_pybullet(world: World, show_gui: bool = True):
    """물리 기반 PyBullet 시뮬레이션 (공기저항, 진공, 바람, 마찰, 각속도 포함)"""
    # ✅ 시뮬레이터 연결
    cid = p.connect(p.GUI if show_gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(*world.environment.gravity)

    # ✅ 환경 변수 설정
    R = 287.05
    temperature = getattr(world.environment, "temperature", 298.0)
    pressure = getattr(world.environment, "pressure", 101325.0)
    air_density = getattr(world.environment, "air_density", pressure / (R * temperature))
    drag_coefficient = getattr(world.environment, "drag_coefficient", 0.47)

    wind = getattr(world.environment, "wind", {"direction": [0, 0, 0], "strength": 0.0})
    wind_dir = wind.get("direction", [0, 0, 0])
    wind_strength = wind.get("strength", 0.0)
    use_turbulence = (sum(abs(d) for d in wind_dir) < 1e-5 and wind_strength > 0)

    time_step = world.environment.time_step
    steps = int(world.environment.duration / time_step)

    # ✅ 항상 기본 바닥 plane 생성
    ground_id = p.loadURDF("plane.urdf")
    p.changeDynamics(ground_id, -1, restitution=0.3, lateralFriction=0.8)

    id_map = {}

    # ✅ 객체 생성
    for obj in world.objects:
        pos = obj.initial_state.position
        lin_v = obj.initial_state.velocity
        mass = obj.initial_state.mass
        ori = getattr(obj.initial_state, "orientation", [0, 0, 0, 1])
        cross_section = getattr(obj, "cross_section", 0.0314)
        friction = getattr(obj, "friction", 0.6)
        restitution = getattr(obj, "restitution", 0.3)

        # plane은 이미 있음 → 중복 생성 방지
        if obj.type == "plane":
            print(f"[INFO] plane 객체 감지됨 — 기본 바닥이 이미 활성화되어 생략함.")
            continue

        # 구체(ball)
        if obj.type == "ball":
            r = math.sqrt(cross_section / math.pi)
            col_id = p.createCollisionShape(p.GEOM_SPHERE, radius=r)
            vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=r, rgbaColor=[1, 0, 0, 1])

        # 박스(box, table)
        elif obj.type in ["box", "table"]:
            side = (cross_section ** 0.5) * 2
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[side / 2] * 3)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[side / 2] * 3)

        # 미지원 타입
        else:
            print(f"[WARN] 지원되지 않는 객체: {obj.type}")
            continue

        # ✅ 객체 생성
        body = p.createMultiBody(
            baseMass=mass,
            baseCollisionShapeIndex=col_id,
            baseVisualShapeIndex=vis_id,
            basePosition=pos,
            baseOrientation=ori
        )

        # ✅ 마찰 및 반발 계수 적용
        p.changeDynamics(
            body, -1,
            restitution=restitution,
            lateralFriction=friction,
            rollingFriction=0.01,
            spinningFriction=0.01
        )

        # ✅ 초기 속도 및 각속도 적용
        ang_v = getattr(obj.initial_state, "angular_velocity", None)
        if ang_v is not None:
            p.resetBaseVelocity(body, linearVelocity=lin_v, angularVelocity=ang_v)
        else:
            # 공이며 선속도가 있으면 ω = v/r 가정
            if obj.type == "ball":
                if abs(lin_v[0]) + abs(lin_v[1]) + abs(lin_v[2]) > 1e-6:
                    omega = [0.0, (lin_v[0] / r) if r > 0 else 0.0, 0.0]
                    p.resetBaseVelocity(body, linearVelocity=lin_v, angularVelocity=omega)
                else:
                    p.resetBaseVelocity(body, linearVelocity=lin_v)
            else:
                p.resetBaseVelocity(body, linearVelocity=lin_v)

        id_map[obj.id] = {"body": body, "area": cross_section}

    # ✅ 시뮬레이션 루프
    for _ in range(steps):
        for meta in id_map.values():
            body = meta["body"]
            A = meta["area"]
            try:
                vel, _ = p.getBaseVelocity(body)
                wind_v = [wind_strength * d for d in wind_dir]
                rel_v = [vel[i] - wind_v[i] for i in range(3)]
                speed = math.sqrt(sum(v ** 2 for v in rel_v))

                # --- 공기저항 ---
                if speed > 1e-6 and air_density > 0:
                    unit_v = [v / speed for v in rel_v]
                    drag_mag = 0.5 * air_density * drag_coefficient * A * (speed ** 2)
                    drag_force = [-drag_mag * u for u in unit_v]
                    p.applyExternalForce(body, -1, drag_force, [0, 0, 0], p.WORLD_FRAME)

                # --- 난류 효과 ---
                if use_turbulence:
                    jitter = (random.random() - 0.5) * 2.0
                    turb = [wind_strength * 0.2 * jitter, 0.0, 0.0]
                    p.applyExternalForce(body, -1, turb, [0, 0, 0], p.WORLD_FRAME)

            except Exception:
                pass

        p.stepSimulation()
        if show_gui:
            time.sleep(time_step)

    # ✅ 최종 상태 저장
    final = world.model_copy(deep=True)
    for obj in final.objects:
        if obj.id in id_map:
            b = id_map[obj.id]["body"]
            pos, orn = p.getBasePositionAndOrientation(b)
            vel, ang = p.getBaseVelocity(b)
            obj.initial_state.position = list(pos)
            obj.initial_state.orientation = list(orn)
            obj.initial_state.velocity = list(vel)

    p.disconnect(cid)
    return {"final_state": final.model_dump(), "world": world}
