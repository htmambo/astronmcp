**Status**: ✅ 完成 (完成时间: 2026-06-22)

## 任务目标

在 MCP 启动 JSON 的 `env` 段中支持三种代理模式：`PROXY=false`（默认直连） / `PROXY=true|env`（使用环境变量代理） / `PROXY=custom`（自定义代理，含可选认证）。

## 设计要点

| `PROXY` 取值 | 含义 |
|---|---|
| `false` / `no` / `off` / `0` *(默认)* | 直连；httpx `trust_env=False`；websockets `proxy=None` |
| `true` / `env` / `yes` / `on` / `1` | 启用环境变量；httpx `trust_env=True` |
| `custom` | 使用下方 `HTTP(S)_PROXY_HOST/PORT/USER/PASSWORD`；HTTP 与 HTTPS 必须同时配置 |

## 改动详情

### 文件 1: `src/coding_bridge_mcp/config.py`
- 新增 `ProxyEndpoint` dataclass（scheme/host/port/username/password）
- 新增 `VALID_PROXY_MODES = {"false", "env", "custom"}` 与 `_TRUE_ALIASES` / `_FALSE_ALIASES`
- 新增 `_parse_proxy_endpoint(scheme)`：解析并校验 host/port/认证
- 新增 `_resolve_proxy_mode()`：归一化别名（true→env, false→false）
- 新增 `_load_proxy_settings()`：组合 mode + 两个 endpoint，启动期 fail-fast
- `Settings` dataclass 新增字段：`proxy_mode: str`、`proxy_http: Optional[ProxyEndpoint]`、`proxy_https: Optional[ProxyEndpoint]`

### 文件 2: `src/coding_bridge_mcp/api_client.py`
- 新增 `_build_client_kwargs(settings)` 工厂：
  - `false` → `{timeout, trust_env=False}`
  - `true|env` → `{timeout, trust_env=True}`
  - `custom` → `{timeout, trust_env=False, proxy: {scheme: httpx.Proxy(url)}}`
- `HttpApiClient.call` 改用 `_build_client_kwargs(self.settings)`
- `WebSocketApiClient.call` 在 `false` 模式显式 `proxy=None`；`env` 不传；`custom` 传 HTTPS proxy URL

### 文件 3: `tests/test_proxy_modes.py` (新增)
15 个用例，覆盖：
- 默认值 / 三种模式取值 / 别名 / 无效值报错
- custom 模式校验（必填 / 部分填 / 端口越界 / 密码无用户）
- `_build_client_kwargs` 契约（trust_env + proxy 字典结构）
- `HttpApiClient.call` 在 hostile env 与三种模式下的 httpx kwargs 传递

### 文件 4: `tests/test_no_proxy.py` (修改)
- `_settings()` 工厂补充 `proxy_mode="false"`, `proxy_http=None`, `proxy_https=None`（旧测试用例本身无需变更）

### 文件 5: `.env.example`
- 新增「代理 (PROXY)」段，含三种模式示例

### 文件 6: `README.md` §5
- 新增「代理 (PROXY)」子节，含配置表 + `settings.json` 示例

## 验收标准

| 标准 | 状态 |
|---|---|
| 全量 pytest 通过（含 15 个新用例） | ✅ 31 passed |
| 端到端 `PROXY=custom` 真实环境加载 | ✅ url 含认证信息 |
| 端到端 `PROXY=bogus` 报错列出全部合法值 | ✅ 无重复 |
| `.env.example` 与 `README §5` 同步 | ✅ |
| 旧测试 (config/logging/session/no_proxy) 不回归 | ✅ |

## 风险评估

- **WebSocket false 模式**：`websockets` 库 12+ 在 `proxy=None` 时仍可能读取 `https_proxy` 环境变量——已通过显式传 `proxy=None` 显式覆盖。需在真实部署验证。
- **SOCKS 代理**：本次未实现；`httpx[socks]` 仍为可选依赖 (review extra)。TODO 标记为「v1.1」。
- **代理认证**：当前仅支持 HTTP Basic；不支持摘要/SCRAM/NTLM。URL 中 username/password 已 percent-encode。

## 外部评审

外部评审 MCP (coding-bridge) 调用仍因调用方环境 socksio 缺失失败（与本项目无关）。按 CLAUDE.md §1.4 降级到主助理独立评审：verdict `APPROVED`，全部 15 个测试用例 + 端到端配置加载均验证通过。
