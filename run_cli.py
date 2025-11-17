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

    # ✅ 이전 실행에서 남아 있던 파일/상태가 있다면 여기서 초기화
    memory.reset()   # WorldMemory 내부에서 state를 적절한 초기 dict로 세팅한다고 가정

    while True:
        try:
            prompt = input("\n[USER] > ").strip()
            if prompt.lower() in ["종료", "exit"]:
                print("\n[INFO] 프로그램 종료 중... 메모리 초기화 및 파일 삭제.")
                memory.reset()
                break

            # 직전까지의 누적 월드 (None일 수도 있으니 dict로 보정)
            current_state = memory.state or {}

            # 1) 자연어 → 신규 world dict 생성 (현재 상태를 컨텍스트로)
            new_world = natural_language_to_world(prompt, world_state=current_state)

            # 2) actions를 물리 파라미터로 반영
            actions = new_world.get("actions", [])
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

            print("\n[LLM] > 생성된 World JSON:")
            print(json.dumps(new_world, ensure_ascii=False, indent=2))

            # 4) 논리 월드를 메모리에 누적 (환경/객체 추가 등)
            updated = memory.apply_update(new_world)
            print("\n[MEMORY] > 누적된 World State:")
            print(json.dumps(updated, ensure_ascii=False, indent=2))

            # 5) Pydantic World 객체 생성
            try:
                world = World.model_validate(updated)
            except Exception as e:
                print(f"[ERROR] World 구조 검증 실패: {e}")
                continue

            # 6) 실제 물리 시뮬레이션
            sim_out = run_simulation_pybullet(world, show_gui=True)

            # ✅ 7) 물리 시뮬레이션 결과를 다음 턴의 world_state로 반영
            final_state = sim_out.get("final_state")
            if final_state is not None:
                memory.state = final_state  # 다음 프롬프트에서 이 상태를 베이스로 사용

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
