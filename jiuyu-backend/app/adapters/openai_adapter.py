# app/adapters/openai_adapter.py
from .base import BaseDrawingAdapter
import os
from openai import AsyncOpenAI

class OpenAIAdapter(BaseDrawingAdapter):
    async def generate_image(self, request, model_config):
        # 1. 整理提示词
        final_prompt = request.prompt
        if request.style != "none":
            final_prompt = f"3D render, octane render, unreal engine 5, ray tracing, cinematic lighting, high detail, {request.prompt}"

        # 2. 呼叫标准网关客户端
        ai_client = AsyncOpenAI(
            api_key=os.getenv("AI_API_KEY", "sk-dummy-key-for-test"),
            base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1") 
        )

        # 3. 发送极其标准的请求
        response = await ai_client.images.generate(
            model=request.model,
            prompt=final_prompt,
            size="1024x1024", # 随便塞个参数骗过原生SDK
            extra_body={
                "aspectRatio": request.aspectRatio,
                "imageSize": request.imageSize,
                "urls": request.urls
            }
        )
        return response.data[0].url