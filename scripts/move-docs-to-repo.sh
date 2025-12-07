#!/bin/bash
# 将文档移到 docs 库的脚本
# 使用前需要设置 DOCS_REPO_PATH 环境变量

set -e

# 默认路径：假设 xiaole-ai 仓库在同级目录
DOCS_REPO_PATH="${DOCS_REPO_PATH:-../xiaole-ai}"

if [ ! -d "$DOCS_REPO_PATH" ]; then
  echo "❌ Docs 仓库不存在: $DOCS_REPO_PATH"
  echo ""
  echo "💡 设置环境变量（本地文件系统路径，不是 GitHub URL）:"
  echo "   export DOCS_REPO_PATH=/path/to/xiaole-ai"
  echo ""
  echo "   例如："
  echo "   export DOCS_REPO_PATH=../xiaole-ai"
  echo "   或"
  echo "   export DOCS_REPO_PATH=/Users/rockts/Dev/xiaole-ai"
  echo ""
  echo "   GitHub 仓库: https://github.com/rockts/xiaole-ai"
  exit 1
fi

echo "📚 移动文档到 docs 库..."
echo "📁 Docs 仓库路径: $DOCS_REPO_PATH"
echo ""

# 创建目录结构
BACKEND_DOCS_DIR="$DOCS_REPO_PATH/backend"
mkdir -p "$BACKEND_DOCS_DIR/setup"
mkdir -p "$BACKEND_DOCS_DIR/development"

# 前端文档目录（如果存在前端文档）
FRONTEND_DOCS_DIR="$DOCS_REPO_PATH/frontend"
mkdir -p "$FRONTEND_DOCS_DIR"

# 移动文档
echo "📦 移动文档..."

# 使用指南
if [ -f docs/USAGE.md ]; then
  mv docs/USAGE.md "$BACKEND_DOCS_DIR/setup/usage.md"
  echo "   ✅ USAGE.md → backend/setup/usage.md"
fi

# 多仓库设置
if [ -f docs/MULTI-REPO-SETUP.md ]; then
  mv docs/MULTI-REPO-SETUP.md "$BACKEND_DOCS_DIR/setup/multi-repo-setup.md"
  echo "   ✅ MULTI-REPO-SETUP.md → backend/setup/multi-repo-setup.md"
fi

# iCloud 同步设置
if [ -f docs/iCloud-Sync-Setup.md ]; then
  mv docs/iCloud-Sync-Setup.md "$BACKEND_DOCS_DIR/setup/icloud-sync-setup.md"
  echo "   ✅ iCloud-Sync-Setup.md → backend/setup/icloud-sync-setup.md"
fi

# 优化方案
if [ -f docs/OPTIMIZATION-PLAN.md ]; then
  mv docs/OPTIMIZATION-PLAN.md "$BACKEND_DOCS_DIR/development/optimization-plan.md"
  echo "   ✅ OPTIMIZATION-PLAN.md → backend/development/optimization-plan.md"
fi

# 测试结果
if [ -f docs/TEST-RESULTS.md ]; then
  mv docs/TEST-RESULTS.md "$BACKEND_DOCS_DIR/development/test-results.md"
  echo "   ✅ TEST-RESULTS.md → backend/development/test-results.md"
fi

# 对话上下文模板
if [ -f docs/conversation-context.md ]; then
  mv docs/conversation-context.md "$BACKEND_DOCS_DIR/setup/conversation-context.md"
  echo "   ✅ conversation-context.md → backend/setup/conversation-context.md"
fi

# docs README
if [ -f docs/README.md ]; then
  mv docs/README.md "$BACKEND_DOCS_DIR/README.md"
  echo "   ✅ docs/README.md → backend/README.md"
fi

# 备份文件（删除）
if [ -f docs/DEV_CONTEXT.md.backup ]; then
  rm docs/DEV_CONTEXT.md.backup
  echo "   🗑️  删除备份文件: DEV_CONTEXT.md.backup"
fi

# 文档管理规则（移到 docs 库）
if [ -f docs/DOCS-MANAGEMENT.md ]; then
  mv docs/DOCS-MANAGEMENT.md "$BACKEND_DOCS_DIR/docs-management.md"
  echo "   ✅ DOCS-MANAGEMENT.md → backend/docs-management.md"
fi

echo ""
echo "✅ 文档移动完成！"
echo ""
echo "📁 文档位置："
echo "   - 后端文档: $BACKEND_DOCS_DIR/"
echo "     - setup/: 设置相关文档"
echo "     - development/: 开发相关文档"
echo "   - 前端文档: $FRONTEND_DOCS_DIR/ (如果有)"
echo ""
echo "📝 下一步："
echo "   1. 进入 docs 仓库: cd $DOCS_REPO_PATH"
echo "   2. 检查更改: git status"
echo "   3. 提交更改: git add . && git commit -m 'docs: 从 xiaole-backend 迁移文档到 backend/'"
echo "   4. 推送到远程: git push"
echo ""
echo "💡 注意："
echo "   - 后端文档已移动到: xiaole-ai/backend/"
echo "   - 前端文档应放在: xiaole-ai/frontend/ (如果创建了新文档)"

