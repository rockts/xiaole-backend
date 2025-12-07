#!/bin/bash
# 开发上下文设置脚本
# 用于在新电脑上快速设置开发上下文

set -e

REPO_NAME=$(basename "$(pwd)")
ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/XiaoleDev"

# 根据仓库名称确定上下文文件名
if [[ "$REPO_NAME" == *"backend"* ]] || [[ "$REPO_NAME" == *"xiaole-backend"* ]]; then
  CONTEXT_FILE="xiaole-backend-context.md"
elif [[ "$REPO_NAME" == *"web"* ]] || [[ "$REPO_NAME" == *"xiaole-web"* ]]; then
  CONTEXT_FILE="xiaole-web-context.md"
else
  CONTEXT_FILE="${REPO_NAME}-context.md"
fi

echo "📦 设置开发上下文: $REPO_NAME"
echo "📄 上下文文件: $CONTEXT_FILE"
echo ""

# 1. 创建 iCloud 目录
echo "1️⃣ 创建 iCloud 目录..."
mkdir -p "$ICLOUD_DIR"
echo "   ✅ 目录已创建: $ICLOUD_DIR"

# 2. 创建 .cursorrules（如果不存在）
echo ""
echo "2️⃣ 检查 .cursorrules..."
if [ ! -f .cursorrules ]; then
  cat > .cursorrules << 'EOF'
Include context from ./xiaole-agent-context/*

# 开发上下文（iCloud 同步，不提交到代码库）
Include context from ./docs/DEV_CONTEXT.md if it exists
EOF
  echo "   ✅ 已创建 .cursorrules"
else
  # 检查是否已包含 DEV_CONTEXT.md
  if ! grep -q "DEV_CONTEXT.md" .cursorrules; then
    echo "" >> .cursorrules
    echo "# 开发上下文（iCloud 同步，不提交到代码库）" >> .cursorrules
    echo "Include context from ./docs/DEV_CONTEXT.md if it exists" >> .cursorrules
    echo "   ✅ 已更新 .cursorrules"
  else
    echo "   ℹ️  .cursorrules 已配置"
  fi
fi

# 3. 创建 docs 目录
echo ""
echo "3️⃣ 创建 docs 目录..."
mkdir -p docs
echo "   ✅ 目录已创建"

# 4. 创建 iCloud 文件（如果不存在）
echo ""
echo "4️⃣ 检查 iCloud 文件..."
if [ ! -f "$ICLOUD_DIR/$CONTEXT_FILE" ]; then
  cat > "$ICLOUD_DIR/$CONTEXT_FILE" << EOF
# $REPO_NAME 开发上下文

> 此文件通过 iCloud 在 Mac 设备间同步

## 当前任务

### [任务标题]
- **状态**: created | in_progress | waiting_user | completed
- **创建时间**: $(date '+%Y-%m-%d %H:%M')
- **描述**: [任务详细描述]
- **当前步骤**: [当前执行到哪一步]
- **下一步计划**: [接下来要做什么]

---

## 最近对话记录

### $(date '+%Y-%m-%d') - [对话主题]

**用户**: [用户输入]

**AI**: [AI回复]

**执行的操作**:
- [操作1]
- [操作2]

**结果**: [操作结果或状态]

---

## 待办事项

- [ ] [待办1]
- [ ] [待办2]

---

## 重要信息

- [重要信息或注意事项]
- [代码变更说明]
- [配置变更说明]

---

## 问题记录

### [问题标题]
- **描述**: [问题描述]
- **解决方案**: [解决方案或待解决]
- **相关文件**: [相关文件路径]
EOF
  echo "   ✅ 已创建 iCloud 文件: $CONTEXT_FILE"
else
  echo "   ℹ️  文件已存在: $CONTEXT_FILE"
fi

# 5. 创建符号链接
echo ""
echo "5️⃣ 创建符号链接..."
if [ -L docs/DEV_CONTEXT.md ]; then
  CURRENT_TARGET=$(readlink docs/DEV_CONTEXT.md)
  if [ "$CURRENT_TARGET" = "$ICLOUD_DIR/$CONTEXT_FILE" ]; then
    echo "   ℹ️  符号链接已存在且正确"
  else
    echo "   ⚠️  符号链接指向不同文件，更新中..."
    rm docs/DEV_CONTEXT.md
    ln -s "$ICLOUD_DIR/$CONTEXT_FILE" docs/DEV_CONTEXT.md
    echo "   ✅ 符号链接已更新"
  fi
elif [ -f docs/DEV_CONTEXT.md ]; then
  echo "   ⚠️  文件已存在，备份中..."
  mv docs/DEV_CONTEXT.md docs/DEV_CONTEXT.md.backup
  ln -s "$ICLOUD_DIR/$CONTEXT_FILE" docs/DEV_CONTEXT.md
  echo "   ✅ 已备份并创建符号链接"
else
  ln -s "$ICLOUD_DIR/$CONTEXT_FILE" docs/DEV_CONTEXT.md
  echo "   ✅ 符号链接已创建"
fi

# 6. 验证
echo ""
echo "6️⃣ 验证设置..."
if [ -L docs/DEV_CONTEXT.md ]; then
  TARGET=$(readlink -f docs/DEV_CONTEXT.md)
  if [ -f "$TARGET" ]; then
    echo "   ✅ 符号链接有效"
    echo "   📍 指向: $TARGET"
  else
    echo "   ⚠️  警告: 目标文件不存在，等待 iCloud 同步..."
  fi
else
  echo "   ❌ 错误: 符号链接创建失败"
  exit 1
fi

echo ""
echo "🎉 设置完成！"
echo ""
echo "📝 下一步："
echo "   1. 等待 iCloud 同步完成（查看 Finder 中的文件图标）"
echo "   2. 编辑 docs/DEV_CONTEXT.md 开始记录开发上下文"
echo "   3. AI 会自动读取此文件（无需手动操作）"
echo ""

