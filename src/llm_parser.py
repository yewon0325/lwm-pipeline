import os
import json
import re
from typing import Dict, Any
from pathlib import Path
from openai import OpenAI

# --- 설정 및 초기화 ---
ROOT = Path(__file__).resolve().parents[1]
KEY_PATH = ROOT / "config" / "openai_key.json"
PROMPT_PATH = ROOT / "config" / "prompts.md"

def _load_api_key() -> str:
    """config 파일 또는 환경 변수에서 OpenAI API 키를 로드합니다."""
    if KEY_PATH.exists():
        with KEY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f).get("OPENAI_API_KEY", "").strip()
    return os.getenv("OPENAI_API_KEY", "").strip()

api_key = _load_api_key()
if not api_key:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. config/openai_key.json 또는 환경변수를 확인하세요.")

client = OpenAI(api_key=api_key)
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


# --- 핵심 함수 ---
def natural_language_to_world(user_text: str, world_state: Dict = None) -> Dict:
    """
    LLM을 호출하여 사용자의 자연어 명령을 3D 시뮬레이션용 JSON으로 변환합니다.
    이전 월드 상태(world_state)를 대화의 문맥으로 함께 제공할 수 있습니다.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 이전 상태가 있다면, LLM에게 현재 상태를 알려주어 대화의 연속성을 유지합니다.
    if world_state:
        state_for_context = world_state.copy()
        state_for_context.pop("actions", None)  # 이전 액션은 제외하고 전달
        context_message = f"현재 월드 상태는 다음과 같습니다:\n{json.dumps(state_for_context, ensure_ascii=False, indent=2)}\n\n이 상태를 바탕으로 다음 명령을 처리해주세요:"
        messages.append({"role": "system", "content": context_message})

    messages.append({"role": "user", "content": user_text})

    # OpenAI API 호출
    comp = client.chat.completions.create(
        model="gpt-4o",  # gpt-4o 모델 사용
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"}  # JSON 강제
    )

    raw_response = comp.choices[0].message.content or "{}"

    try:
        world_draft = json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"[ERROR] LLM의 응답이 유효한 JSON이 아닙니다: {e}")
        print(f"LLM 원본 응답: {raw_response}")
        return {}

    # 기본값 채우기
    world_draft.setdefault("environment", {
        "gravity": [0.0, 0.0, -9.81],
        "time_step": 0.01,
        "duration": 5.0
    })

    # 정제 및 보정
    return sanitize_world_state(world_draft)



# --- 환경 및 객체 정제 함수 ---
def sanitize_world_state(world: dict) -> dict:
    """LLM이 만든 world JSON을 정제하고 물리 시뮬레이션 기본값을 보정"""
    
    def fix_vector3(v, default=[0.0, 0.0, 0.0]):
        if not isinstance(v, list) or len(v) != 3:
            return list(default)
        return [float(x) if x is not None else 0.0 for x in v]

    # --- 객체 정제 ---
    for obj in world.get("objects", []):
        init = obj.get("initial_state", {})
        init["position"] = fix_vector3(init.get("position", [0, 0, 0]))
        init["velocity"] = fix_vector3(init.get("velocity", [0, 0, 0]))

        if "angular_velocity" in init:
            init["angular_velocity"] = fix_vector3(init["angular_velocity"])

        if init.get("mass") is None:
            init["mass"] = 1.0

        obj["initial_state"] = init

    # --- 환경 정제 ---
    env = world.get("environment", {}) or {}
    env["gravity"] = fix_vector3(env.get("gravity", [0, 0, -9.81]))

    # 바람
    wind = env.get("wind", {})
    wind["direction"] = fix_vector3(wind.get("direction", [0, 0, 0]))
    wind["strength"] = float(wind.get("strength", 0.0))
    env["wind"] = wind

    # 공기 관련 물리값 보정
    env.setdefault("temperature", 298.0)        # K
    env.setdefault("pressure", 101325.0)        # Pa
    env.setdefault("air_density", 1.225)        # kg/m³
    env.setdefault("drag_coefficient", 0.47)
    env.setdefault("humidity", 0.5)

    # 시간 관련
    env.setdefault("time_step", 0.01)
    env.setdefault("duration", 5.0)

    world["environment"] = env

    # 액션 누락 보정
    if "actions" not in world:
        world["actions"] = []

    return world

#motion action을 물리 파라미터로 매핑(통합)

def map_action_to_physics(action: dict, obj: dict) -> dict:
    import math
    t = (action.get("type") or "").lower()
    mag = float(action.get("magnitude", 1.0))
    dx, dy, dz = [float(d) for d in action.get("direction", [0, 0, 0])]

    cross_section = obj.get("cross_section", 0.0314)
    r = math.sqrt(max(cross_section, 1e-6) / math.pi)

    if t == "throw": # 던지기
        return {"velocity": [dx*mag*5, dy*mag*5, dz*mag*5],
                "angular_velocity":[dy*2, -dx*2,0], "restitution":0.6}

    if t == "roll": # 구르기
        vx, vy = dx*mag*2, dy*mag*2
        return {"velocity":[vx,vy,0], "angular_velocity":[0,(vx/r) if r>0 else 0,0],
                "rolling_friction":0.02}

    if t == "stop": # 정지
        return {"velocity":[0,0,0], "angular_velocity":[0,0,0]}
    
    if t == "vacuum": # 진공 상태
        return {
            "_env_update": {
                "air_density": 0.0,
                "drag_coefficient": 0.0,
                "wind": {"direction":[0,0,0], "strength":0.0}
            }
    }
    
    if t == "drop": #낙하
        return {
            "velocity": [0.0, 0.0, -0.1],  # 살짝만 음수, 중력에 의해 가속됨
            "restitution": 0.3
        }

    return {}
