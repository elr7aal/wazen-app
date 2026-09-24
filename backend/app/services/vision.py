import json
import os
from typing import Any
import httpx

DEFAULT_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-6-astra")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

SYSTEM_PROMPT = """You are WAZEN food image analysis.
Analyze only visible food and drink. Return strict JSON only, no markdown:
{
  \"description_ar\": \"short Arabic description\",
  \"items\": [{\"name\":\"food item name\",\"name_ar\":\"Arabic food item name\",\"estimated_quantity\":1,\"estimated_unit\":\"serving\",\"estimated_calories\":0,\"estimated_protein_g\":0,\"estimated_carbs_g\":0,\"estimated_fat_g\":0,\"confidence\":0.0}],
  \"overall_confidence\": 0.0,
  \"needs_review\": true
}
All nutrition values are visual estimates. Never claim exact branded nutrition unless visible evidence supports it.
If uncertain, lower confidence. Never diagnose or treat health conditions.
"""

def provider_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))

def re_fence(text: str) -> str:
    lines=text.splitlines()
    if lines and lines[0].startswith("```"):
        lines=lines[1:]
    if lines and lines[-1].strip()=="```":
        lines=lines[:-1]
    return "\n".join(lines).strip()

def _extract_output_text(payload: dict[str, Any]) -> str:
    parts=[]
    for item in payload.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if isinstance(content, dict) and content.get("type")=="output_text":
                parts.append(content.get("text",""))
    return "\n".join(x for x in parts if x).strip()

def analyze_food_image(image_base64: str, caption: str | None = None) -> dict[str, Any]:
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return {"provider":"NOT_CONFIGURED","model":None,"result":None}
    prompt=SYSTEM_PROMPT
    if caption:
        prompt += f"\nUser-provided context: {caption}"
    body={"model":DEFAULT_MODEL,"input":[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":f"data:image/jpeg;base64,{image_base64}","detail":"auto"}]}]}
    response=httpx.post(OPENAI_RESPONSES_URL,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json=body,timeout=45.0)
    response.raise_for_status()
    payload=response.json()
    raw=_extract_output_text(payload)
    if raw.startswith("```"):
        raw=re_fence(raw)
    try:
        parsed=json.loads(raw)
    except json.JSONDecodeError:
        parsed={"description_ar":raw[:500],"items":[],"overall_confidence":0.0,"needs_review":True,"parse_warning":"VISION_RESPONSE_NOT_JSON"}
    return {"provider":"OPENAI_RESPONSES","model":DEFAULT_MODEL,"result":parsed}
