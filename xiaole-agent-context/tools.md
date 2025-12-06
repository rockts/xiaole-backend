# 工具系统文档

## 工具概述

小乐 AI 管家支持多种工具，用于扩展 AI 的能力。所有工具通过 `ToolRegistry` 统一管理。

## 工具列表

### 1. 天气工具 (`weather_tool`)
**功能**：查询指定城市的天气信息

**参数**：
- `city` (str, 必填)：城市名称，如"北京"、"上海"
- `query_type` (str, 可选)：查询类型
  - `now`：当前天气（默认）
  - `3d`：3天预报
  - `7d`：7天预报

**使用示例**：
- "北京天气怎么样" → `{"city": "北京", "query_type": "now"}`
- "上海未来3天天气" → `{"city": "上海", "query_type": "3d"}`

### 2. 系统信息工具 (`system_info_tool`)
**功能**：查询系统资源使用情况

**参数**：
- `info_type` (str, 可选)：信息类型
  - `cpu`：CPU 使用率
  - `memory`：内存使用情况
  - `disk`：磁盘使用情况
  - `all`：全部信息（默认）

### 3. 时间工具 (`time_tool`)
**功能**：查询当前时间

**参数**：
- `format` (str, 可选)：时间格式
  - `full`：完整日期时间（默认）
  - `date`：仅日期
  - `time`：仅时间

### 4. 计算器工具 (`calculator_tool`)
**功能**：执行数学计算

**参数**：
- `expression` (str, 必填)：数学表达式，如 "2+3*4"

**注意**：支持基本四则运算，使用安全求值

### 5. 提醒工具 (`reminder_tool`)
**功能**：管理提醒事项

**参数**：
- `operation` (str, 必填)：操作类型
  - `create`：创建提醒
    - `content` (str, 必填)：提醒内容
    - `time_desc` (str, 必填)：时间描述（自然语言，如"明天早上8点"）
    - `title` (str, 可选)：提醒标题
  - `list`：查询提醒列表
    - `status` (str, 可选)：状态筛选（active/all/completed）
  - `delete`：删除提醒
    - `reminder_id` (int, 必填)：提醒ID
  - `update`：更新提醒
    - `reminder_id` (int, 必填)：提醒ID
    - `content` (str, 可选)：新内容
    - `time_desc` (str, 可选)：新时间

**使用示例**：
- "提醒我明天9点开会" → `{"operation": "create", "content": "开会", "time_desc": "明天9点"}`
- "删除提醒72" → `{"operation": "delete", "reminder_id": 72}`

### 6. 搜索工具 (`search_tool`)
**功能**：网络搜索

**参数**：
- `query` (str, 必填)：搜索关键词
- `max_results` (int, 可选)：最大结果数（默认5）
- `timelimit` (str, 可选)：时间限制（d/w/m/y）

**使用场景**：
- 实时信息查询
- 产品发布、价格等最新信息
- 知识库可能过时的内容

### 7. 文件工具 (`file_tool`)
**功能**：文件读写操作

**参数**：
- `operation` (str, 必填)：操作类型
  - `read`：读取文件
    - `path` (str, 必填)：文件路径
  - `write`：写入文件
    - `path` (str, 必填)：文件路径
    - `content` (str, 必填)：文件内容
  - `list`：列出目录
    - `path` (str, 可选)：目录路径（默认当前目录）
    - `recursive` (bool, 可选)：是否递归
  - `search`：搜索文件
    - `pattern` (str, 必填)：搜索模式
    - `recursive` (bool, 可选)：是否递归

**文档问答规则**：
- 询问总结/概要 → 不需要工具（使用记忆库中的文档摘要）
- 询问具体细节/特定数据 → **必须**调用 file 工具读取全文

### 8. 任务工具 (`task_tool`)
**功能**：任务管理

**参数**：
- `operation` (str, 必填)：操作类型
  - `list`：查询任务列表
    - `status` (str, 可选)：状态筛选
  - `delete`：删除任务
    - `task_id` (int, 必填)：任务ID

### 9. 视觉识别工具 (`vision_tool`)
**功能**：图片内容识别

**参数**：
- `image_path` (str, 必填)：图片路径

**功能**：
- 识别图片中的物体、场景、文字
- 识别人脸（如果已注册）
- 识别课程表等结构化内容

**使用场景**：
- 用户上传图片时自动调用
- 询问"这是什么"、"这张图是什么"时调用

### 10. 人脸注册工具 (`register_face_tool`)
**功能**：注册人脸信息

**参数**：
- `image_path` (str, 必填)：图片路径
- `person_name` (str, 必填)：人名

**使用场景**：
- 用户说"这是xxx"、"记住这张脸是xxx"、"认识一下xxx"时调用

### 11. 删除记忆工具 (`delete_memory_tool`)
**功能**：删除指定记忆

**参数**：
- `memory_id` (int, 必填)：记忆ID

## 工具调用流程

### 1. 意图识别
- 使用 `EnhancedToolSelector` 分析用户意图
- 快速规则匹配（常见模式）
- AI 深度分析（复杂场景）

### 2. 工具执行
- 通过 `ToolRegistry.execute()` 执行
- 支持异步执行
- 自动重试机制

### 3. 结果处理
- 工具结果传递给 AI 生成回复
- 工具数据优先级最高，覆盖记忆和对话历史
- 搜索结果保留来源链接

## 工具开发指南

### 创建新工具

1. 在 `tools/` 目录创建工具文件
2. 实现工具函数或类
3. 在 `agent.py` 的 `_register_tools()` 中注册
4. 在 `_analyze_intent()` 中添加意图识别规则

### 工具接口规范

```python
def tool_function(params: dict, user_id: str = None, session_id: str = None) -> dict:
    """
    工具函数
    
    Args:
        params: 工具参数
        user_id: 用户ID
        session_id: 会话ID
    
    Returns:
        {
            "success": bool,
            "data": any,
            "error": str (可选)
        }
    """
    pass
```

## 工具优先级

1. **search 工具**：实时信息查询，优先级最高
2. **reminder/task 工具**：用户明确要求时优先
3. **file 工具**：文档具体细节查询时使用
4. **其他工具**：根据用户意图选择

## 注意事项

1. **时间描述**：reminder 工具的 `time_desc` 使用自然语言，工具会自动解析，不要手动转换为 UTC
2. **城市信息**：weather 工具需要明确城市名，可以从记忆库中提取用户位置
3. **文档查询**：询问文档总结时不需要工具，询问具体细节时必须调用 file 工具
4. **工具结果优先级**：工具返回的数据绝对准确，必须优先使用，忽略过时的记忆

