#!/bin/bash
# 验证开发上下文设置

set -e

echo "🔍 验证开发上下文设置..."
echo ""

# 1. 检查 .cursorrules
echo "1️⃣ 检查 .cursorrules..."
if [ -f .cursorrules ]; then
  if grep -q "DEV_CONTEXT.md" .cursorrules; then
    echo "   ✅ .cursorrules 已配置 DEV_CONTEXT.md"
  else
    echo "   ⚠️  .cursorrules 未包含 DEV_CONTEXT.md"
  fi
  
  if grep -q "xiaole-agent-context" .cursorrules; then
    echo "   ✅ .cursorrules 已配置 xiaole-agent-context"
  else
    echo "   ⚠️  .cursorrules 未包含 xiaole-agent-context"
  fi
else
  echo "   ❌ .cursorrules 不存在"
fi

# 2. 检查符号链接
echo ""
echo "2️⃣ 检查符号链接..."
if [ -L docs/DEV_CONTEXT.md ]; then
  TARGET=$(readlink -f docs/DEV_CONTEXT.md)
  echo "   ✅ 符号链接存在"
  echo "   📍 指向: $TARGET"
  
  if [ -f "$TARGET" ]; then
    echo "   ✅ 目标文件存在"
    FILE_SIZE=$(stat -f%z "$TARGET" 2>/dev/null || stat -c%s "$TARGET" 2>/dev/null)
    echo "   📊 文件大小: $FILE_SIZE 字节"
  else
    echo "   ⚠️  目标文件不存在（可能正在 iCloud 同步）"
  fi
elif [ -f docs/DEV_CONTEXT.md ]; then
  echo "   ⚠️  docs/DEV_CONTEXT.md 是普通文件，不是符号链接"
else
  echo "   ❌ docs/DEV_CONTEXT.md 不存在"
fi

# 3. 检查 iCloud 文件
echo ""
echo "3️⃣ 检查 iCloud 文件..."
ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/XiaoleDev"
if [ -d "$ICLOUD_DIR" ]; then
  echo "   ✅ iCloud 目录存在"
  
  # 检查后端文件
  if [ -f "$ICLOUD_DIR/xiaole-backend-context.md" ]; then
    echo "   ✅ xiaole-backend-context.md 存在"
  else
    echo "   ⚠️  xiaole-backend-context.md 不存在"
  fi
  
  # 列出所有上下文文件
  echo ""
  echo "   📁 iCloud 目录内容:"
  ls -lh "$ICLOUD_DIR"/*.md 2>/dev/null | awk '{print "      " $9 " (" $5 ")"}' || echo "      无 .md 文件"
else
  echo "   ❌ iCloud 目录不存在"
fi

# 4. 检查 xiaole-agent-context
echo ""
echo "4️⃣ 检查 xiaole-agent-context..."
if [ -d xiaole-agent-context ]; then
  FILE_COUNT=$(find xiaole-agent-context -name "*.md" | wc -l | tr -d ' ')
  echo "   ✅ 目录存在，包含 $FILE_COUNT 个 .md 文件"
  
  echo "   📄 文件列表:"
  find xiaole-agent-context -name "*.md" -exec basename {} \; | sed 's/^/      - /'
else
  echo "   ❌ xiaole-agent-context 目录不存在"
fi

# 5. 检查 .gitignore
echo ""
echo "5️⃣ 检查 .gitignore..."
if [ -f .gitignore ]; then
  if grep -q "docs/DEV_CONTEXT.md" .gitignore; then
    echo "   ✅ DEV_CONTEXT.md 已加入 .gitignore"
  else
    echo "   ⚠️  DEV_CONTEXT.md 未加入 .gitignore"
  fi
else
  echo "   ⚠️  .gitignore 不存在"
fi

# 6. 测试读取（如果可能）
echo ""
echo "6️⃣ 测试文件可读性..."
if [ -f docs/DEV_CONTEXT.md ]; then
  if head -5 docs/DEV_CONTEXT.md > /dev/null 2>&1; then
    echo "   ✅ 文件可读"
    echo "   📝 前 3 行内容:"
    head -3 docs/DEV_CONTEXT.md | sed 's/^/      /'
  else
    echo "   ⚠️  文件无法读取"
  fi
fi

echo ""
echo "✅ 验证完成！"
echo ""
echo "💡 提示："
echo "   - 如果目标文件显示为云朵图标，需要等待 iCloud 同步"
echo "   - 可以在 Finder 中右键文件 → '下载' 手动触发同步"
echo "   - AI 会在每次对话时自动读取这些文件"

