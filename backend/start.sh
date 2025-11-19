#!/bin/bash
# 后端启动脚本

echo "正在启动新闻聚合引擎后端服务..."

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖包..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "复制环境变量文件..."
    cp .env.example .env
fi

# 启动Flask应用
echo "启动Flask服务 (http://localhost:5001)..."
python run.py

