#!/bin/bash
# 开发上下文同步脚本
# 功能：总结今日开发任务，同步对话和任务到 DEV_CONTEXT.md，支持跨设备继续开发

set -e

SYNOLOGY_DIR="$HOME/SynologyDrive/XiaoleDev"
REPO_NAME=$(basename "$(pwd)")

# 根据仓库名称确定上下文文件
if [[ "$REPO_NAME" == *"backend"* ]] || [[ "$REPO_NAME" == *"xiaole-backend"* ]]; then
  CONTEXT_FILE="xiaole-backend-context.md"
elif [[ "$REPO_NAME" == *"web"* ]] || [[ "$REPO_NAME" == *"xiaole-web"* ]]; then
  CONTEXT_FILE="xiaole-web-context.md"
else
  CONTEXT_FILE="${REPO_NAME}-context.md"
fi

CONTEXT_PATH="$SYNOLOGY_DIR/$CONTEXT_FILE"
LINK_PATH="docs/DEV_CONTEXT.md"

echo "📝 开发上下文同步工具"
echo "================================"
echo ""

# 检查并初始化环境
init_environment() {
  echo "1️⃣ 检查环境..."
  
  # 创建 SynologyDrive 目录
  if [ ! -d "$SYNOLOGY_DIR" ]; then
    mkdir -p "$SYNOLOGY_DIR"
    echo "   ✅ 已创建 SynologyDrive 目录"
  fi
  
  # 创建上下文文件（如果不存在）
  if [ ! -f "$CONTEXT_PATH" ]; then
    cat > "$CONTEXT_PATH" << EOF
# $REPO_NAME 开发上下文

> 📱 此文件通过 SynologyDrive 同步，可在其他设备继续对话

---

## 当前状态 ($(date '+%Y-%m-%d %H:%M'))

### 代码同步状态
- **本地 develop**: 待更新
- **远程 develop**: 待更新
- **main**: 待更新
- **状态**: 待更新

---

## ✅ 已完成任务

（暂无）

---

## 📝 待办事项

（暂无）

---

## 最近对话记录

（暂无）

EOF
    echo "   ✅ 已创建上下文文件"
  fi
  
  # 创建符号链接
  mkdir -p docs
  if [ ! -L "$LINK_PATH" ]; then
    if [ -f "$LINK_PATH" ]; then
      mv "$LINK_PATH" "${LINK_PATH}.backup"
      echo "   ⚠️  已备份现有文件"
    fi
    ln -s "$CONTEXT_PATH" "$LINK_PATH"
    echo "   ✅ 已创建符号链接"
  fi
  
  echo ""
}

# 获取今日 git 提交记录
get_today_commits() {
  echo "2️⃣ 分析今日代码变更..."
  
  TODAY=$(date '+%Y-%m-%d')
  COMMITS=$(git log --oneline --since="$TODAY 00:00" --format="%h|%s" 2>/dev/null || echo "")
  
  if [ -z "$COMMITS" ]; then
    echo "   ℹ️  今日暂无提交记录"
    return
  fi
  
  echo "   📊 今日提交记录："
  echo "$COMMITS" | while IFS='|' read -r hash message; do
    echo "      - $message ($hash)"
  done
  echo ""
}

# 获取分支状态
get_branch_status() {
  CURRENT_BRANCH=$(git branch --show-current)
  CURRENT_COMMIT=$(git rev-parse --short HEAD)
  
  # 获取远程状态
  git fetch origin --quiet 2>/dev/null || true
  
  REMOTE_DEVELOP=$(git rev-parse --short origin/develop 2>/dev/null || echo "unknown")
  REMOTE_MAIN=$(git rev-parse --short origin/main 2>/dev/null || echo "unknown")
  
  # 检查工作区状态
  if git diff-index --quiet HEAD -- 2>/dev/null; then
    STATUS="✅ 完全同步，工作区干净"
  else
    STATUS="⚠️ 有未提交的变更"
  fi
  
  echo "当前分支: $CURRENT_BRANCH ($CURRENT_COMMIT)"
  echo "develop: $REMOTE_DEVELOP"
  echo "main: $REMOTE_MAIN"
  echo "状态: $STATUS"
}

