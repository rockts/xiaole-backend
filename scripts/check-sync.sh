#!/bin/bash
# 检查 iCloud 同步状态

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/XiaoleDev"

echo "☁️  检查 iCloud 同步状态..."
echo ""

if [ ! -d "$ICLOUD_DIR" ]; then
  echo "❌ iCloud 目录不存在"
  exit 1
fi

echo "📁 iCloud 目录: $ICLOUD_DIR"
echo ""

# 检查文件
for file in "$ICLOUD_DIR"/*.md; do
  if [ -f "$file" ]; then
    filename=$(basename "$file")
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    modified=$(stat -f%Sm "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2)
    
    # 检查是否是 iCloud 占位符（文件存在但可能未下载）
    # macOS 上，如果文件是 iCloud 占位符，stat 可能返回特殊值
    echo "📄 $filename"
    echo "   大小: $size 字节"
    echo "   修改时间: $modified"
    
    # 尝试读取前几行
    if head -1 "$file" > /dev/null 2>&1; then
      echo "   ✅ 文件已下载到本地"
    else
      echo "   ☁️  文件可能正在同步（云朵图标）"
    fi
    echo ""
  fi
done

echo "💡 提示："
echo "   - 如果文件显示为云朵图标，右键文件 → '下载' 手动触发同步"
echo "   - 在 Finder 中查看文件图标状态最准确"

