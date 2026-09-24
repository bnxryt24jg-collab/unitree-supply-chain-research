# 宇树科技供应链与合作关系研究

本项目基于合法公开资料，研究宇树科技股份有限公司（688836.SH）的供应商、客户、合作伙伴、投资关系与可比公司。交付重点不是关系数量，而是每个结论能否回答三个问题：**证据是否真的支持、关系方向是否准确、结论在当前时点是否仍成立**。本项目仅供研究与方法展示，不构成投资建议。

[![verify](https://github.com/bnxryt24jg-collab/unitree-supply-chain-research/actions/workflows/verify.yml/badge.svg)](https://github.com/bnxryt24jg-collab/unitree-supply-chain-research/actions/workflows/verify.yml)

[关系数据](./data/relations.json) · [证据清单](./data/evidence_manifest.json) · [数据口径](./SCHEMA.md)

## 结论摘要

### 1. 收入结构已经从四足机器人扩展到人形机器人

公开的《招股说明书（上会稿）》显示，2025 年人形机器人收入占比为 **51.78%**，四足机器人占比为 **41.62%**，人形机器人销量为 **5,215 台**（p.138）。这意味着分析宇树时，不能再只沿用“四足机器人公司”的单一标签；客户场景、竞争集合与核心零部件需求均已发生变化。下文“招股书”均指该上会稿。

### 2. 公开披露能证明采购结构，却不能识别十家候选上市供应商

2025 年机械类、电子类、电气类原材料采购占比分别为 **50.71%、22.40%、22.23%**，前五大原材料供应商采购占比合计 **22.54%**（招股书 pp.141–142）。但 p.142 的前五大供应商使用匿名代号，另列出的公司也不包含项目早期整理的绿的谐波、鸣志电器、奥比中光等十家公司。

因此，这十条记录保留为 `candidate`，置信度上限 40，默认不在查询结果中作为已确认供应商展示。这个处理比用“招股书是一手来源”替代“招股书是否出现该公司”的判断更重要。

### 3. 客户关系需要区分直接买方、上市母公司和终端使用单位

- 招股书 p.273 披露的签约主体是**中移（杭州）信息技术有限公司**，合同金额不超过 **3,970.35 万元**；项目将其映射至上市母公司中国移动，但明确标记为间接关系。媒体报道的 4,605 万元是标包预算，未当作实际合同金额。
- 同济大学公告证明采购 **1 台宇树 G1 EDU**，成交价 17 万元；成交供应商为幻飞智控科技（上海）有限公司，因此同济是终端使用单位，不等同于已证实的直接交易对手。
- 中国铁塔项目中宇树响应被否，属于失败投标边界案例，不构成客户事实。

### 4. 股权关系中，直接持股、战略配售和基金穿透不能混写

- 红杉中国相关主体发行前合计直接持股 **7.1149%**（招股书 pp.60–61）。
- 美团上市主体经汉海信息等路径发行前间接持股 **7.6114%**（招股书 pp.58–59、p.260）；“美团相关主体合计口径”与“上市公司穿透口径”不是同一个数字。
- DeepSeek 获配 933,399 股，占本次发行 **2.31%**，锁定 36 个月（发行结果公告 p.3），属于直接战略配售，不是基金间接持股。
- 中科创达持有相关基金 6.7797%，基金持有宇树 0.2925%；简单乘算约为 **0.0198%**，仍受基金结构影响，不能把 0.2925%直接写成中科创达的穿透持股。

### 5. 可比公司应按用途分组

- **财务可比**：优必选、越疆科技；
- **产品竞品**：云深处、乐聚、智元；
- **全球技术对标**：Tesla Optimus、Figure AI。

这种分组避免把“同赛道”“同产品形态”和“可用于估值比较”混为一谈。

## 研究范围与口径

| 项目 | 口径 |
|---|---|
| 研究对象 | 宇树科技股份有限公司（曾用名：杭州宇树科技股份有限公司） |
| 证券标识 | 688836.SH |
| 数据截点 | 2026-09-20 |
| 关系类型 | supplier、customer、partner、investor_or_investee、peer |
| 主体范围 | 以上市公司为主，补充必要的未上市投资方、政府与高校使用单位 |
| 不覆盖 | 未公开客户名单、传闻、个人信息、需绕过访问控制的资料 |

`status` 区分 `fact`、`inference` 与 `unknown`；`claim_support` 区分证据直接支持、有限推导、不支持与冲突。项目采用“一分一档”：

- `confidence_score`（0–100）只回答证据可信度；
- `relevance_tier`（`core` / `supplementary` / `candidate`）只回答业务重要性或当前处置。

证据不支持当前结论时最高 40 分；单一二手源最高 70 分；未解决冲突最高 60 分。完整公式和字段约束见 [SCHEMA.md](./SCHEMA.md)。

## 数据快照

当前 fixture 包含 **39 个实体、41 条研究记录和 46 条证据引用**：

| 分层 | 数量 | 含义 | 默认展示 |
|---|---:|---|---|
| core | 10 | 业务上优先关注且有支持证据 | 是 |
| supplementary | 18 | 证据成立，但关系间接、量级较低或用于补充背景 | 是 |
| candidate | 13 | 失败投标、生态兼容或未获直接证据支持 | 否 |

`39 / 41 / 46` 是用于检查确定性重建的 fixture 基线，不是研究质量证明。质量由 locator、claim 支持判断、置信度上限、边界案例测试和人工复核共同保证。

## 查看、查询与复现

### 环境与完整验证

项目使用 Python 3.11+，不需要 API key 或其他真实凭据。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python src/build_dataset.py
python src/build_evidence_manifest.py
python src/validate/check_consistency.py
python -m pytest -q
```

以上命令会确定性重建 JSON 和证据清单。CI 会在 Python 3.11、3.12、3.13 下执行相同步骤并检查生成物漂移。

### CLI

```bash
python src/cli.py stats
python src/cli.py relations --type customer --min-confidence 70
python src/cli.py relations --tier candidate
python src/cli.py evidence --relationship-id r-deepseek-inv
python src/cli.py graph --tier core
```

默认 `relations` 与 `graph` 不包含 `candidate`；使用 `--tier candidate` 或 `--include-candidates` 才会显式返回候选记录。

### HTTP JSON API

```bash
python -m uvicorn src.api:app --port 8000
curl 'http://127.0.0.1:8000/relations?type=customer&min_confidence=70'
curl 'http://127.0.0.1:8000/evidence?relationship_id=r-deepseek-inv'
curl 'http://127.0.0.1:8000/graph?tier=core'
```

API 与 CLI 复用 [src/query.py](./src/query.py)，支持关系类型、分层、状态、实体、置信度、时间窗口与分页；非法输入返回明确错误。

## 证据与合规

每条证据保留 URL、发布方、发布时间或获取时间、外部页码/章节/页面内检索短语、信息源头 `origin_id` 和本地研究笔记。`data/raw/*.md` 是摘要，不冒充来源全文；URL 是深链也不自动等于内容已经证明 claim。

研究仅使用合法可访问的公开资料，不绕过 robots、登录、付费墙、验证码、限流或其他访问控制，不保存密钥、个人数据、客户机密或未授权原文。来源选择、转载去重和冲突处理见 [COLLECTION.md](./COLLECTION.md)。

## 目录

```text
data/                       生成数据、来源登记、证据清单和研究摘要
src/build_dataset.py        声明式研究输入与数据生成
src/scoring.py              置信度公式和硬性上限
src/query.py                CLI/API 共用查询语义
src/cli.py                  可脚本化 JSON CLI
src/api.py                  FastAPI HTTP JSON API
src/validate/               数据一致性检查
tests/                      评分闸门、边界案例、查询和端到端测试
```

## 限制与下一步

| 当前限制 | 优先改进 |
|---|---|
| 十家候选上市供应商缺少逐家公司直接证据 | 仅在取得公司公告、投资者关系记录或可核实采购披露后升级 |
| 部分基金穿透只来自上市公司公开回应的媒体转述 | 补充上市公司公告和基金层级实体，避免简单乘算替代权益口径 |
| 华电、卧龙、长春合作等仍依赖二手来源 | 寻找官方成交公告、公司公告或协议发布页交叉验证 |
| 当前只有一个研究截点 | 增加版本化快照，记录关系状态、数值和证据变化 |

AI 与检索工具的实际用途、本人判断和数据安全边界见 [AI_USAGE.md](./AI_USAGE.md)。题目 01–10 的检查入口保留在 [ACCEPTANCE.md](./ACCEPTANCE.md)，仅作索引，不作为“完成度自评”。
