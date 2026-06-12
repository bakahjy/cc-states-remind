# Claude Code Permission Toast — 设计文档

> 日期: 2026-06-13
> 状态: Approved Design

## 1. 概述

为 Claude Code 终端 CLI 提供一个右下角气泡样式的权限确认弹窗。当 Claude 试图执行 Bash/Write/Edit 等工具时，在屏幕右下角弹出带按钮的 GUI 窗口，让用户选择"允许一次"、"本次会话始终允许"或"拒绝"。

## 2. 架构

```
Claude Code Terminal
    │
    ├─ PreToolUse Hook ──→ permission_toast.py
    │                           │
    │                           ├─ session_cache.py ──→ .claude/cctoast-session.json
    │                           │       ↓
    │                           │  命中缓存? → exit 0
    │                           │
    │                           ├─ toast_window.py
    │                           │       ↓
    │                           │  Tkinter 弹窗 (屏幕右下角)
    │                           │  [Reject] [Allow Once] [Allow Session]
    │                           │
    │                           ├─ exit 0 → 继续执行
    │                           └─ exit 2 → 阻断操作
    │
    └─ .claude/settings.json ← Hook 注册
```

## 3. 触发范围

- **监控工具**: Bash, Write, Edit
- **Read / Glob / Grep 等只读工具**: 不弹窗，直接放行
- 支持 `matcher` 细粒度过滤（通过 settings.json 配置）

## 4. UI 方案

### 4.1 定位

- **屏幕右下角**，距底部 20px、距右侧 20px
- 使用 `tkinter` 获取工作区（workarea），避开任务栏
- `topmost=True` 置顶
- `overrideredirect(True)` + `withdraw()` 不在任务栏显示
- 多显示器：默认主显示器右下角（后续可配置跟随鼠标所在屏幕）

### 4.2 视觉风格（方案 B：暗色）

基于 VS Code 暗色风格：
- 背景: `#252526`，边框: `#3c3c3c`
- 圆角 12px，阴影 8px 32px
- 标题栏: 红色圆点状态指示 + "Permission Request" + 关闭按钮(×)
- 命令预览区域: `#1a1a1a` 背景，代码高亮色
- 按钮组: 右侧对齐

### 4.3 按钮行为

| 按钮 | 快捷键 | Exit Code | 行为 |
|------|--------|-----------|------|
| **Reject** | ESC / Alt+R | `exit 2` | 阻断操作，Claude 报权限拒绝 |
| **Allow Once** | Enter / Alt+O | `exit 0` | 本次放行 |
| **Allow Session** | Alt+S | `exit 0` | 写入 session cache + 放行 |

### 4.4 超时

- 默认 30 秒无操作 → 自动 Reject（`exit 2`）
- 通过环境变量 `CCTOAST_TIMEOUT` 可配置

## 5. Session 缓存

### 5.1 文件位置

```
<project>/.claude/cctoast-session.json
```

### 5.2 格式

```json
{
  "session_id": "cc-sess-<随机字符串>",
  "allowed_commands": [
    "Bash|rm -rf node_modules",
    "Edit|src/main.py|update version"
  ],
  "created_at": "2026-06-13T01:50:00",
  "expires_at": "2026-06-13T04:50:00"
}
```

### 5.3 匹配规则

- 精确匹配：`<ToolName>|<命令/路径前100字符>`
- 例如 Bash 命令精确匹配完整命令字符串，Edit/Write 匹配文件路径
- Session 过期时间: 默认 3 小时（通过 `CCTOAST_SESSION_TTL` 配置）

## 6. Hook 配置

### `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python \"<INSTALL_DIR>/hooks/permission_toast.py\""
          }
        ]
      }
    ]
  }
}
```

实际脚本内部根据 `CCTOAST_WATCHED_TOOLS` 环境变量过滤工具类型，非监控工具直接 exit 0 放行。

### 配置项（环境变量）

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `CCTOAST_TIMEOUT` | 30 | 弹窗超时（秒） |
| `CCTOAST_WATCHED_TOOLS` | Bash,Write,Edit | 需要弹窗的工具列表，逗号分隔 |
| `CCTOAST_SESSION_TTL` | 180 | Session 缓存有效期（分钟） |
| `CCTOAST_THEME` | dark | 主题（dark） |

## 7. stdin/stdout 协议

Hook 脚本通过标准输入接收 Claude Code 的事件信息，通过 exit code 返回决策。

### stdin 输入

```json
{
  "tool": "Bash",
  "input": "rm -rf node_modules",
  "cwd": "/home/user/project",
  "user": "Baka"
}
```

### stdout 日志（可选，供调试）

```json
{"action": "deny", "reason": "timeout"}
{"action": "allow_once"}
{"action": "allow_session"}
```

## 8. 项目结构

```
cc_states_remind/
├── hooks/
│   ├── permission_toast.py     ← 主入口
│   ├── config.py               ← 配置读取
│   ├── session_cache.py        ← Session 缓存读写
│   └── toast_window.py         ← Tkinter 弹窗 UI
├── .claude/
│   └── settings.json           ← Hook 配置
└── README.md                   ← 安装与使用说明
```

## 9. 平台兼容性

| 平台 | Tkinter | 安装命令 |
|------|---------|---------|
| Windows | ✅ 内置 | 无需额外安装 |
| Linux | ✅ apt install python3-tk | `sudo apt install python3-tk` |
| macOS | ✅ 内置 | 无需额外安装 |

## 10. 安全设计

- **超时默认 Deny**：用户无操作时自动拒绝，不放过风险
- **Session 精确匹配**：只放过完全相同的命令，避免误放
- **ESC / × 关闭**：所有非确认操作默认 Deny
- **无敏感信息存储**：Session 文件只存命令摘要
- **Session 自动过期**：3 小时后清除，不留永久缓存
