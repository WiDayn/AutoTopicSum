#!/bin/bash
# 前端启动脚本

echo "正在启动新闻聚合引擎前端服务..."

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "安装依赖包..."
    npm install
fi

# 启动开发服务器
echo "启动Vite开发服务器 (http://localhost:3000)..."
npm run dev

