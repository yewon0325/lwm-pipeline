# run_cli.py
import json
from src.llm_parser import natural_language_to_world
from src.validate import validate_world
from src.types import World
from src.physics_pymunk import run as run_simulation
from src.reporting import summarize, plot_trajectories

def main():
    print("===== 대화형 물리 시뮬레이션 =====")
    print("명령을 입력하세요. (예: '테이블 위에 탱탱볼을 올려줘')")
    print("종료하려면 '종료' 또는 'exit'를 입력하세요.")
    
    world_state = None  # 초기 월드 상태는 비어있음

    while True:
        try:
            prompt = input("\n[USER] > ")
            if prompt.lower() in ["종료", "exit"]:
                print("시뮬레이션을 종료합니다.")
                break

            # 1) LLM 호출 (이전 상태를 컨텍스트로 제공)
            world_json = natural_language_to_world(prompt, world_state)
            
            print("\n[LLM] > 생성된 World JSON:")
            print(json.dumps(world_json, ensure_ascii=False, indent=2))

            # 2) 스키마 검증 및 Pydantic 모델 변환
            validate_world(world_json)
            world = World.model_validate(world_json)

            # 3) 시뮬레이션 실행
            sim_out = run_simulation(world)

            # 4) 결과 리포팅
            summary = summarize(sim_out) # reporting.py의 summarize를 그대로 사용
            out_path = plot_trajectories(sim_out, out_path="trajectory.png")
            
            print("\n[SYSTEM] > 시나리오 요약:")
            for obj_id, narrative in summary.items():
                print(narrative)
            print(f"궤적 이미지 저장 완료: {out_path}")

            # 5) 다음 루프를 위해 월드 상태 업데이트
            world_state = sim_out["final_state"]

        except Exception as e:
            print(f"\n[ERROR] 오류가 발생했습니다: {e}")
            # 오류 발생 시 월드 상태를 초기화하지 않고 계속 진행
            continue

if __name__ == "__main__":
    main()