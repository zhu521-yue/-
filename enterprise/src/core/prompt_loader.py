import yaml
from pathlib import Path
from loguru import logger
import json
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def load_prompt(name:str)->dict:
    file_path = PROMPTS_DIR / f"{name}.yaml"
    with open(file_path,"r",encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    parent_name = data.pop("inherits",None)
    if parent_name:
        parent_data = load_prompt(parent_name)
    else:
        parent_data = {}
    merged = {**parent_data,**data}
    if "constraints" in parent_data and "constraints" in data:
          merged["constraints"] = parent_data["constraints"] + data["constraints"]

    logger.info(f"Loaded prompt: {name}")
    return merged
if __name__ == "__main__":
    result = load_prompt("tutor")
    print(result)