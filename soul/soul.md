# Soul Agent 架构说明

## 当前能力
- 有情绪、性格、心跳
- 有短期记忆、长期压缩记忆、重要事件记忆和遗忘
- 支持多模型接口，目前已接入 `DeepSeek`、`OpenAI`、`Ollama`
- 支持结构化 tool-calling
- 支持模型驱动的多轮工具调用
- 支持桌面 autopilot：观察屏幕、决定动作、再观察
- 支持文件、目录、程序、窗口、网页和基础桌面操作

## 结构化工具调用
### 机制
- Provider 层支持接收 `tools`
- 对支持原生 tool-calling 的模型，直接解析返回的 `tool_calls`
- 对不支持的模型，仍保留 JSON fallback

### 当前工具
- `open_app`
- `open_url`
- `search_web`
- `list_processes`
- `list_windows`
- `inspect_screen`
- `capture_screen`
- `read_file`
- `write_file`
- `create_dir`
- `list_dir`
- `run_command`
- `type_text`
- `hotkey`
- `focus_window`
- `click`
- `scroll`

## 桌面 Autopilot
### 工作方式
1. 观察当前桌面
2. 把活动窗口、窗口列表、OCR、截图路径喂给模型
3. 模型选择下一步工具
4. 执行动作后再次观察
5. 直到模型返回最终总结或达到轮数上限

### CLI
- `/desktop <目标>`

### 例子
- `/desktop 观察当前屏幕并总结`
- `/desktop 打开记事本并输入 hello`

## 文件与系统工具
### 自然语言示例
- `创建 notes.txt 内容 你好`
- `读取 notes.txt`
- `创建文件夹 demo`
- `列出目录 .`
- `查看进程`
- `列出窗口`
- `看看屏幕`

## 配置
- `SOUL_TOOL_AGENT_ENABLED`
- `SOUL_MAX_TOOL_ROUNDS`
- `SOUL_ENABLE_LLM_PARSE`
- `SOUL_ENABLE_LLM_RESPOND`
- `SOUL_MODEL_ALIAS`
- `SOUL_MODEL_PROVIDER`
- `SOUL_MODEL_NAME`

## CLI 命令
- `/status`
- `/memory`
- `/models`
- `/model <alias>`
- `/screen`
- `/windows`
- `/processes`
- `/tasks`
- `/pending`
- `/desktop <目标>`
- `/exit`

## 运行
```bash
python -m soul.main
```