# 交互式更新上下文
update_context() {
  echo "3️⃣ 更新开发上下文..."
  echo ""
  
  # 提取今日任务摘要
  TODAY=$(date '+%Y-%m-%d')
  COMMITS=$(git log --oneline --since="$TODAY 00:00" --format="- %s" 2>/dev/null || echo "")
  
  # 获取分支状态
  BRANCH_INFO=$(get_branch_status)
  
  echo "准备写入以下信息到上下文文件："
  echo ""
  echo "📅 日期: $TODAY"
  echo "🌿 分支状态:"
  echo "$BRANCH_INFO" | sed 's/^/   /'
  echo ""
  
  if [ -n "$COMMITS" ]; then
    echo "✅ 今日完成:"
    echo "$COMMITS" | sed 's/^/   /'
    echo ""
  fi
  
  # 询问是否添加对话摘要
  echo "是否添加对话摘要？(y/n) [按回车跳过]"
  read -r ADD_SUMMARY
  
  SUMMARY=""
  if [[ "$ADD_SUMMARY" =~ ^[Yy]$ ]]; then
    echo ""
    echo "请输入对话摘要（多行输入，结束后输入单独一行的 'END'）："
    SUMMARY_LINES=()
    while IFS= read -r line; do
      if [ "$line" = "END" ]; then
        break
      fi
      SUMMARY_LINES+=("$line")
    done
    SUMMARY=$(printf "%s\n" "${SUMMARY_LINES[@]}")
  fi
  
  # 生成更新内容
  TEMP_FILE=$(mktemp)
  
  # 读取现有文件并更新
  if [ -f "$CONTEXT_PATH" ]; then
    # 更新"当前状态"部分
    awk -v date="$(date '+%Y-%m-%d %H:%M')" -v info="$BRANCH_INFO" '
      /## 当前状态/ { 
        print $0 " (" date ")"
        print ""
        print "### 代码同步状态"
        print info
        print ""
        skip=1
        next
      }
      /^---$/ && skip { skip=0 }
      !skip
    ' "$CONTEXT_PATH" > "$TEMP_FILE"
    
    # 如果有今日提交，添加到"已完成任务"
    if [ -n "$COMMITS" ]; then
      awk -v date="$TODAY" -v commits="$COMMITS" '
        /## ✅ 已完成/ || /## ✅ 今日已完成/ {
          print "## ✅ 今日已完成 (" date ")"
          print ""
          print commits
          print ""
          print "---"
          print ""
          inserted=1
          next
        }
        { print }
      ' "$TEMP_FILE" > "${TEMP_FILE}.2" && mv "${TEMP_FILE}.2" "$TEMP_FILE"
    fi
    
    # 如果有对话摘要，添加到"最近对话记录"
    if [ -n "$SUMMARY" ]; then
      awk -v date="$TODAY" -v summary="$SUMMARY" '
        /## 最近对话记录/ {
          print $0
          print ""
          print "### " date " - 开发总结"
          print ""
          print summary
          print ""
          print "---"
          print ""
          inserted=1
          next
        }
        { print }
      ' "$TEMP_FILE" > "${TEMP_FILE}.2" && mv "${TEMP_FILE}.2" "$TEMP_FILE"
    fi
    
    mv "$TEMP_FILE" "$CONTEXT_PATH"
    echo ""
    echo "   ✅ 上下文已更新"
  else
    echo "   ❌ 上下文文件不存在"
    rm "$TEMP_FILE"
    return 1
  fi
}

# 验证同步状态
verify_sync() {
  echo ""
  echo "4️⃣ 验证同步状态..."
  
  if [ -f "$CONTEXT_PATH" ]; then
    SIZE=$(stat -f%z "$CONTEXT_PATH" 2>/dev/null || stat -c%s "$CONTEXT_PATH" 2>/dev/null)
    echo "   ✅ 上下文文件存在 ($SIZE 字节)"
  else
    echo "   ❌ 上下文文件不存在"
    return 1
  fi
  
  if [ -L "$LINK_PATH" ]; then
    TARGET=$(readlink "$LINK_PATH")
    if [ "$TARGET" = "$CONTEXT_PATH" ]; then
      echo "   ✅ 符号链接正确"
    else
      echo "   ⚠️  符号链接指向错误: $TARGET"
    fi
  else
    echo "   ❌ 符号链接不存在"
  fi
  
  echo ""
  echo "📍 文件位置: $CONTEXT_PATH"
  echo "🔗 符号链接: $LINK_PATH"
}

# 主流程
main() {
  init_environment
  get_today_commits
  
  echo "是否更新开发上下文？(y/n) [默认: y]"
  read -r UPDATE_CONTEXT
  
  if [[ ! "$UPDATE_CONTEXT" =~ ^[Nn]$ ]]; then
    update_context
  fi
  
  verify_sync
  
  echo ""
  echo "🎉 完成！"
  echo ""
  echo "💡 使用提示："
  echo "   - 上下文文件会自动通过 SynologyDrive 同步到其他设备"
  echo "   - 在新设备上，运行此脚本初始化环境"
  echo "   - AI 会自动读取 docs/DEV_CONTEXT.md（无需手动操作）"
  echo "   - 定期运行此脚本，保持上下文同步"
  echo ""
}

# 支持命令行参数
case "${1:-}" in
  --init)
    init_environment
    verify_sync
    ;;
  --status)
    get_today_commits
    get_branch_status
    ;;
  --help)
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --init     仅初始化环境（创建目录和符号链接）"
    echo "  --status   仅显示今日提交和分支状态"
    echo "  --help     显示此帮助信息"
    echo ""
    echo "不带参数运行时，进入交互式更新流程"
    ;;
  *)
    main
    ;;
esac
