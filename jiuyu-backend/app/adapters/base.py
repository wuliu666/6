# app/adapters/base.py
class BaseDrawingAdapter:
    """所有翻译官的终极基类，必须遵守这个规矩"""
    async def generate_image(self, request, model_config):
        raise NotImplementedError("子类必须实现 generate_image 方法！")