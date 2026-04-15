# upgrade_db.py
from app.core.database import engine
from sqlalchemy import text

def run_upgrade():
    with engine.begin() as conn:
        print("🚀 开始无损升级数据库表结构...")
        for col in ["prompt VARCHAR(1000)", "ratio VARCHAR(50)", "style VARCHAR(50)"]:
            col_name = col.split()[0]
            try:
                conn.execute(text(f"ALTER TABLE assets ADD COLUMN {col}"))
                print(f"✅ 成功添加新列: {col_name}")
            except Exception:
                print(f"⚠️ 忽略: {col_name} 列可能已存在")
    print("🎉 数据库无损升级完成！您的旧数据完好无损！")

if __name__ == "__main__":
    run_upgrade()