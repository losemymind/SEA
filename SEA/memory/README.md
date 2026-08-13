# memory/ — 跨会话记忆库（SEA 运行时内）

本目录是 agent 的长期记忆。**写得进、查得到、可回滚、会遗忘**——这是记忆库与普通笔记的区别。

## 文件约定

| 文件 | 内容 | 分类 |
|---|---|---|
| `preferences.yaml` | 用户/团队偏好条目 | preference |
| `lessons.yaml` | 经验教训、策略、事实 | experience / engineering |
| `NOTES.md` | 会话内短期笔记（工作区），完成后蒸馏进 yaml 再清理 | 短期 |
| `README.md` | 本说明 | — |

## 三类记忆

- **preference（个人偏好）**：代码风格、行为偏好、用户指令（如"完成任务后必须生成单元测试"）
- **experience（历史经验）**：出错与解决办法、主要流程、排查经验、构建运行经验
- **engineering（工程知识）**：技术栈、功能架构、API 文档、代码库顶层认知

## 条目 schema

字段定义见 `SEA/templates/lesson-schema.yaml`。核心：`id` / `type` / `category` / `claim` / `evidence` / `source`。

## 生命周期

```
召回 → 执行 → 多源提取 → 质量评估 → 整理（去重/冲突/融合）→ 有效性评估 → 遗忘
```

- **召回**：任务开始时检索相关条目，选择性注入上下文（不做全量塞入）
- **质量评估**：缺 `evidence` / `claim` 无法验证 → 拒绝保留
- **去重**：`python SEA/scripts/dedup-check.py` 提示近重复，人工合并
- **冲突**：时间新 + 证据强 胜出；旧条目标记 `deprecated: true`
- **有效性**：任务结束后对召回的条目评效；无效则降 `confidence` / 标记待遗忘
- **遗忘**：`confidence` 过低或长期未命中（`hits` 停滞 + 时间衰减）→ 从活跃区移除（归档，不硬删）

## 使用

- **写入**：按 schema 追加条目 → `python SEA/scripts/validate-memory.py` → 更新 CHANGELOG → git commit
- **校验**：`python SEA/scripts/validate-memory.py`（必填字段/类型/id 唯一）
- **查重**：`python SEA/scripts/dedup-check.py`（标题相似度 + 合并建议）

## 注意事项

- PII / 密钥绝不入库；如已误入，立即清理并更新 CHANGELOG
- 每条经验标注 `source`（self-reflect / user-correct / tool-feedback），用户纠正优先
- 记忆是"证明没变坏"后才算数：缺验证的教训先放 NOTES.md 草稿，别直接进正式库
