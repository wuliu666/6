from fastapi import FastAPI, Depends, HTTPException, File, Form, UploadFile, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from passlib.context import CryptContext
import os
import uuid
import time
import shutil
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware # 👈 新增这一行！
import jwt
from datetime import datetime, timedelta
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
import re
from typing import List, Optional, Dict
import requests
# 💡 引入我们的翻译官部门
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.nano_adapter import NanoAdapter

# 引入腾讯云 COS SDK
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from app.core.database import SessionLocal
from app.models import base as models

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME", "九雨创作台"),
    description="九雨团队专属创作平台全新后端 API",
    version="1.0.0"
)



# 开启静态文件代理：把本地的 uploads 文件夹暴露到 /uploads 网址下
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 👈 新增下面这一大段跨域配置
app.add_middleware(
    CORSMiddleware,
    # 把粗暴的 ["*"] 换成你前端真实的地址
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 初始化 AI 客户端，加上默认假钥匙防止启动崩溃
ai_client = AsyncOpenAI(
    api_key=os.getenv("AI_API_KEY", "sk-dummy-key-for-test"), # 👈 这里加了备用字符串
    base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1") 
)

# 定义前端传过来的画图参数模板
class DrawRequest(BaseModel):
    prompt: str
    model: str
    channel_name: str = "未分类"  # 👈 前端画图时必须带上文件夹名
    aspectRatio: Optional[str] = "1:1"
    imageSize: Optional[str] = "1K"
    style: Optional[str] = "none"
    urls: Optional[List[str]] = []
    
# 💡 新增：文件夹创建请求包
class ChannelFolderRequest(BaseModel):
    name: str
    base_url: str = ""
    api_key: str = ""
    
# 1. 确保接收包裹允许前端传空值
class ConfigUpdateRequest(BaseModel):
    model_config = {"protected_namespaces": ()} 
    id: Optional[int] = None
    model_name: str
    channel_name: str = "未分类"          
    api_protocol: str = "standard_openai" 
    is_image_model: bool = True
    supported_ratios: Optional[list] = []
    supported_sizes: Optional[list] = []

 # 💡 新增：用于批量更新（如批量移动渠道、批量改协议）的请求体
class BulkUpdateRequest(BaseModel):
    ids: List[int] # 前端传过来的模型 ID 列表
    channel_name: Optional[str] = None
    api_protocol: Optional[str] = None

# 💡 新增：用于批量删除的请求体
class BulkDeleteRequest(BaseModel):
    ids: List[int]





# 🛡️ 密码加密机：使用极其安全的 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 📦 数据校验图纸（确保前端传来的数据格式是对的） ---
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    invite_code: str

# ----------------- 🔌 API 接口 -----------------

@app.get("/")
async def root():
    return {"message": "🎉 恭喜！九雨创作台后端正常运行！"}

@app.post("/admin/generate-invite", tags=["管理员操作"], summary="一键生成专属邀请码")
def generate_invite_code(db: Session = Depends(get_db)):
    random_str = str(uuid.uuid4())[:8].upper()
    code_str = f"JIUYU-{random_str}"
    
    new_code = models.InvitationCode(code=code_str)
    db.add(new_code)
    db.commit()
    
    return {
        "status": "success",
        "message": "邀请码生成成功！赶快发给你的团队成员吧！",
        "code": code_str
    }

@app.post("/auth/register", tags=["用户认证"], summary="使用邀请码注册新账号")
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    团队成员通过填入账号、密码和邀请码来注册。
    """
    # 1. 检查邀请码是否存在且没被用过
    db_code = db.query(models.InvitationCode).filter(
        models.InvitationCode.code == request.invite_code,
        models.InvitationCode.is_used == False
    ).first()
    
    if not db_code:
        # 如果邀请码不对，直接无情拒绝
        raise HTTPException(status_code=400, detail="无效或已使用的邀请码！")

    # 2. 检查用户名是否已经被别人抢注了
    existing_user = db.query(models.User).filter(models.User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已被注册，换一个吧！")

    # 3. 密码加密（绝对不能存明文！）
    hashed_password = pwd_context.hash(request.password)

    # 4. 创建新用户
    # 我们默认第一个注册的人（或者特定邀请码）是 admin，这里简单起见，统一先给 member 角色
    new_user = models.User(
        username=request.username,
        password_hash=hashed_password,
        role="member",
        balance=100.0  # 注册送 100 额度！
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user) # 获取刚生成的 user_id

    # 5. 销毁（标记）邀请码，防止被二次使用，并记录是谁用的
    db_code.is_used = True
    db_code.used_by_user_id = new_user.id
    db.commit()

    return {
        "status": "success",
        "message": f"欢迎加入九雨创作台，{new_user.username}！注册成功！"
    }

# --- 📦 登录请求格式 ---
class LoginRequest(BaseModel):
    username: str
    password: str

# 密钥（未来可以移到 .env 里，现在先写死测试）
JWT_SECRET = "jiuyu_super_secret_key_2026"

# 🛡️ 守卫 1号：检查通行证真伪
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未携带合法通行证，拒绝访问！")
    
    token = authorization.split(" ")[1] # 提取出真实的 token 字符串
    try:
        # 尝试用我们的专属密钥解开它
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload # 如果解开成功，这里面就包含了 {"sub": "用户ID", "role": "角色"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="通行证已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="伪造的通行证，抓起来！")

# 🛡️ 守卫 2号：专门拦截非管理员
def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="越权警告：后端已拦截！你的真实身份不是管理员！")
    return current_user

@app.post("/auth/login", tags=["用户认证"], summary="🔑 用户登录与签发 Token")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 1. 在数据库里找这个用户
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 2. 校验密码
    if not pwd_context.verify(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 3. 密码正确，开始签发 VIP 通行证 (有效期设为 7 天)
    expire = datetime.utcnow() + timedelta(days=7)
    # 把用户 ID 和角色藏进通行证里
    to_encode = {"sub": str(user.id), "role": user.role, "exp": expire} 
    token = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

    # 4. 把通行证发给前端
    return {
        "message": "登录成功！欢迎回来。",
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }

@app.get("/admin/users", tags=["管理员操作"], summary="👀 查看所有已注册用户")
def get_all_users(db: Session = Depends(get_db)):
    """上帝视角：查看数据库里究竟有哪些人注册成功了"""
    users = db.query(models.User).all()
    return {
        "total": len(users),
        "users": [
            {"id": u.id, "username": u.username, "role": u.role, "balance": u.balance} 
            for u in users
        ]
    }

@app.get("/admin/invites", tags=["管理员操作"], summary="👀 查看所有邀请码状态")
def get_all_invites(db: Session = Depends(get_db)):
    """上帝视角：查看所有的邀请码到底是没用过，还是被谁用掉了"""
    invites = db.query(models.InvitationCode).all()
    return {
        "total": len(invites),
        "invites": [
            {"code": i.code, "is_used": i.is_used, "used_by_user_id": i.used_by_user_id} 
            for i in invites
        ]
    }


# --- 📦 新增的 API 渠道数据格式要求 ---
class ChannelCreateRequest(BaseModel):
    name: str           # 比如："Gemini 官方通道" 或 "OneAPI 备用池"
    model_name: str     # 比如："gemini-pro" 或 "gpt-4"
    api_key: str        # 你的 sk-xxxxx 密钥
    base_url: str = None # 中转地址，原生接口可以不填

# ----------------- 🔌 AI 网关控制台接口 -----------------

@app.get("/admin/channels", tags=["AI网关管理"], summary="🎛️ 查看所有 AI 渠道配置")
def get_all_channels(db: Session = Depends(get_db)):
    """上帝视角：查看当前系统中配置了哪些大模型和 Key"""
    channels = db.query(models.ApiChannel).all()
    return {"total": len(channels), "channels": channels}

@app.post("/admin/channels", tags=["AI网关管理"], summary="➕ 新增一个 AI 渠道")
def add_channel(request: ChannelCreateRequest, db: Session = Depends(get_db)):
    """在后台随时添加新的模型或新的 Key"""
    new_channel = models.ApiChannel(
        name=request.name,
        model_name=request.model_name,
        api_key=request.api_key,
        base_url=request.base_url,
        is_active=True # 默认开启
    )
    db.add(new_channel)
    db.commit()
    return {"status": "success", "message": f"渠道【{request.name}】添加成功！"}

@app.put("/admin/channels/{channel_id}/toggle", tags=["AI网关管理"], summary="🔛 一键开启/关闭某渠道")
def toggle_channel(channel_id: int, db: Session = Depends(get_db)):
    """遇到某个 Key 欠费了？点一下直接切断，防止前端一直报错"""
    channel = db.query(models.ApiChannel).filter(models.ApiChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="找不到这个渠道")
    
    channel.is_active = not channel.is_active # 状态反转
    db.commit()
    
    status_text = "已开启" if channel.is_active else "已停用"
    return {"status": "success", "message": f"渠道【{channel.name}】{status_text}！"}

@app.delete("/admin/channels/{channel_id}", tags=["AI网关管理"], summary="🗑️ 彻底删除某渠道")
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """彻底废弃不用的 Key"""
    channel = db.query(models.ApiChannel).filter(models.ApiChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="找不到这个渠道")
    
    db.delete(channel)
    db.commit()
    return {"status": "success", "message": f"渠道已彻底删除！"}

import httpx
from fastapi.responses import StreamingResponse
import json

# --- 📦 对话请求的数据格式 ---
class ChatMessage(BaseModel):
    role: str       # "user" 或 "assistant" 或 "system"
    content: str    # 聊天内容

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    # 如果前端不传模型名字，我们就在后台随便挑一个可用的
    model: str = None 

# ----------------- 💬 核心对话引擎 -----------------

@app.post("/chat/completions", tags=["核心业务"], summary="💬 核心 AI 对话接口 (支持流式输出)")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """接收前端问题，自动寻找可用渠道并返回 AI 的流式回答"""
    
    # 1. 智能路由：去数据库找一个处于“开启状态”的渠道
    # 如果前端指定了模型，就找对应的；如果没指定，就随便抓一个开启的
    query = db.query(models.ApiChannel).filter(models.ApiChannel.is_active == True)
    if request.model:
        query = query.filter(models.ApiChannel.model_name == request.model)
    
    channel = query.first()
    
    if not channel:
        raise HTTPException(status_code=500, detail="💥 后台没有可用的 AI 渠道，请联系管理员！")

    # 2. 组装请求包 (完全兼容 OneAPI / OpenAI 格式)
    headers = {
        "Authorization": f"Bearer {channel.api_key}",
        "Content-Type": "application/json"
    }
    
    # 将前端传来的 Pydantic 模型列表转换为字典列表
    messages_dict = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    payload = {
        "model": channel.model_name,
        "messages": messages_dict,
        "stream": True  # ⚡ 开启打字机流式输出
    }
    
    # 确保 base_url 末尾没有多余的斜杠，并拼接上标准路径
    # 如果是原生 OpenAI，通常不需要改；如果是 OneAPI，需要带上 /v1
    base_url = channel.base_url.rstrip('/') if channel.base_url else "https://api.openai.com/v1"
    url = f"{base_url}/chat/completions"

    # 3. 建立异步连接并实时透传给前端
    async def stream_generator():
        # 这里使用 httpx 发起异步请求，绝对不会阻塞你的服务器！
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                    # 如果渠道里的 Key 过期了或填错了
                    if response.status_code != 200:
                        error_msg = await response.aread()
                        yield f"data: {json.dumps({'error': 'AI 网关请求失败，请检查后台配置', 'details': error_msg.decode()})}\n\n"
                        return
                    
                    # 🚀 见证奇迹：将 AI 吐出的每一个字，原封不动地转发给前端
                    async for chunk in response.aiter_text():
                        yield chunk
            except Exception as e:
                yield f"data: {json.dumps({'error': '连接 AI 网关时发生异常', 'details': str(e)})}\n\n"

    # 使用 FastAPI 特有的 StreamingResponse 保持长连接
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# ----------------- 📁 素材与存储双擎系统 -----------------

# 1. 初始化腾讯云 COS 客户端 (自动读取你刚才在 .env 里写的机密配置)
cos_config = CosConfig(
    Region=os.getenv("COS_REGION"),
    SecretId=os.getenv("COS_SECRET_ID"),
    SecretKey=os.getenv("COS_SECRET_KEY")
)
cos_client = CosS3Client(cos_config)



@app.post("/assets/upload", tags=["素材管理"], summary="📁 智能双擎上传 (自动分拣云端/本地)")
async def upload_asset(
    file: UploadFile = File(..., description="你要上传的图片/文件"),
    asset_type: str = Form(..., description="填 'team' (团队素材) 或 'personal' (个人私密)"),
    user_id: int = Form(..., description="上传者的用户 ID"),
    prompt: Optional[str] = Form(""),   
    ratio: Optional[str] = Form("1:1"),
    size: Optional[str] = Form(""),     # 💡 补漏：接收前端传来的尺寸
    model: Optional[str] = Form(""),    # 💡 补漏：接收前端传来的模型
    style: Optional[str] = Form("none"),
    db: Session = Depends(get_db)
):



    """
    核心分拣逻辑：
    - team -> 传到腾讯云 COS
    - personal -> 存到本地服务器 /uploads/personal/user_{id}/ 目录下
    """
    # 获取文件后缀名 (比如 .png, .jpg)
    ext = file.filename.split(".")[-1]
    # 生成一个绝对不会重复的文件名 (时间戳 + 随机码)
    unique_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    
    file_url = ""
    storage_type = ""

    # 💡 绝杀技 2：先统一把图片读入内存，并瞬间提取“极小高斯模糊骨架代码”
    contents = await file.read()
    blur_hash_str = ""
    try:
        from PIL import Image
        import io
        import base64
        # 将内存中的字节转为图片
        img = Image.open(io.BytesIO(contents)).convert('RGB')
        img.thumbnail((16, 16)) # 极限压缩到只有 16x16 像素
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=40)
        # 转成极短的 Base64 字符串
        blur_hash_str = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"骨架代码提取失败: {e}")

    # 🚀 分拣通道 A：团队素材 -> 上云！
    if asset_type == "team":
        bucket = os.getenv("COS_BUCKET")
        if not bucket:
            raise HTTPException(status_code=500, detail="COS_BUCKET 未配置！")
            
        cos_key = f"team_assets/{unique_name}"
        
        try:
            # 💡 直接使用刚才内存里的 contents
            cos_client.put_object(Bucket=bucket, Body=contents, Key=cos_key)
            file_url = f"https://{bucket}.cos.{os.getenv('COS_REGION')}.myqcloud.com/{cos_key}"
            storage_type = "TENCENT_COS"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"腾讯云上传失败: {str(e)}")

    # 🏠 分拣通道 B：个人素材 -> 存本地，绝对隔离！
    elif asset_type == "personal":
        local_base_dir = "uploads/personal"
        user_folder = f"{local_base_dir}/user_{user_id}"
        os.makedirs(user_folder, exist_ok=True) 
        
        local_path = f"{user_folder}/{unique_name}"
        
        # 💡 直接把刚才内存里的 contents 写入硬盘，抛弃缓慢的 copyfileobj
        with open(local_path, "wb") as buffer:
            buffer.write(contents)
            
        file_url = f"/{local_path}" 
        storage_type = "LOCAL"
        
    else:
        raise HTTPException(status_code=400, detail="asset_type 只能是 team 或 personal")

     # 💾 核心修改：大厂标准做法！图片留云端，参数进数据库，绝对并发安全！
    new_asset = models.Asset(
            user_id=user_id,
            storage_type=storage_type,
            file_url=file_url,
            asset_type=asset_type,
            prompt=prompt,
            ratio=ratio,
            size=size,      
            model=model,    
            style=style,
            blur_hash=blur_hash_str # 💡 这里千万别忘了存进数据库！！
        )
    db.add(new_asset)
    db.commit()

    return {
        "status": "success", 
        "message": "文件上传并入库成功！",
        "storage": storage_type,
        "url": file_url
    }
    

@app.get("/assets", tags=["素材管理"], summary="🖼️ 获取历史素材列表")
def get_assets(asset_type: str, user_id: int, db: Session = Depends(get_db)):
    """
    前端刷新页面时，来这里拉取以前上传过的所有图片
    """
    # 核心查询逻辑：如果是团队素材，大家都能看；如果是个人素材，只看自己的
    query = db.query(models.Asset).filter(models.Asset.asset_type == asset_type)
    
    if asset_type == "personal":
        query = query.filter(models.Asset.user_id == user_id)
        
    # 按照 ID 倒序排列（最新上传的排在最前面）
    assets = query.order_by(models.Asset.id.desc()).all()

    # 整理返回数据，顺便把本地图片的网址补全
    
    result = []
    for a in assets:
        full_url = f"http://127.0.0.1:8000{a.file_url}" if a.storage_type == "LOCAL" else a.file_url
        
        # 💡 直接从数据库对象 a 中提取文本属性，0 延迟，不会撑爆服务器硬盘
        result.append({
            "id": a.id,
            "url": full_url,
            "storage": a.storage_type,
            "prompt": a.prompt or "",
            "ratio": a.ratio or "1:1",
            "size": a.size or "",       
            "model": a.model or "",     
            "style": a.style or "none",
            "blur_hash": a.blur_hash or ""  # 💡 绝杀技2：把骨架代码吐给前端
        })
    return {"status": "success", "assets": result}

@app.delete("/assets/{asset_id}", tags=["素材管理"], summary="🗑️ 管理员专属：彻底粉碎素材")
def delete_asset(
    asset_id: int, 
    db: Session = Depends(get_db),
    # 👈 核心物理防御在这里！只要加了这行，没有合法 admin 通行证的人绝对进不来！
    admin_user: dict = Depends(require_admin) 
):
    # ... 下面的删除逻辑完全不用动 ...
    # 1. 在案卷中找到这个目标
    asset = db.query(models.Asset).filter(models.Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在或已被删除")

    try:
        # 2. 执行物理级毁灭
        if asset.storage_type == "LOCAL":
            # 把本地路径前面的 '/' 切掉，拼成真实相对路径
            local_path = asset.file_url.lstrip('/')
            if os.path.exists(local_path):
                os.remove(local_path) # 🗡️ 直接从硬盘抹除！
                
        elif asset.storage_type == "TENCENT_COS":
            bucket = os.getenv("COS_BUCKET")
            # 提取云端的关键标识 Key，精准狙击
            if ".com/" in asset.file_url:
                cos_key = asset.file_url.split(".com/")[1]
                cos_client.delete_object(Bucket=bucket, Key=cos_key) # 🗡️ 从云端彻底抹除！

        # 3. 最后，从数据库档案中除名
        db.delete(asset)
        db.commit()
        
        return {"status": "success", "message": "素材已彻底从这个宇宙中抹除！"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"粉碎失败: {str(e)}")
    
    

@app.post("/drawing/generate", tags=["AI 创作"], summary="🚀 智能双引擎：路由表分发")
async def generate_image(request: DrawRequest, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    
    try:
        # ==========================================
        # 👑 核心架构：双重定位（模型名字 + 渠道），绝对不会撞名
        # ==========================================
        model_config = db.query(models.ModelConfig).filter(
            models.ModelConfig.model_name == request.model,
            models.ModelConfig.channel_name == request.channel_name
        ).first()
        
        # 1. 严格获取协议（如果没有在数据库档案里，默认它是一个符合标准 OpenAI 协议的模型）
        protocol = model_config.api_protocol if model_config else "standard_openai"

        # 2. 🏢 翻译官注册表：只认协议，不认名字！
        ADAPTER_REGISTRY = {
            "standard_openai": OpenAIAdapter(),
            "grsai_nano": NanoAdapter()
            # 💡 以后如果遇到必须轮询的奇葩 Nano，直接加一行: "polling_nano": PollingNanoAdapter()
        }

        adapter = ADAPTER_REGISTRY.get(protocol)
        if not adapter:
            raise HTTPException(status_code=500, detail=f"系统缺少协议为 [{protocol}] 的翻译插件！")

        print(f"⚡ 正在通过【{adapter.__class__.__name__}】处理 [{request.model}] 的生图请求 (协议: {protocol})...")

        adapter = ADAPTER_REGISTRY.get(protocol)
        if not adapter:
            raise HTTPException(status_code=500, detail=f"系统缺少协议为 [{protocol}] 的翻译插件！")

        print(f"⚡ 正在通过【{adapter.__class__.__name__}】处理 {request.model} 的生图请求...")
        
        # 🚀 一键呼叫翻译官干活！主程序完全不管里面是怎么处理的
        image_url = await adapter.generate_image(request, model_config)

        return {"status": "success", "image_url": image_url}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"绘图引擎调用失败: {str(e)}")
    
# =========================================================
# ⚙️ 模型动态配置中心 API (大厂标准)
# =========================================================



@app.post("/admin/model-configs/update", tags=["管理端"])
async def update_model_config(req: ConfigUpdateRequest, db: Session = Depends(get_db)):
    try:
        import json
        config_record = None
        
        # 1. 精准定位：如果前端传了 ID，直接按 ID 找
        if getattr(req, "id", None):
            config_record = db.query(models.ModelConfig).filter(models.ModelConfig.id == req.id).first()
            
        # 2. 兜底定位：按名字和【文件夹名】查找 (💡 彻底消灭 provider)
        if not config_record:
            config_record = db.query(models.ModelConfig).filter(
                models.ModelConfig.model_name == req.model_name,
                models.ModelConfig.channel_name == req.channel_name # 👈 修复点：改用 channel_name
            ).first()
            
        # 3. 没找到就是新建
        if not config_record:
            config_record = models.ModelConfig(model_name=req.model_name)
            db.add(config_record)
            
        # 开始更新字段
        config_record.channel_name = req.channel_name
        config_record.api_protocol = req.api_protocol
        config_record.is_image_model = getattr(req, "is_image_model", True)
        
        # 强制转为 JSON 字符串，防止 SQLite 崩溃
        config_record.supported_ratios = json.dumps(req.supported_ratios) if getattr(req, "supported_ratios", None) else "[]"
        config_record.supported_sizes = json.dumps(req.supported_sizes) if getattr(req, "supported_sizes", None) else "[]"
        
        db.commit()
        return {"status": "success", "message": f"🎉 模型 [{req.model_name}] 已成功转移并配置！"}

    except Exception as e:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"后端存入崩溃: {str(e)}")

# =================================================================
# 🚀 批量大管家接口：批量更新 / 批量删除 / 清理失联
# =================================================================
@app.post("/admin/models/bulk-update", tags=["管理端"])
async def bulk_update_models(req: BulkUpdateRequest, db: Session = Depends(get_db)):
    """批量修改选定模型的渠道归属或协议"""
    try:
        models_to_update = db.query(models.ModelConfig).filter(models.ModelConfig.id.in_(req.ids)).all()
        for m in models_to_update:
            if req.channel_name is not None:
                m.channel_name = req.channel_name
            if req.api_protocol is not None:
                m.api_protocol = req.api_protocol
        db.commit()
        return {"status": "success", "message": f"成功批量更新了 {len(models_to_update)} 个模型！"}
    except Exception as e:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/models/bulk-delete", tags=["管理端"])
async def bulk_delete_models(req: BulkDeleteRequest, db: Session = Depends(get_db)):
    """物理删除选定的模型（单删也是调这个）"""
    try:
        db.query(models.ModelConfig).filter(models.ModelConfig.id.in_(req.ids)).delete(synchronize_session=False)
        db.commit()
        return {"status": "success", "message": f"成功删除了 {len(req.ids)} 个模型记录。"}
    except Exception as e:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/models/clean-lost", tags=["管理端"])
async def clean_lost_models(db: Session = Depends(get_db)):
    """一键清理当前系统内所有 is_lost=True 的幽灵模型"""
    try:
        deleted_count = db.query(models.ModelConfig).filter(models.ModelConfig.is_lost == True).delete()
        db.commit()
        return {"status": "success", "message": f"世界清静了，共清理 {deleted_count} 个失联模型。"}
    except Exception as e:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# 📂 文件夹 (渠道) 管理与 NewAPI 极速同步引擎
# =========================================================
@app.get("/admin/folders", tags=["管理端"])
def get_channel_folders(db: Session = Depends(get_db)):
    return {"status": "success", "folders": db.query(models.ImageChannelFolder).all()}

@app.post("/admin/folders", tags=["管理端"])
def create_channel_folder(req: ChannelFolderRequest, db: Session = Depends(get_db)):
    folder = db.query(models.ImageChannelFolder).filter(models.ImageChannelFolder.name == req.name).first()
    if not folder:
        db.add(models.ImageChannelFolder(name=req.name, base_url=req.base_url, api_key=req.api_key))
    else:
        folder.base_url, folder.api_key = req.base_url, req.api_key
    db.commit()
    return {"status": "success"}

@app.get("/admin/all-models", tags=["管理端"])
def get_all_models_for_admin(db: Session = Depends(get_db)):
    return {"status": "success", "models": db.query(models.ModelConfig).all()}

@app.post("/admin/sync-newapi", tags=["管理端"])
def sync_newapi(db: Session = Depends(get_db)):
    # 💡 使用全局环境里的管理员总钥匙去 NewAPI 进货
    base_url = os.getenv("AI_BASE_URL", "http://127.0.0.1:3000/v1").replace("/v1", "")
    api_key = os.getenv("AI_API_KEY", "")
    try:
        res = requests.get(f"{base_url}/v1/models", headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        res.raise_for_status()
        newapi_models = [m["id"] for m in res.json().get("data", [])]

        local_models = db.query(models.ModelConfig).all()
        local_names = {m.model_name for m in local_models}

        new_count, lost_count = 0, 0
        # 1. 发现新模型，扔进未分类暂存池
        for name in newapi_models:
            if name not in local_names:
                db.add(models.ModelConfig(model_name=name, channel_name="未分类", api_protocol="standard_openai", is_image_model=True))
                new_count += 1
                
        # 2. 检查本地模型是否在 NewAPI 丢失
        for m in local_models:
            if m.model_name not in newapi_models and not m.is_lost:
                m.is_lost = True
                lost_count += 1
            elif m.model_name in newapi_models and m.is_lost:
                m.is_lost = False
                
        db.commit()
        return {"status": "success", "new_count": new_count, "lost_count": lost_count}
    except Exception as e:
        return {"status": "error", "message": str(e)}



@app.get("/drawing/models", tags=["AI 创作"])
async def get_available_models(db: Session = Depends(get_db)):
    configs = db.query(models.ModelConfig).filter(models.ModelConfig.is_image_model == True).all()
    grouped_models = {}
    for c in configs:
        # 💡 画板绝对不展示“未分类”或“已丢失”的模型
        if c.channel_name == "未分类" or c.is_lost: continue
        if c.channel_name not in grouped_models: grouped_models[c.channel_name] = []
        grouped_models[c.channel_name].append(c.model_name)
    return {"status": "success", "models": grouped_models}

@app.get("/drawing/model-configs")
def get_dynamic_model_configs(db: Session = Depends(get_db)):
    import json
    configs = db.query(models.ModelConfig).all()
    res = {}
    for c in configs:
        unique_key = f"{c.channel_name}::{c.model_name}"
        res[unique_key] = {
            "ratios": c.supported_ratios if isinstance(c.supported_ratios, list) else [],
            "sizes": c.supported_sizes if isinstance(c.supported_sizes, list) else []
        }
    return {"status": "success", "configs": res}


    

