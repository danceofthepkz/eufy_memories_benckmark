#!/bin/bash

# Gemini Service Account 环境变量设置脚本
# 使用方法: source setup_env.sh

# 检查 Service Account 文件是否存在
if [ ! -f "./gen-lang-sa.json" ]; then
    echo "⚠️  警告: Service Account 文件不存在: ./gen-lang-sa.json"
    echo "请从 Google Cloud Console 下载 Service Account JSON 文件并放在项目根目录"
    echo ""
fi

# 设置 Google Cloud 环境变量
export GOOGLE_APPLICATION_CREDENTIALS=./gen-lang-sa.json
export GOOGLE_CLOUD_PROJECT=gen-lang-client-0057517563
export GOOGLE_CLOUD_LOCATION=us-central1

# 设置 PostgreSQL 环境变量（如果未设置，使用默认值）
export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export POSTGRES_DB=${POSTGRES_DB:-neweufy}
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-eufy123}

echo "✅ 环境变量已设置:"
echo ""
echo "📦 Google Cloud:"
echo "   GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
echo "   GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
echo "   GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"
echo ""
echo "🗄️  PostgreSQL:"
echo "   POSTGRES_HOST=$POSTGRES_HOST"
echo "   POSTGRES_PORT=$POSTGRES_PORT"
echo "   POSTGRES_DB=$POSTGRES_DB"
echo "   POSTGRES_USER=$POSTGRES_USER"
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "   ⚠️  POSTGRES_PASSWORD 未设置，请手动设置: export POSTGRES_PASSWORD=your_password"
else
    echo "   POSTGRES_PASSWORD=***"
fi
echo ""
echo "💡 提示: 如果使用 .env 文件，请确保已安装 python-dotenv 并在代码中加载"

