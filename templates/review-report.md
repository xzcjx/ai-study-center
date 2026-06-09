## Code Review 报告 · {review_id}

| 项 | 值 |
|----|-----|
| 目标 | `{target_ref}`（commit / PR / 模块） |
| 分析窗口 | `{window}` |
| 变更规模 | {commits} commits · {loc} LOC |
| 门禁 | {gate_result}（P0={p0_count} · P1={p1_count} · P2={p2_count}） |

### 摘要

{summary}

### 责任链进度（Agent 必须维护）

```
Review {review_id}
- [ ] R01 Intake      · 输入与边界
- [ ] R02 Scope       · DR 簇激活
- [ ] R03 Invariant   · 不变量扫描
- [ ] R04 Detect      · DR 逐条判定
- [ ] R05 Evidence    · 证据绑定
- [ ] R06 Triage      · 严重度与去重
- [ ] R07 Report      · 本模板输出
- [ ] R08 Gate        · 合入建议
```

### Findings（DR 格式 · 权威清单）

| DR | 严重度 | 位置 | 违反不变量 | 后果 | 建议方向 |
|----|--------|------|------------|------|----------|
| {dr_id} | {P0/P1/P2} | `{file:line}` | {invariant_one_liner} | {impact} | {fix_direction} |

> 无 findings 时写：`P0/P1 未命中`；P2 可选项单独列出。

### DR 覆盖矩阵

| DR 簇 | 已激活 | 命中 DR | 说明 |
|-------|--------|---------|------|
| SEC 机密与访问 | {Y/N} | {ids} | |
| DUR 持久与恢复 | {Y/N} | {ids} | |
| ATOM 原子与一致 | {Y/N} | {ids} | |
| ID 标识与关联 | {Y/N} | {ids} | |
| OBS 失败语义 | {Y/N} | {ids} | |
| ISO 隔离 | {Y/N} | {ids} | |
| LIFE 资源生命周期 | {Y/N} | {ids} | |
| CAP 容量与边界 | {Y/N} | {ids} | |
| CTR 外部契约 | {Y/N} | {ids} | |
| CHG 变更可审性 | {Y/N} | {ids} | |

### P0 门禁结论

{block_merge_reason / 可合入}

### 实例映射（可选 · 仅溯源）

| DR | 报告实例 |
|----|----------|
| {dr_id} | {omsec_or_sha_one_liner} |

### 下一步

- {request_changes_items}
- {human_confirm_items}
