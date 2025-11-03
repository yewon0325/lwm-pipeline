# src/reporting.py
import math
from typing import Dict, Any

def summarize(sim_result: Dict[str, Any]) -> Dict[str, str]:
    """시뮬레이션 결과 요약"""
    world = sim_result["world"]
    final_state = sim_result["final_state"]
    summaries = {}

    for obj in world.objects:
        obj_id = obj.id
        final_obj = next((o for o in final_state["objects"] if o["id"] == obj_id), None)
        if not final_obj:
            continue
        pos = final_obj["initial_state"]["position"]
        summaries[obj_id] = (
            f"'{obj_id}'(default)에 대한 시뮬레이션 결과:\n"
            f"  - 최종 위치: (x={pos[0]:.2f}, y={pos[1]:.2f}, z={pos[2]:.2f})"
        )

    return summaries
