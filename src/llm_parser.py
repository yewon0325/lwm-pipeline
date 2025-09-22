# src/llm_parser.py
import os, json, re
from typing import Dict, Any
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
KEY_PATH = ROOT / "config" / "openai_key.json"
PROMPT_PATH = ROOT / "config" / "prompts.md"

def _load_api_key() -> str:
    if KEY_PATH.exists():
        with KEY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f).get("OPENAI_API_KEY","").strip()
    return os.getenv("OPENAI_API_KEY","").strip()

api_key = _load_api_key()
if not api_key:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. config/openai_key.json 또는 환경변수 확인.")
client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

def _try_json(s: str) -> Any:
    """LLM 출력에서 JSON 코드 블록을 추출하여 파싱합니다."""
    s = s.strip()
    # 마크다운 JSON 블록 추출
    match = re.search(r"```json\s*(\{.*?\})\s*```", s, re.DOTALL)
    if not match:
        # 일반 텍스트에서 JSON 객체 추출
        match = re.search(r"(\{.*?\})", s, re.DOTALL)

    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 파싱 실패: {e}")
            print(f"파싱 시도한 문자열: {json_str}")
            return None
    return None

def natural_language_to_world(user_text: str, world_state: Dict = None) -> Dict:
    """
    LLM을 호출하여 사용자 입력을 JSON으로 변환합니다.
    이전 월드 상태(world_state)를 컨텍스트로 함께 제공할 수 있습니다.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # 이전 상태가 있다면 컨텍스트에 추가하여 대화의 연속성을 유지
    if world_state:
        # 이전 상태에서 actions는 제외하고 전달하여 LLM이 새 액션만 생성하게 함
        state_for_context = world_state.copy()
        state_for_context.pop("actions", None)
        context = f"현재 월드 상태는 다음과 같습니다:\n{json.dumps(state_for_context, ensure_ascii=False, indent=2)}\n\n이 상태를 바탕으로 다음 명령을 처리해주세요:"
        # 시스템 메시지 바로 다음에 현재 상태를 알려주는 것이 더 효과적일 수 있습니다.
        messages.append({"role": "system", "content": context})

    messages.append({"role": "user", "content": user_text})

    comp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"} # JSON 출력 모드 활용
    )
    raw = comp.choices[0].message.content or "{}"
    
    try:
        world_draft = json.loads(raw)
    except json.JSONDecodeError:
        world_draft = {}

    # LLM이 environment를 생성하지 않았을 경우 기본값 채우기
    world_draft.setdefault("environment", {
        "dimensions": "2D",
        "gravity": [0.0, -9.81],
        "time_step": 0.01,
        "duration": 3.0 # 연속 상호작용을 위해 duration을 줄임
    })
    
    return world_draft