# 题目要求检查索引

本文件将题目 01–10 映射到可直接检查的文件；事实与判断口径以数据、SCHEMA 和来源记录为准。

| 编号 | 检查内容 | 直接检查位置 |
|---|---|---|
| 01 | 研究对象、证券标识、截点、范围、边界、状态和免责声明 | `README.md`、`SCHEMA.md`、`data/entities.json` |
| 02 | 五类关系、方向、主体、状态、时效与不确定性 | `src/schema.py`、`data/relations.json` |
| 03 | 合法公开资料与访问控制边界 | `COLLECTION.md`、`src/collect/fetch.py` |
| 04 | URL、发布方、日期、locator、实体歧义、冲突和过期处理 | `data/source_register.json`、`data/evidence_manifest.json`、`data/raw/` |
| 05 | 0–100 置信度、解释维度与业务分层 | `SCHEMA.md`、`src/scoring.py`、`tests/test_scoring_schema.py` |
| 06 | 数据源、采集、清洗、处理与离线复核 | `COLLECTION.md`、`src/build_dataset.py`、`src/build_evidence_manifest.py` |
| 07 | HTTP JSON API、CLI、筛选、分页、校验和错误响应 | `src/api.py`、`src/cli.py`、`src/query.py`、`tests/test_query.py` |
| 08 | 依赖、凭据说明、启动测试、更新复现和快照 | `README.md`、`requirements.txt`、`.github/workflows/verify.yml` |
| 09 | 关键路径、失败/边界测试、限制和改进方向 | `tests/`、`README.md` |
| 10 | AI/检索用途、人工验证、本人判断和数据安全 | `AI_USAGE.md` |

审阅时建议先读 README 的结论摘要，再抽查 `r-green-harmonic`、`r-chinamobile`、`r-chinatelecom-tower`、`r-tongji`、`r-zhongke-inv`、`r-deepseek-inv` 六条记录；它们覆盖了不支持证据、母子公司映射、失败投标、终端使用、基金穿透和直接战略配售六类关键边界。
