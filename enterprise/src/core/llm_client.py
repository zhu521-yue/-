from openai import OpenAI
# from langfuse.decorators import observe (v4 不兼容，部署时禁用)
from dotenv import load_dotenv
import os
from loguru import logger
from pathlib import Path

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
deepseek_client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL"),
    timeout=60,
    max_retries=3,
)
gpt_client = None
if os.getenv("GPT_API_KEY"):
    gpt_client = OpenAI(
        api_key=os.getenv("GPT_API_KEY"),
        base_url=os.getenv("GPT_BASE_URL"),
        timeout=60,
        max_retries=3,
    )

MODEL_CONFIG = {
    "deepseek": {"client": deepseek_client, "model": "deepseek-chat"},
    "gpt": {"client": gpt_client, "model": os.getenv("GPT_MODEL", "gpt-5.5")},
}

# @observe(as_type="generation")
def chat(system_prompt: str, user_message: str, model: str = "deepseek") -> str:
    """
    调用 LLM 生成回复。
    参数：
        model: "deepseek"（默认，便宜快速）或 "gpt"（复杂任务）
    """
    config = MODEL_CONFIG.get(model, MODEL_CONFIG["deepseek"])
    client = config["client"]
    model_name = config["model"]
    # 如果 GPT 未配置，fallback 到 DeepSeek
    if client is None:
        client = deepseek_client
        model_name = "deepseek-chat"
        logger.warning(f"[LLM] {model} 未配置，fallback 到 deepseek")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        result = response.choices[0].message.content
        logger.info(f"LLM response ({model_name}): {result[:50]}...")
        return result
    except Exception as e:
        # DeepSeek 失败时尝试 fallback 到 GPT
        if model == "deepseek" and gpt_client:
            logger.warning(f"[LLM] DeepSeek 失败: {e}, fallback 到 GPT")
            return chat(system_prompt, user_message, model="gpt")
        raise
if __name__ == "__main__":
    system_prompt = """
    你是一个智能教育系统中的AI教学助手。
    你的任务是根据学生的问题和学习水平，生成符合要求的教育内容。
    """
    user_message = "我想学习方程"
    result = chat(system_prompt,user_message)
    print(result)