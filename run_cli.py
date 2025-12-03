import json
from src.llm_parser import natural_language_to_world, sanitize_world_state, map_action_to_physics
from src.memory_engine import WorldMemory
from src.types import World
from src.physics_pybullet import run_simulation_pybullet
from src.reporting import summarize


def main():
    print("===== 3D 대화형 물리 시뮬레이션 =====")
    memory = WorldMemory()

    # 🔸 이건 굳이 초기화할 필요 없음 (파일에 저장된 상태를 살리고 싶으면)
    #memory.reset()

    while True:
        try:
            prompt = input("\n[USER] > ").strip()
            if prompt.lower() in ["종료", "exit"]:
                print("\n[INFO] 프로그램 종료 중... 메모리 초기화 및 파일 삭제.")
                memory.reset()
                break

            # 0) 직전까지의 누적 월드
            current_state = memory.state or {}
            print("\n[DEBUG] > 현재 메모리(World State, sim 직전):")
            print(json.dumps(current_state, ensure_ascii=False, indent=2))

            # 1) 자연어 → 신규 world dict 생성 (현재 상태를 컨텍스트로)
            new_world = natural_language_to_world(prompt, world_state=current_state)

            # 2) actions를 물리 파라미터로 반영
            actions = new_world.get("actions", []) or []
            objects = new_world.get("objects", []) or []
            obj_map = {o["id"]: o for o in objects if "id" in o}

            for act in actions:
                tid = act.get("target_id")
                if not tid or tid not in obj_map:
                    continue

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

            # 3) 월드 정리
            new_world = sanitize_world_state(new_world)

            print("\n[LLM] > 생성된 World JSON (정제 후):")
            print(json.dumps(new_world, ensure_ascii=False, indent=2))

            # 4) 논리 월드를 메모리에 누적 (환경/객체 추가 등)
            updated = memory.apply_update(new_world)
            print("\n[MEMORY] > LLM 기준 누적된 World State (sim 전):")
            print(json.dumps(updated, ensure_ascii=False, indent=2))

            # 5) Pydantic World 객체 생성
            try:
                world = World.model_validate(updated)
            except Exception as e:
                print(f"[ERROR] World 구조 검증 실패: {e}")
                continue

            # 6) 실제 물리 시뮬레이션
            sim_out = run_simulation_pybullet(world, show_gui=True)

            # 7) 물리 시뮬레이션 결과를 다음 턴의 world_state로 반영
            final_state = sim_out.get("final_state")
            if final_state is not None:
                memory.state = final_state   # RAM 업데이트
                memory.save()               # 파일에도 저장

                print("\n[MEMORY] > 물리 결과까지 반영된 World State (sim 후):")
                print(json.dumps(memory.state, ensure_ascii=False, indent=2))

            # 8) 요약 출력
            summary = summarize(sim_out)
            print("\n[SYSTEM] > 시나리오 요약:")
            for obj_id, narrative in summary.items():
                print(narrative)

        except Exception as e:
            print(f"\n[ERROR] 오류가 발생했습니다: {e}")
            continue


if __name__ == "__main__":
    main()
