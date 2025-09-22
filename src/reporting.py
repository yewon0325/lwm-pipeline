# src/reporting.py
import math
from typing import Dict, List
import matplotlib.pyplot as plt

def get_sound_description(material, speed):
    """재질과 속도에 따라 충돌음 묘사"""
    if speed < 0.5: return "조용한 소리가 났습니다."
    if material == "bouncy":
        return "경쾌한 '통통' 소리가 여러 번 났습니다." if speed > 3.0 else "가볍게 '통' 튀는 소리가 났습니다."
    elif material == "wood":
        return "꽤 큰 '쿵' 하는 둔탁한 소리가 났습니다." if speed > 3.0 else "'툭'하는 소리가 났습니다."
    else:
        return "요란한 '쾅' 소리가 났습니다." if speed > 4.0 else "평범한 충돌음이 들렸습니다."

def summarize(sim_out: Dict):
    """
    시뮬레이션 결과를 분석하여 자연어 시나리오를 생성합니다.
    특히 바닥과의 충돌 및 튀어 오름(bounce)을 상세히 묘사합니다.
    """
    history = sim_out.get("history", {})
    world = sim_out.get("world")
    if not world: return {"error": "World 객체가 없어 요약할 수 없습니다."}

    narrative_summary = {}

    for obj_id, traj in history.items():
        obj_info = next((o for o in world.objects if o.id == obj_id), None)
        if not obj_info or obj_info.type != 'ball': continue
        
        material = getattr(obj_info.properties, 'material', 'default')
        radius = getattr(obj_info.properties, 'radius', 0.1)
        narrative = f"'{obj_id}'({material})에 대한 시뮬레이션 결과:\n"
        
        if not traj:
            narrative += "  - 움직임 데이터가 없습니다."
            narrative_summary[obj_id] = narrative
            continue

        # 바닥 충돌 및 바운스 감지
        floor_y = 0.0 # 바닥의 높이
        bounces = []
        is_bouncing = False
        for i, (x, y, vx, vy) in enumerate(traj):
            # 공의 바닥이 y=0 근처에 있고, 하강 중일 때를 충돌로 간주
            if y - radius <= floor_y + 0.01 and vy < 0:
                if not is_bouncing: # 새로운 바운스 시작
                    bounces.append({"step": i, "pos": (x, y)})
                    is_bouncing = True
            elif vy > 0: # 상승 중이면 is_bouncing 상태 해제
                is_bouncing = False
        
        # 시나리오 생성
        max_height = max(p[1] for p in traj) - radius
        initial_pos = traj[0]
        final_pos = traj[-1]

        narrative += f"  - 시작 위치: ({initial_pos[0]:.2f}, {initial_pos[1]:.2f}), 최고 높이: {max_height:.2f}m\n"
        
        if not bounces:
            narrative += "  - 이벤트: 바닥에 충돌하지 않았습니다.\n"
        else:
            narrative += f"  - 이벤트: 총 {len(bounces)}번 바닥에 튀었습니다.\n"
            first_bounce = bounces[0]
            dt = world.environment.time_step
            speed = (traj[first_bounce['step']][2]**2 + traj[first_bounce['step']][3]**2)**0.5
            narrative += f"    - 첫 충돌 시간: 약 {first_bounce['step'] * dt:.2f}초\n"
            narrative += f"    - 첫 충돌 속도: 약 {speed:.2f}m/s\n"
            narrative += f"    - 충격음: {get_sound_description(material, speed)}\n"

        narrative += f"  - 최종 위치: ({final_pos[0]:.2f}, {final_pos[1]:.2f})"
        narrative_summary[obj_id] = narrative
        
    return narrative_summary


def plot_trajectories(sim_out: Dict, out_path="trajectory.png"):
    history = sim_out.get("history", {})
    plt.figure()
    for obj_id, traj in history.items():
        if not traj: continue
        xs = [p[0] for p in traj]
        ys = [p[1] for p in traj]
        plt.plot(xs, ys, label=obj_id)
    plt.legend()
    plt.xlabel("x")
    plt.ylabel("y")
    plt.title("Trajectories")
    plt.savefig(out_path, dpi=150)
    plt.close() # 메모리 관리를 위해 그래프 창을 닫아줍니다.
    return out_path