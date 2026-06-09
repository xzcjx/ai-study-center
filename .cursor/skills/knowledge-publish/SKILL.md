---
name: knowledge-publish
description: >-
  从学习中心笔记生成可发布的小红书/公众号文章，或淘宝/闲鱼商品文案。
  AI 痕迹低、遵循各平台习惯。Use when user says /kb-publish, -redbook, -wechat,
  -taobao, -xianyu, 生成小红书, 公众号文章, 闲鱼商品, 淘宝上架, 发布笔记.
---

# Knowledge Publish · 笔记 → 平台内容

## 仓库路径

```
${AI_LEARNING_CENTER:-/Users/admin/cursorProjects/ai-study-center}
```

## 触发条件

用户消息含以下任一即执行本 Skill（**不是**入库 H01–H12）：

- `/kb-publish -redbook @notes/...`
- `/kb-publish -wechat notes/...`
- `/kb-publish -taobao` / `-xianyu`
- 「把这篇笔记发小红书」「生成闲鱼商品」

## 责任链 checklist

```
发布 {publish_id} · {platform} · {note_path}
- [ ] P01 Intake      → 解析平台 flag + 笔记路径
- [ ] P02 Load        → scripts/kb-publish.sh 输出 brief JSON
- [ ] P03 Platform    → knowledge/platforms-registry.yaml
- [ ] P04 Transform   → 按平台规范 + anti-AI-slop 生成正文
- [ ] P05 Persist     → 写入 publish/{platform}/（--no-save 跳过）
- [ ] P07 Publish     → scripts/publish-content.sh（默认 commit + push）
- [ ] P06 Report      → templates/publish-report.md 交付用户
```

## P01 · Intake

**平台 flag（必选其一）**：

| Flag | 平台 | 产出类型 |
|------|------|----------|
| `-redbook` | 小红书 | 短文 + 话题标签 |
| `-wechat` | 微信公众号 | 长文 + 小标题 |
| `-taobao` | 淘宝 | 商品标题 + 详情 + 定价 |
| `-xianyu` | 闲鱼/咸鱼 | 口语化 listing + Q&A |

**笔记路径**：`@notes/{module}/xxx.md` 或相对路径，必须在 `notes/` 下。

生成 `publish_id`：`PUB-{YYYYMMDD}-{note_id 末段或序号}`

## P02 · Load

```bash
{KB}/scripts/kb-publish.sh -{platform} @{note_path}
# 或
python3 {KB}/scripts/kb_publish.py --kb-root {KB} brief {platform} {note_path}
```

读取 JSON 中的 `note.tldr_bullets`、`key_points_excerpt`、`cautions` 作为改写素材。**禁止**整段复制笔记。

## P03 · Platform

读 [`knowledge/platforms-registry.yaml`](../../knowledge/platforms-registry.yaml)：

- `global_style.anti_ai_slop` — 所有平台强制
- `platforms.{id}.structure` / `formatting` / `avoid`
- 商品类额外读 `product_defaults`

## P04 · Transform

按 `platform.type` 分支：

### article（redbook / wechat）

1. 从 TL;DR + 知识要点提炼 **3–5 个读者收益点**
2. 用具体数字、对比、案例（仅笔记已有数据）
3. 小红书：600–900 字、短段、3–5 个 `#标签`
4. 公众号：1500–3500 字、`##` 小标题 3–5 个、可保留精简表格
5. 带货/收入类内容**必须**保留「案例需交叉验证」类提醒（来自笔记 cautions）

### product（taobao / xianyu）

1. 将笔记定位为 **电子资料 / 行业洞察合集 / 方法论手册**（按内容判断）
2. 淘宝：SEO 标题 ≤60 字、5 条卖点、详情分段、三档定价
3. 闲鱼：标题 ≤30 字、口语化、交付清单、3 条 FAQ、偏低定价
4. **禁止**绝对化用语、编造销量

**Anti-AI 自检**（生成后必做）：

- [ ] 无「首先/其次/综上所述/值得一提的是」套话
- [ ] 无 emoji 墙（小红书 ≤5 个）
- [ ] 至少 2 处具体数字或专有名词
- [ ] 读 aloud 不像 ChatGPT 模板

## P05 · Persist（默认开启，用户 `--no-save` 则跳过）

用户未说 `--no-save` 时，将成稿写入：

```
publish/{platform_id}/{YYYY-MM-DD}-{中文标题}.md
```

文件名取自笔记 frontmatter `title`；非法路径字符（`/`、`:` 等）替换为 `-`，超长截断至 80 字。

使用对应 [`templates/publish-*.md`](../../templates/) 结构填充。

## P07 · Publish

P05 落盘成功后 **默认执行**；用户显式 `--no-push` / `不要推送` / `--no-save` 时跳过。

```bash
{KB}/scripts/publish-content.sh {publish_id} {platform_id} "{成稿标题}" publish/{platform}/{filename}.md
```

- 仅提交 `publish/` 下文件
- 无 `origin` → 本地 commit，P06 标注未推送
- 推送失败 → P06 标注原因，不阻断成稿交付

## P06 · Report

用 [`templates/publish-report.md`](../../templates/publish-report.md) 回复，**开头**含：

```
发布 {publish_id} · {platform_label} · {note_title}
- [x] P01 … P07 · P06
```

正文区：**完整可粘贴的成稿**（聊天内直接可用）。**须含 P07 推送结果**（commit hash / 失败原因 / 已跳过）。

## 快捷命令

```
/kb-publish -redbook @notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md
/kb-publish -wechat notes/ai-tools/geo/2026-06-09-wechat-ai-live-commerce-landscape.md
/kb-publish -taobao @notes/.../xxx.md
/kb-publish -xianyu @notes/.../xxx.md
/kb-publish --list
/kb-publish -redbook @notes/.../xxx.md --no-save    # 仅聊天输出，不写文件、不推送
/kb-publish -redbook @notes/.../xxx.md --no-push    # 写文件但不推送
```

## SSOT

- [docs/PUBLISH.md](../../docs/PUBLISH.md)
- [knowledge/platforms-registry.yaml](../../knowledge/platforms-registry.yaml)

## 与入库的关系

- **独立链路**：不更新 INDEX、不跑 validate-note
- P07 默认 `publish-content.sh` commit + push（`--no-push` / `--no-save` 除外）
- 源笔记变更后重新 `/kb-publish` 即可
