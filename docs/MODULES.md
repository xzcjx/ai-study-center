# 知识模块注册表

> **SSOT 机器可读版**：[`knowledge/registry.yaml`](../knowledge/registry.yaml)  
> 分类变更须同步：registry.yaml → 本文件 → INDEX.md → pipeline.md

## 模块一览

| ID | 目录 | 标签 | 涵盖范围 |
|----|------|------|----------|
| MOD-FE | `notes/frontend` | 前端 | React/Vue/CSS/性能/工程化/UX |
| MOD-BE | `notes/backend` | 后端 | API、框架、并发、缓存 |
| MOD-TEST | `notes/testing` | 测试 | 单元/E2E/性能/TDD |
| MOD-AI | `notes/ai-tools` | AI 工具 | Cursor/LLM/Prompt/Agent |
| MOD-OPS | `notes/devops` | DevOps | CI/CD/Docker/K8s/监控 |
| MOD-DB | `notes/database` | 数据库 | SQL/NoSQL/ORM/优化 |
| MOD-ARCH | `notes/architecture` | 架构 | 系统设计/模式/微服务 |
| MOD-MISC | `notes/misc` | 其他 | 工具/效率/兜底 |

## 分类决策树

```
内容是否关于 AI/LLM/Cursor/Agent？
  ├─ 是 → MOD-AI (ai-tools)
  └─ 否 → 是否关于测试？
           ├─ 是 → MOD-TEST
           └─ 否 → 是否关于部署/CI/容器？
                    ├─ 是 → MOD-OPS
                    └─ 否 → 是否关于数据库？
                             ├─ 是 → MOD-DB
                             └─ 否 → 是否关于系统设计/架构？
                                      ├─ 是 → MOD-ARCH
                                      └─ 否 → 是否前端 UI/浏览器？
                                               ├─ 是 → MOD-FE
                                               └─ 否 → 是否服务端/API？
                                                        ├─ 是 → MOD-BE
                                                        └─ 否 → MOD-MISC
```

## 跨模块内容

一篇输入可产生**多篇笔记**（H04 Classify → action: split）：

- 例：「Playwright 在 CI 中跑 E2E」→ `testing` + `devops` 各一篇，互相 `related` 链接

## 模块负责人（Agent 角色）

| Handler | 职责 |
|---------|------|
| H04 Classify | 读 registry.yaml keywords，打分选模块 |
| H07 Persist | 写入 `modules[].path` |
| H08 Index | 更新 INDEX.md 对应分区 |
