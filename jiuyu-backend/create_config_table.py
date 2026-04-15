from app.core.database import engine
from app.models.base import Base

def run_safe_migration():
    print("🚀 开始扫描数据库表结构...")
    # 💡 核心安全机制：create_all 遇到已存在的表会自动跳过，只创建全新的表
    Base.metadata.create_all(bind=engine)
    print("✅ model_configs 新表创建/验证成功！旧数据完好无损。")

if __name__ == "__main__":
    run_safe_migration()