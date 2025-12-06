#!/bin/bash
# 文档创建助手
# 自动将文档创建到 xiaole-ai 文档库的正确位置

set -e

DOCS_REPO_PATH="${DOCS_REPO_PATH:-../xiaole-ai}"
REPO_NAME=$(basename "$(pwd)")

# 检测仓库类型
if [[ "$REPO_NAME" == *"backend"* ]] || [[ "$REPO_NAME" == *"xiaole-backend"* ]]; then
  REPO_TYPE="backend"
  DOCS_DIR="$DOCS_REPO_PATH/backend"
elif [[ "$REPO_NAME" == *"web"* ]] || [[ "$REPO_NAME" == *"xiaole-web"* ]]; then
  REPO_TYPE="frontend"
  DOCS_DIR="$DOCS_REPO_PATH/frontend"
else
  echo "❌ 无法识别仓库类型: $REPO_NAME"
  echo "💡 请手动指定文档类型或检查仓库名称"
  exit 1
fi

# 检查文档库是否存在
if [ ! -d "$DOCS_REPO_PATH" ]; then
  echo "❌ 文档库不存在: $DOCS_REPO_PATH"
  echo "💡 设置环境变量: export DOCS_REPO_PATH=/path/to/xiaole-ai"
  exit 1
fi

# 显示使用说明
if [ $# -eq 0 ]; then
  echo "📚 文档创建助手"
  echo ""
  echo "用法:"
  echo "  $0 <文档类型> <文档名称>"
  echo ""
  echo "文档类型:"
  echo "  setup        - 设置相关文档 (→ $DOCS_DIR/setup/)"
  echo "  development  - 开发相关文档 (→ $DOCS_DIR/development/)"
  echo "  components   - 组件文档 (仅前端, → $DOCS_DIR/components/)"
  echo "  api          - API 文档 (仅前端, → $DOCS_DIR/api/)"
  echo ""
  echo "示例:"
  echo "  $0 setup usage-guide"
  echo "  $0 development optimization-plan"
  echo ""
  echo "当前仓库: $REPO_NAME ($REPO_TYPE)"
  echo "文档目录: $DOCS_DIR"
  exit 0
fi

DOC_TYPE=$1
DOC_NAME=$2

if [ -z "$DOC_NAME" ]; then
  echo "❌ 错误: 请提供文档名称"
  echo "用法: $0 <文档类型> <文档名称>"
  exit 1
fi

# 确定目标目录
case "$DOC_TYPE" in
  setup)
    TARGET_DIR="$DOCS_DIR/setup"
    ;;
  development|dev)
    TARGET_DIR="$DOCS_DIR/development"
    ;;
  components|component)
    if [ "$REPO_TYPE" != "frontend" ]; then
      echo "❌ 错误: components 类型仅适用于前端仓库"
      exit 1
    fi
    TARGET_DIR="$DOCS_DIR/components"
    ;;
  api)
    if [ "$REPO_TYPE" != "frontend" ]; then
      echo "❌ 错误: api 类型仅适用于前端仓库"
      exit 1
    fi
    TARGET_DIR="$DOCS_DIR/api"
    ;;
  *)
    echo "❌ 错误: 未知的文档类型: $DOC_TYPE"
    echo "支持的类型: setup, development, components (仅前端), api (仅前端)"
    exit 1
    ;;
esac

# 创建目录
mkdir -p "$TARGET_DIR"

# 生成文档文件名（确保是 .md 扩展名）
if [[ "$DOC_NAME" != *.md ]]; then
  DOC_FILE="$DOC_NAME.md"
else
  DOC_FILE="$DOC_NAME"
fi

TARGET_FILE="$TARGET_DIR/$DOC_FILE"

# 检查文件是否已存在
if [ -f "$TARGET_FILE" ]; then
  echo "⚠️  文件已存在: $TARGET_FILE"
  read -p "是否覆盖? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消"
    exit 1
  fi
fi

# 创建文档模板
cat > "$TARGET_FILE" << EOF
# ${DOC_NAME//-/ /}

> 创建时间: $(date '+%Y-%m-%d %H:%M')
> 仓库: $REPO_NAME ($REPO_TYPE)
> 类型: $DOC_TYPE

## 概述

[文档概述]

## 详细内容

[详细内容]

## 相关链接

- [相关链接]

## 更新记录

- $(date '+%Y-%m-%d'): 创建文档
EOF

echo "✅ 文档已创建: $TARGET_FILE"
echo ""
echo "📝 下一步:"
echo "   1. 编辑文档: $TARGET_FILE"
echo "   2. 提交到文档库:"
echo "      cd $DOCS_REPO_PATH"
echo "      git add $TARGET_FILE"
echo "      git commit -m 'docs($REPO_TYPE): 添加 $DOC_NAME'"
echo "      git push"

