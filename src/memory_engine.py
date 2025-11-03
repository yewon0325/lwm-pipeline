# src/memory_engine.py
import json
import os
from pathlib import Path
from typing import Dict, Any

class WorldMemory:
    """LWM-style memory system: keeps and updates a persistent world state."""
    
    def __init__(self, memory_path: str = "data/world_state.json"):
        self.path = Path(memory_path)
        if not self.path.exists():
            self.state = {"objects": [], "environment": {}}
            self.save()
        else:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
    
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def apply_update(self, new_state: Dict[str, Any]):
        """Merge new state into memory (object add/modify/remove)."""
        if "objects" in new_state:
            existing = {obj["id"]: obj for obj in self.state.get("objects", [])}
            for obj in new_state["objects"]:
                existing[obj["id"]] = obj
            self.state["objects"] = list(existing.values())
        
        if "environment" in new_state:
            self.state["environment"] = new_state["environment"]
        
        self.save()
        return self.state

    def reset(self):
        """Reset memory and delete saved file."""
        self.state = {"objects": [], "environment": {}}
        if self.path.exists():
            try:
                os.remove(self.path)
                print("[INFO] memory file removed successfully.")
            except Exception as e:
                print(f"[WARN] memory file could not be removed: {e}")
