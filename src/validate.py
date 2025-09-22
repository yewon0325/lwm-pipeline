import json, jsonschema, pathlib

def validate_world(world_json: dict):
    schema = json.loads(pathlib.Path("config/schema_world.json").read_text())
    jsonschema.validate(instance=world_json, schema=schema)
    return True
