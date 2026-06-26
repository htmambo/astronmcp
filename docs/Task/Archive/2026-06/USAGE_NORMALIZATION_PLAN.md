**Status**: ✅ 已完成并通过外部审核 (开始时间: 2026-06-27 / 完成时间: 2026-06-27)

## 任务目标

在 Coding Bridge MCP 中引入 token 用量归一化与会话级累计能力，使用户（主要使用 volcengine-coding、偶尔 xfyun-coding）能够：

1. 每次 `chat` / `review_code` / `review_plan` 调用后在响应里看到本轮与累计的 token 用量
2. 通过新工具 `get_token_stats` 查询单会话或全局累计
3. 暴露 Anthropic 风格的 `cached_tokens` / `cache_creation_input_tokens` / `cache_read_input_tokens` 三件套 schema，保证未来切到原生缓存 Provider 时调用方零改动

## 改动详情

### 文件 1: `src/coding_bridge_mcp/api_client.py`
- 新增 `_normalize_usage(usage)` 模块级函数：归一化 OpenAI 兼容协议的 `usage` 字段为稳定 schema
  - 输入兼容 `usage.prompt_tokens_details.cached_tokens`（火山方舟风格）与顶层 `cached_tokens`（部分 xfyun 响应）
  - `_coerce_int` 防御性处理非数字 / 缺失字段
  - `cache_creation_input_tokens` / `cache_read_input_tokens` 在 OpenAI 兼容协议中**不存在对应字段**，统一置 0
- HTTP 与 WebSocket 路径均接入 `_normalize_usage`

### 文件 2: `src/coding_bridge_mcp/server.py`
- 新增 `_session_stats: Dict[sid, usage]` 累计字典
- 新增 `_SESSION_STATS_FIELDS` 常量统一字段定义
- 新增 `_empty_stats()` / `_accumulate_stats()` / `_aggregate_stats()` 三个辅助函数
- `_execute()` 在成功路径上调用 `_accumulate_stats`，响应新增 `cumulative_usage` 字段（**单次 `usage` 字段保持不变**，向后兼容）
- 新增 `get_token_stats` MCP 工具：传 `SESSION_ID` 取单会话累计；不传则取当前进程所有会话全局汇总（带 `session_count` / `sessions` 明细）

### 文件 3: `README.md`
- 工具说明章节追加 `get_token_stats` 段落
- `chat` 返回值示例补 `cumulative_usage` 字段并解释语义

### 文件 4-5: `tests/test_usage.py` (新增) / `tests/test_token_stats.py` (新增)
- 5 个归一化测试：None/空/火山风格/讯飞风格/total 缺失兜底/垃圾字段兜底
- 7 个累计 & 工具测试：累加正确性、None 跳过、跨会话聚合、全局查询、单会话查询、未知会话、cd 校验

## 验收标准

| 标准 | 状态 |
|---|---|
| `pytest` 全部通过 (43 passed，新增 12 个) | ✅ |
| 改动仅限目标文件，未污染其他业务代码 | ✅ |
| 既有 chat/review_code/review_plan 响应 schema 向后兼容 | ✅ |
| 外部审核（coding-bridge MCP review_code）通过 | ✅ APPROVED_WITH_NITS |

## 外部审核结论

通过 `mcp__coding-bridge__review_code` 提交审核，得到 **APPROVED_WITH_NITS** 评级。

### 关键风险与处置

| 严重度 | 外部报告 | 我的判定 | 处置 |
|---|---|---|---|
| High | `_session_stats` 内存泄漏 | ✅ 真实，但属**预存债** | **本次不修**——`_sessions` 自始就无清理机制，本改动只是复用了同一模式；属于项目层级遗留问题，单独建 issue 处理，避免本次越界 |
| Medium | API 失败时可能错误累计 | ❌ **误判** | 已在本地代码核查：`_accumulate_stats`（server.py:221）位于 `try/except ApiError`（server.py:210-218）**之后**，失败路径直接 return，**不会执行累计** |
| Medium | `cache_creation_input_tokens` / `cache_read_input_tokens` 硬编码 0 | ❌ **误判** | OpenAI 兼容协议**根本无此字段**。保留是为了未来接 Anthropic 原生 provider 时 schema 不变；注释中已显式说明 |
| Low | `cached_tokens=0` 时 fallback 误覆盖 | ❌ 理论可能，实际两个位置不会同时返回 | 不修 |

### 外部肯定点
- 归一化函数对缺失/非数字字段兜底充分
- 并发控制正确使用 `_sessions_lock`，无竞态
- 响应同时返回 `usage` 和 `cumulative_usage`，设计合理、向后兼容
- `get_token_stats` 支持按会话查询和全局聚合

## 遗留债（待跟进）

### 1. `_session_stats` / `_sessions` 内存泄漏
- **现象**：两个字典以 `session_id` 为键无限增长，无清理机制
- **影响**：长跑进程（如开发服务器）内存持续上升
- **建议方案**（下一个 PR）：
  - 在 `_append_message` 旁增加 `delete_session(sid)` 函数
  - 给 `_session_stats` 加上「最近访问时间」字段，`get_token_stats` 提供 `prune(older_than=...)` 入口
  - 或者直接对接到现有 `_trim_messages` 的字符上限，超过即驱逐
- **优先级**：低（CLI 进程通常短命，生产部署每次启动也是新进程）

### 2. OpenAI 兼容层不支持真正缓存
- **现象**：当前 volcengine-coding / xfyun-coding 默认不启用上下文缓存，`cached_tokens` 恒为 0
- **建议**：未来若需要真实缓存成本节省，应评估 Anthropic 原生 provider（火山方舟有「上下文缓存」功能但需 API 层显式 `cache_control` 字段）
- **优先级**：低

## 备注

- 审核过程中**额外验证**：`mcp__coding-bridge__review_code` 实际返回的响应里 `usage` 和 `cumulative_usage` 字段均存在，schema 与设计一致——这是新增工具链的首次实战验证
- 真实厂商响应字段命名未经在线 API Key 验证（项目 Not-tested 标注），但两个 provider 均为 OpenAI 兼容，归一化逻辑对标准字段名已覆盖
