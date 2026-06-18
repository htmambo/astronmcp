# Claude 协作约定（项目级）

本文件由 Claude 在每次会话自动加载，补充全局 `~/.claude/CLAUDE.md`。
本仓库为 vibe coding 通用仓库，新增 hook / 脚本 / 工具时遵循以下约定。

## 目录约定

### 脚本与工具位置

- ✅ **新脚本放在仓库根平级目录**：`hooks/`、`scripts/`、`tools/` 等
- ✅ 与现有 `src/`、`tests/`、`README.md` 平级，README/IDE 浏览一目了然
- ❌ **不要**嵌进 `.claude/`（除非是 Claude Code 工具自建的 `settings.local.json`）
- ❌ **不要**嵌进 `.omc/`（OMC 运行时状态，git 可忽略）
- ❌ **不要**嵌进 `.git/`（hook 系统自管）

理由：本仓库 `~/.claude/CLAUDE.md` 文档已声明"Coding Bridge MCP 是 vibe coding 通用仓库"。
隐藏目录约定（`.claude/hooks/`）属于用户级基础设施，**与本仓库定位无关**。
若两者混淆，会导致：

1. hook 源文件被错误地放在 `.claude/hooks/` —— 实际只是 Claude Code 工具的本地覆盖目录，不是项目约定
2. 用户级 settings.json 路径与项目路径语义混乱
3. 后续接入其他项目时，错误的目录约定会被错误复用

### Claude Code 工具目录

- `.claude/settings.local.json` —— Claude Code 自动创建，**只存本地覆盖**（如 hook 注册、permission allow），不应手动维护脚本
- `.claude/` 目录除 `settings.local.json` 外，**默认情况下不要新增任何文件**

## 已注册的全局 hook

| Hook | 路径 | 触发 | 行为 |
|---|---|---|---|
| review-watchdog | `~/.claude/hooks/review-watchdog.mjs` (symlink → `hooks/review-watchdog.mjs`) | PostToolUse: Write\|Edit | 代码文件改动后未检测到 runReview 调用则 stderr 告警 |

修改或新增 hook 时：源文件放 `hooks/`（仓库根平级），`~/.claude/hooks/` 改为 symlink 指向项目路径，`~/.claude/settings.json` 注册。

## 教训记录

### 2026-06-19 — 不再把 hook/脚本放进 `.claude/` 子目录

**事件**：实现 review-watchdog 时，第一版把 hook 放在 `.claude/hooks/review-watchdog.mjs`。
**用户纠正**：本仓库是 vibe coding 通用仓库，`.claude/` 是 Claude Code 工具自动管理的目录（含 `settings.local.json`），不需要再嵌一层项目级子目录。脚本应放在仓库根平级（如 `hooks/`）。
**Why**：避免项目级目录约定与用户级 Claude Code 工具目录约定混淆；保持仓库根目录与 README 一致可读。
**How to apply**：今后在本仓库新增任何 hook / 脚本 / 工具，**先看 `ls -la` 确认仓库根目录约定**，再决定平级目录名。不要默认套用其他项目的 `.claude/hooks/` 模式。