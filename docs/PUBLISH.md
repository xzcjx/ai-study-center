# 内容发布工作流（笔记 → 平台）

> **执行 SSOT**：从 `notes/` 笔记生成可发布的小红书/公众号文章，或淘宝/闲鱼商品文案。  
> **Skill**：`.cursor/skills/knowledge-publish/SKILL.md`  
> **平台规范**：[`knowledge/platforms-registry.yaml`](../knowledge/platforms-registry.yaml)

## 总览

```mermaid
flowchart LR
  N[notes/*.md] --> P01
  P01[Intake] --> P02[Load brief]
  P02 --> P03[Platform 规范]
  P03 --> P04[Transform 生成]
  P04 --> P05[Persist 可选]
  P05 --> P06[Report 交付]
```

## 责任链

| ID | 名称 | 输入 | 输出 |
|----|------|------|------|
| **P01** | Intake | 平台 flag + 笔记路径 | `publish_id` |
| **P02** | Load | 笔记文件 | brief JSON（`kb-publish.sh`） |
| **P03** | Platform | platform id | structure / anti-slop 规则 |
| **P04** | Transform | brief + 规则 | 平台成稿（Agent） |
| **P05** | Persist | 成稿 | `publish/{platform}/`（默认写入） |
| **P06** | Report | 全链路 | 用户可粘贴正文 + 备忘 |

## 快捷命令

```
/kb-publish -redbook @notes/{module}/xxx.md     # 小红书短文
/kb-publish -wechat @notes/{module}/xxx.md    # 公众号长文
/kb-publish -taobao @notes/{module}/xxx.md     # 淘宝商品页
/kb-publish -xianyu @notes/{module}/xxx.md     # 闲鱼 listing
/kb-publish --list                             # 列出平台
```

## 脚本

```bash
# 列出平台
scripts/kb-publish.sh --list

# 生成 Agent brief（JSON）
scripts/kb-publish.sh -redbook notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md
```

## 支持平台

| ID | 类型 | 说明 |
|----|------|------|
| `redbook` | article | 600–900 字、短段、话题标签 |
| `wechat` | article | 1500–3500 字、二级标题、导语小结 |
| `taobao` | product | SEO 标题、五条卖点、详情、定价档 |
| `xianyu` | product | 口语标题、交付清单、FAQ、闲鱼价 |

别名见 `platforms-registry.yaml`（如 `-xiaohongshu`、`-咸鱼`）。

## 产出路径

| 产物 | 路径 |
|------|------|
| 成稿（默认） | `publish/{platform}/{YYYY-MM-DD}-{中文标题}.md` |
| 模板 | `templates/publish-{platform}.md` |
| 报告 | Agent 回复（`templates/publish-report.md`） |

## 写作原则

1. **提炼不搬运** — 从 TL;DR / 知识要点改写，禁止整段复制笔记
2. **Anti-AI-slop** — 见 registry `global_style.anti_ai_slop`
3. **事实守恒** — 数据与案例仅来自笔记；带货类保留合规与交叉验证提醒
4. **平台习惯** — 小红书短平快；公众号可深度；淘宝 SEO；闲鱼像个人卖家

## 与入库 / 消费的区别

| 链路 | 场景 |
|------|------|
| H01–H12 Ingest | 新知识入库 |
| C00–C05 Consume | 跨项目装工具 / 方法论 |
| **P01–P06 Publish** | 已有笔记 → 对外发布内容 |

Publish **不**更新 INDEX、**不**自动 git commit（除非用户明确要求）。

## 示例

```
/kb-publish -redbook @notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md
```

Agent 将：

1. 运行 `kb-publish.sh` 加载笔记摘要
2. 按小红书规范生成 600–900 字成稿
3. 写入 `publish/redbook/2026-06-09-微信 AI 带货与 AI+电商落地-入口变革、数字人爆发与叫好叫座之辩.md`
4. 在回复中贴出可直接发布的正文
