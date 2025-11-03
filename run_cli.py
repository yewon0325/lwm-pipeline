import json
from src.llm_parser import natural_language_to_world, sanitize_world_state
from src.memory_engine import WorldMemory
from src.validate import validate_world
from src.types import World
from src.physics_pybullet import run_simulation_pybullet
from src.reporting import summarize
from src.motion_mapper import map_action_to_physics




def main():
    print("===== 3D 대화형 물리 시뮬레이션 =====")
    memory = WorldMemory()

    while True:
        try:
            prompt = input("\n[USER] > ").strip()
            if prompt.lower() in ["종료", "exit"]:
                print("\n[INFO] 프로그램 종료 중... 메모리 초기화 및 파일 삭제.")
                memory.reset()
                break


            current_state = memory.state
            new_world = natural_language_to_world(prompt, world_state=current_state)
            # ✅ actions를 먼저 물리 파라미터로 반영
            actions = new_world.get("actions", [])
            if actions:
                obj_map = {o["id"]: o for o in new_world.get("objects", [])}
                for act in actions:
                    tid = act.get("target_id")
                    if tid and tid in obj_map:
                        phys = map_action_to_physics(act, obj_map[tid])
                        init = obj_map[tid].setdefault("initial_state", {})
                        if "velocity" in phys:
                            init["velocity"] = phys["velocity"]
                        if "angular_velocity" in phys:
                            init["angular_velocity"] = phys["angular_velocity"]
                        # 마찰/반발 등은 상위에 기록
                        for k in ("restitution", "friction", "rolling_friction"):
                            if k in phys:
                                obj_map[tid][k] = phys[k]

            new_world = sanitize_world_state(new_world)

            print("\n[LLM] > 생성된 World JSON:")
            print(json.dumps(new_world, ensure_ascii=False, indent=2))

            updated = memory.apply_update(new_world)
            print("\n[MEMORY] > 누적된 World State:")
            print(json.dumps(updated, ensure_ascii=False, indent=2))

            try:
                world = World.model_validate(new_world)
            except Exception as e:
                print(f"[ERROR] World 구조 검증 실패: {e}")
                continue

            sim_out = run_simulation_pybullet(world, show_gui=True)
            summary = summarize(sim_out)
            print("\n[SYSTEM] > 시나리오 요약:")
            for obj_id, narrative in summary.items():
                print(narrative)

        except Exception as e:
            print(f"\n[ERROR] 오류가 발생했습니다: {e}")
            continue

if __name__ == "__main__":
    main()
