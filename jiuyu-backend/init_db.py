# init_db.py
from app.core.database import engine, Base
# 必须导入这里，引擎才能“看见”这些图纸
from app.models.base import User, InvitationCode, Asset, ApiChannel

print("⏳ 正在为九雨创作台建造数据库表...")
Base.metadata.create_all(bind=engine)
print("🎉 恭喜！数据库表单全部创建成功！")