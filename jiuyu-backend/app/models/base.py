# app/models/base.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="member")         # 'admin' 或 'member'
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    assets = relationship("Asset", back_populates="owner")

class InvitationCode(Base):
    __tablename__ = "invitation_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    storage_type = Column(String(20), nullable=False)   # 'TENCENT_COS' 或 'LOCAL'
    file_url = Column(String(500), nullable=False)
    asset_type = Column(String(50))
    prompt = Column(String(1000), nullable=True)        # 💡 正式入库：保存提示词
    ratio = Column(String(50), nullable=True)           # 💡 正式入库：保存比例
    size = Column(String(50), nullable=True)            # 💡 补漏：保存尺寸
    model = Column(String(100), nullable=True)          # 💡 补漏：保存模型
    style = Column(String(50), nullable=True)           # 💡 正式入库：保存风格
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="assets")

class ApiChannel(Base):
    __tablename__ = "api_channels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    model_name = Column(String(50), nullable=False)
    api_key = Column(String(255), nullable=False)
    base_url = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

from sqlalchemy import JSON, Boolean

# =========================================================
# ⚙️ 模型动态配置表 (大厂标准动态注册中心)
# =========================================================
class ModelConfig(Base):
    __tablename__ = "model_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), unique=True, index=True, nullable=False) # 模型名称，如 nano-banana-2
    provider = Column(String(50), default="default") # 供应商，如 grsai
    is_image_model = Column(Boolean, default=False)  # 开关：True为绘图模型，False为对话模型
    
    # 使用 JSON 字段直接存储下拉框配置！完美解决写死代码的问题！
    supported_ratios = Column(JSON, default=list) 
    supported_sizes = Column(JSON, default=list)