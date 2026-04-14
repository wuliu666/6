# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# 获取 .env 文件里的数据库地址（目前我们先用 SQLite，以后换 MySQL 只需要改 .env 里的地址即可）
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jiuyu_test.db")

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} # 这是 SQLite 特有的参数
)

# 创建数据库会话（类似一个可以随时打开关闭的数据通道）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有的表模型都要继承这个 Base 基础类
Base = declarative_base()