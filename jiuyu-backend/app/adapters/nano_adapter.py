# app/adapters/nano_adapter.py
from .base import BaseDrawingAdapter
import httpx
import json
import os

class NanoAdapter(BaseDrawingAdapter):
    async def generate_image(self, request, model_config):
        final_prompt = request.prompt
        if request.style != "none":
            final_prompt = f"3D render, octane render, unreal engine 5, ray tracing, cinematic lighting, high detail, {request.prompt}"

        # 直连配置
        direct_url = f"{os.getenv('GRSAI_DIRECT_URL', 'https://grsai.dakka.com.cn').rstrip('/')}/v1/draw/nano-banana"
        key = os.getenv('GRSAI_DIRECT_KEY')

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        # Nano 专属的奇葩参数组装
        payload = {
            "model": request.model,
            "prompt": final_prompt,
            "urls": request.urls,
            "aspectRatio": request.aspectRatio,
            "imageSize": request.imageSize
        }

        # 异步解析 SSE 数据流
        async with httpx.AsyncClient(timeout=300.0, verify=False) as client:
            res = await client.post(direct_url, json=payload, headers=headers)
            raw_text = res.text
            image_url = None
            
            for line in raw_text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    json_str = line[5:].strip()
                    if not json_str or json_str == "[DONE]":
                        continue
                    try:
                        data_obj = json.loads(json_str)
                        current_status = data_obj.get("status")
                        if current_status in ["succeeded", "success"]:
                            results_list = data_obj.get("results")
                            if results_list and isinstance(results_list, list) and len(results_list) > 0:
                                image_url = results_list[0].get("url")
                            else:
                                image_url = data_obj.get("url") or data_obj.get("image_url")
                            if image_url:
                                break
                    except Exception:
                        continue
                        
            if not image_url:
                raise Exception(f"未能提取到链接，原始返回: {raw_text[:200]}")
            
            return image_url