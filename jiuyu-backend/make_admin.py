from app.core.database import SessionLocal
from app.models import base as models

# 1. 打开数据库的大门
db = SessionLocal()

# 2. 找到你的账号（如果你注册的不是 "用户1"，请把这里改成你的真实用户名）
target_username = "用户1"
user = db.query(models.User).filter(models.User.username == target_username).first()

if user:
    # 3. 赐予最高权限！
    user.role = "admin"
    db.commit()
    print(f"🎉 成功！账号【{user.username}】已在数据库物理层面升级为超级管理员！")
else:
    print(f"❌ 找不到名为【{target_username}】的用户，请检查用户名是否正确。")

db.close()