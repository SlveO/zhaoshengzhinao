FROM python:3.11-slim
WORKDIR /app

# 系统依赖：build-essential 给 sentence-transformers 编译用
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# 知识库数据 + 导入脚本（容器首次启动时自动导入到 TenantData）
COPY data/approved/ /app/data/approved/
COPY scripts/import_scnu_knowledge.py /app/scripts/import_scnu_knowledge.py

# HF Spaces 固定端口
EXPOSE 7860

# 模型缓存放 /data 避免重启后重下载
ENV MODELSCOPE_CACHE=/data/model-cache
ENV SENTENCE_TRANSFORMERS_HOME=/data/model-cache

# ChromaDB 向量库持久化
RUN mkdir -p /app/uploads
ENV CHROMA_PERSIST_DIR=/data/chroma

# 单 worker 避免多进程重复加载模型撑爆内存
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1 --timeout-keep-alive 300"]
