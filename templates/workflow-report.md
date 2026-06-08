## 方法论工作流 · {workflow_name}

| 项 | 值 |
|----|-----|
| 工作流 ID | `{workflow_id}` v{version} |
| 场景 | {query} |
| 路由 | {route_reason} |
| 目标项目 | `{project}` |

### 摘要

{summary}

### 执行进度（Agent 必须维护勾选）

```
工作流 {workflow_id}
- [ ] W01 …
- [ ] W02 工具安装
- [ ] W03 执行
- [ ] W04 验收
```

### 阶段详情

{phases_markdown}

### 一键 Agent Prompt（复制即用）

```
{agent_prompt_bundle}
```

### 下一步

- 安装预览：`{kb}/scripts/install-tool.sh <tool-id> --target "{project}"`
- 确认安装：加 `--yes`
- 仅重出 Prompt：`kb-workflow.sh "{query}" --prompt-only`
