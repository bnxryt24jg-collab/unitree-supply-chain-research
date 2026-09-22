"""数据集构建：把人工研究记录中的候选事实，按 SCHEMA 落成结构化数据。

- 实体 → data/entities.json
- 关系（含 EvidenceRef + 评分）→ data/relations.json
- 置信度由 src/scoring.score_relationship 统一计算，保证可复现。

运行：python src/build_dataset.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from schema import (
    ClaimSupport,
    Entity,
    EntityType,
    EvidenceRef,
    ListedStatus,
    RelationSubtype,
    RelationType,
    RelevanceTier,
    Relationship,
    SourceType,
    Status,
    Uncertainty,
)
from scoring import AS_OF, score_relationship
from evidence_locator import is_specific_locator

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# ----------------------------------------------------------------------------
# 实体库
# ----------------------------------------------------------------------------
ENTITIES = {
    "SH.688836": Entity(entity_id="SH.688836", name="宇树科技股份有限公司", entity_type=EntityType.COMPANY,
                        listed=ListedStatus.LISTED, exchange="SSE", ticker="688836.SH",
                        aliases=["杭州宇树科技股份有限公司", "宇树科技", "杭州宇树科技有限公司", "Unitree", "Unitree Robotics"],
                        role_in_graph="subject", notes="本研究的 focal company；实控人王兴兴，2026-08-19 科创板上市。"),
    # 供应商
    "SH.688017": Entity(entity_id="SH.688017", name="苏州绿的谐波传动科技股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="688017.SH", role_in_graph="related"),
    "SH.603728": Entity(entity_id="SH.603728", name="上海鸣志电器股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="603728.SH", role_in_graph="related"),
    "SH.688322": Entity(entity_id="SH.688322", name="奥比中光科技集团股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="688322.SH", role_in_graph="related"),
    "SH.603009": Entity(entity_id="SH.603009", name="上海北特科技集团股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="603009.SH", role_in_graph="related"),
    "SZ.300580": Entity(entity_id="SZ.300580", name="无锡贝斯特精机股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300580.SZ", role_in_graph="related"),
    "SH.603319": Entity(entity_id="SH.603319", name="湖南美湖智造股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="603319.SH", role_in_graph="related"),
    "SZ.002245": Entity(entity_id="SZ.002245", name="江苏蔚蓝锂芯股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="002245.SZ", role_in_graph="related"),
    "SH.603893": Entity(entity_id="SH.603893", name="瑞芯微电子股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="603893.SH", role_in_graph="related"),
    "SZ.002180": Entity(entity_id="SZ.002180", name="纳思达股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="002180.SZ", role_in_graph="related"),
    "HK.02498": Entity(entity_id="HK.02498", name="深圳市速腾聚创科技有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="HKEX", ticker="02498.HK", role_in_graph="related"),
    "SZ.300718": Entity(entity_id="SZ.300718", name="浙江长盛滑动轴承股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300718.SZ", aliases=["长盛轴承"], role_in_graph="related"),
    "SH.600143": Entity(entity_id="SH.600143", name="金发科技股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="600143.SH", aliases=["金发科技"], role_in_graph="related"),
    "SH.600580": Entity(entity_id="SH.600580", name="卧龙电气驱动集团股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="600580.SH", aliases=["卧龙电驱", "卧龙电气"], role_in_graph="related"),
    # 客户
    "SH.600941": Entity(entity_id="SH.600941", name="中国移动有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE/HKEX", ticker="600941.SH / 00941.HK", aliases=["中国移动"], role_in_graph="related", notes="采购主体为中移（杭州）信息技术有限公司；本节点表示上市母公司。"),
    "STATE.国家电网": Entity(entity_id="STATE.国家电网", name="国家电网有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="央企，未上市"),
    "HK.00788": Entity(entity_id="HK.00788", name="中国铁塔股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="HKEX", ticker="00788.HK", role_in_graph="related"),
    "STATE.华电": Entity(entity_id="STATE.华电", name="中国华电集团有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="央企集团，未上市"),
    "EDU.同济大学": Entity(entity_id="EDU.同济大学", name="同济大学", entity_type=EntityType.EDUCATION, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="高校科研使用单位"),
    # 间接股东
    "SZ.300543": Entity(entity_id="SZ.300543", name="深圳市朗科智能电气股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300543.SZ", aliases=["朗科智能"], role_in_graph="related"),
    "SZ.300454": Entity(entity_id="SZ.300454", name="深信服科技股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300454.SZ", role_in_graph="related"),
    "SZ.300496": Entity(entity_id="SZ.300496", name="中科创达软件股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300496.SZ", role_in_graph="related"),
    "SH.603980": Entity(entity_id="SH.603980", name="浙江吉华集团股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SSE", ticker="603980.SH", role_in_graph="related"),
    "SZ.300308": Entity(entity_id="SZ.300308", name="中际旭创股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="SZSE", ticker="300308.SZ", role_in_graph="related"),
    "UNLISTED.红杉中国": Entity(entity_id="UNLISTED.红杉中国", name="红杉中国", entity_type=EntityType.FUND, listed=ListedStatus.UNLISTED, aliases=["宁波红杉", "厦门雅恒"], role_in_graph="related", notes="招股书将宁波红杉与厦门雅恒合称红杉中国；两家股东为一致行动人"),
    "HK.03690": Entity(entity_id="HK.03690", name="美团", name_en="Meituan", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="HKEX", ticker="03690.HK", aliases=["美团-W", "Meituan"], role_in_graph="related", notes="招股书披露其通过汉海信息等主体间接持股"),
    # 竞争对手
    "HK.09880": Entity(entity_id="HK.09880", name="优必选科技", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="HKEX", ticker="09880.HK", role_in_graph="related"),
    "HK.02432": Entity(entity_id="HK.02432", name="深圳市越疆科技股份有限公司", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="HKEX", ticker="02432.HK", aliases=["越疆科技", "Dobot"], role_in_graph="related", notes="协作机器人上市公司"),
    "UNLISTED.云深处": Entity(entity_id="UNLISTED.云深处", name="云深处科技", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="四足/具身智能"),
    "UNLISTED.乐聚": Entity(entity_id="UNLISTED.乐聚", name="乐聚机器人", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="人形机器人（华为合作）"),
    "UNLISTED.智元": Entity(entity_id="UNLISTED.智元", name="智元机器人", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="人形机器人新锐"),
    "US.TSLA": Entity(entity_id="US.TSLA", name="Tesla (Optimus)", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="NASDAQ", ticker="TSLA", role_in_graph="related"),
    "UNLISTED.Figure": Entity(entity_id="UNLISTED.Figure", name="Figure AI", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="海外人形机器人"),
    # 合作伙伴（partner）
    "NVDA": Entity(entity_id="NVDA", name="NVIDIA 英伟达", entity_type=EntityType.COMPANY, listed=ListedStatus.LISTED, exchange="NASDAQ", ticker="NVDA", role_in_graph="related", notes="战略合作伙伴：联合推出 Isaac GR00T 参考设计人形机器人 H2 Plus"),
    "UNLISTED.DeepSeek": Entity(entity_id="UNLISTED.DeepSeek", name="杭州深度求索人工智能基础技术研究有限公司 (DeepSeek)", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, aliases=["深度求索", "DeepSeek"], role_in_graph="related", notes="战略合作伙伴（MOU）+ 产业股东"),
    "UNLISTED.GoogleDeepMind": Entity(entity_id="UNLISTED.GoogleDeepMind", name="Google DeepMind", entity_type=EntityType.COMPANY, listed=ListedStatus.UNLISTED, aliases=["DeepMind", "Google DeepMind"], role_in_graph="related", notes="研究型弱关联（inference，非官宣合作）"),
    "GOV.天津市": Entity(entity_id="GOV.天津市", name="天津市 / 天津经开区", entity_type=EntityType.GOVERNMENT, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="政府战略合作（具身智能场景落地）"),
    "GOV.成都市": Entity(entity_id="GOV.成都市", name="成都市", entity_type=EntityType.GOVERNMENT, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="政府战略合作"),
    "GOV.长春净月高新区": Entity(entity_id="GOV.长春净月高新区", name="长春净月高新区", entity_type=EntityType.GOVERNMENT, listed=ListedStatus.UNLISTED, role_in_graph="related", notes="政府战略合作"),
}


RAW = "data/raw"

WEB_LOCATORS = {
    "https://finance.ifeng.com/c/8tzPjLIGAof": "文章《卧龙电驱：闷声发财》；页面内检索‘无框力矩电机’与‘宇树’",
    "https://www.xhby.net/content/s699aeb4ce4b0d38d54d20ee9.html": "文章《春晚“机器人天团”刷屏，它们的“肌肉”和“关节”来自何方？》；页面内检索‘无框力矩电机’与‘宇树科技’",
    "https://www.21jingji.com/article/20250222/7db4c71ce3ab393b4333183712860fee.html": "文章《七倍大牛股长盛轴承的人形机器人狂想曲》；页面内检索‘签订合作协议’与‘不足1%’",
    "https://finance.sina.com.cn/stock/hyyj/2025-02-17/doc-inekufee4035232.shtml": "文章《A股有了一条叫“宇树”的人形机器人产业链》；页面内检索‘金发科技’；该文仅支持产业链候选线索",
    "https://finance.eastmoney.com/a/202507123455289035.html": "东方财富文章 ID 202507123455289035；页面内检索‘中移（杭州）’与‘4605万元’；正文依赖动态加载，正式合同额以同关系招股书 p.273 为准",
    "http://ln.people.com.cn/n2/2026/0205/c400024-41494376.html": "文章《国网铁岭供电“数字新员工”上岗》；页面内检索‘这批智能设备由宇树科技研发’与‘变电站自主巡检’",
    "https://www.eeo.com.cn/2026/0115/779669.shtml": "文章《宇树科技中标华电电力科研院人形巡检机器人项目》；页面内检索‘宁夏公司无人值守场站人形巡检机器人’",
    "https://www.stcn.com/article/detail/1467261.html": "文章《朗科智能：间接持有宇树科技约0.05%股权 对其无重大影响》；页面内检索‘0.0458%’",
    "https://www.stcn.com/article/detail/4070279.html": "文章《朗科智能：公司间接持有宇树科技的股份比例约为0.0379%》；页面内检索‘0.0379%’与‘暂无其他业务合作’",
    "https://www.stcn.com/article/detail/1535518.html": "文章《2连板牛股，披露持有宇树科技股权比例！》；页面内检索‘金石成长’与‘0.42%’",
    "https://www.stcn.com/article/detail/2659309.html": "文章《宇树科技启动IPO，参股公司曝光！杠杆资金盯上这10只绩优股》；页面内检索‘卧龙电驱、金发科技均通过金石成长’",
    "https://www.stcn.com/article/detail/1512508.html": "文章《宇树科技机器人上春晚消息刷屏 多家上市公司间接持股宇树科技或有业务合作》；页面内检索‘深信服’与‘有限合伙人’",
    "https://www.stcn.com/article/detail/1559321.html": "文章《中科创达：公司目前和宇树科技暂无业务合作 间接持股比例较低》；页面内检索‘6.7797%’与‘0.2925%’",
    "https://www.stcn.com/article/detail/1469072.html": "文章《三连板吉华集团：未来宇树科技对公司直接影响较小》；页面内检索‘0.02%股权’与‘不存在任何合作关系’",
    "https://www.stcn.com/article/detail/2763758.html": "文章《中际旭创：参投的基金持有部分宇树科技股份》；页面内检索同名标题短语",
    "https://news.cgtn.com/news/2026-06-01/NVIDIA-Unitree-unveil-new-humanoid-powered-by-Isaac-GR00T-1NCWlv6VRde/index.html": "文章《NVIDIA, Unitree unveil new humanoid powered by Isaac GR00T》；页面内检索‘strategic partnership’与‘Isaac GR00T’",
    "https://www.unitree.com/cn/H2plus/": "H2 Plus 产品页；检索‘Jetson Thor’与‘Isaac GR00T’",
    "http://tj.people.com.cn/n2/2026/0527/c375366-41593167.html": "文章《宇树科技与天津市签署合作协议 开展具身智能联合创新应用深度合作》；页面内检索‘签署合作协议’与‘具身智能’",
    "http://sc.people.com.cn/n2/2026/0725/c345167-41649738.html": "文章《成都市与宇树科技签署战略合作协议》；页面内检索‘战略合作协议’与‘产教融合’",
    "https://finance.sina.com.cn/wm/2026-09-03/doc-iniqnyae1083016.shtml": "文章《长春净月高新区正式“牵手”宇树科技，开启政企合作发展新篇章》；页面内检索‘战略合作协议’与‘长春净月高新区’",
    "https://github.com/google-deepmind/mujoco_playground": "GitHub 仓库目录 mujoco_playground/_src/locomotion/g1；检索路径‘/locomotion/g1’；仅支持 Unitree G1 技术生态关联",
}

CANDIDATES = {
    "r-green-harmonic", "r-mingzhi", "r-orbbec", "r-beite", "r-bester",
    "r-meihu", "r-ruixin", "r-nasda", "r-robotec", "r-wolan",
    "r-kingfa-sup", "r-chinatelecom-tower", "r-deepmind-partner",
}

CORE = {
    "r-chinamobile", "r-sequoia-inv", "r-meituan-inv", "r-deepseek-inv",
    "r-ubtech-peer", "r-dobot-peer", "r-nvidia-partner",
    "r-deepseek-partner", "r-tianjin-partner", "r-chengdu-partner",
}

INDIRECT_SUPPORT = {
    "r-chinamobile", "r-stategrid", "r-langke-inv", "r-kingfa-inv",
    "r-wolong-inv", "r-sangfor-inv", "r-zhongke-inv", "r-jihua-inv",
    "r-zhongji-inv",
}

STATEMENT_OVERRIDES = {
    "r-wolong-sup": "两家财经媒体报道卧龙电驱向宇树提供无框力矩电机；公开资料未披露采购占比，因此列为补充关系。",
    "r-kingfa-sup": "金发科技被产业链资料列为潜在材料供应方，但未找到可直接证明其向宇树供货的公开证据。",
    "r-chinamobile": "宇树招股书披露与中移（杭州）信息技术有限公司的重大销售合同，不超过3970.35万元；本关系映射至上市母公司中国移动，因此标记为间接。",
    "r-stategrid": "人民网报道国网铁岭供电公司使用宇树机器人；证据支持终端使用，不证明国家电网总部直接采购。",
    "r-chinatelecom-tower": "中国铁塔采购项目中宇树响应被否，不能据此认定中国铁塔为宇树客户。",
    "r-huadian": "媒体报道华电电力科学研究院相关巡检机器人项目由宇树中标；尚缺采购平台一手结果公告。",
    "r-tongji": "同济大学成交公告显示采购一台宇树G1 EDU，成交供应商为幻飞智控科技（上海）有限公司；同济为终端使用单位而非已证实的直接买方。",
    "r-kingfa-inv": "金发科技持有金石成长基金9.15%份额，该基金持有宇树4.62%；简单乘算约0.42%，实际权益仍受基金结构影响。",
    "r-wolong-inv": "证券时报报道卧龙电驱通过金石基金间接投资宇树；公开报道未披露其最终穿透持股比例。",
    "r-sangfor-inv": "证券时报报道深信服作为基金出资人间接投资宇树；基金持有宇树0.6279%，但深信服最终穿透比例未披露。",
    "r-zhongke-inv": "中科创达持有相关基金6.7797%份额，该基金持有宇树0.2925%；按简单乘算对应约0.0198%，实际权益仍受基金结构影响。",
    "r-deepseek-inv": "发行结果公告显示DeepSeek直接获配宇树首次公开发行战略配售股份933,399股，占本次发行2.31%，锁定期36个月。",
    "r-dobot-peer": "越疆科技（02432.HK）是协作机器人上市公司，作为财务可比公司纳入，而非笼统标作未上市人形机器人企业。",
    "r-deepseek-partner": "宇树上市路演中，王兴兴确认公司已与DeepSeek签署战略合作备忘录，合作覆盖通用AI、具身智能与大模型。",
    "r-deepmind-partner": "Google DeepMind 的 MuJoCo Playground 支持 Unitree 机型，证明生态兼容，不足以证明双方存在商业合作关系。",
}


def ev(source_type: SourceType, name: str, url: str, pub: str, loc: str) -> EvidenceRef:
    if "202608083835834723" in url:
        url = "https://roadshow.cnstock.com/ipo/688836"
        name = "上海证券报·中国证券网 IPO 路演"
        pub = "2026-08-07"
    if "dataclouds.cninfo.com.cn" in url:
        source_type, pub = SourceType.PRIMARY_REGULATORY, "2026-05-25"
    elif "static.cninfo.com.cn" in url or "hkexnews.hk" in url:
        source_type = SourceType.PRIMARY_REGULATORY
    elif "czb.tongji.edu.cn" in url or "ebid.chinatowercom.cn" in url:
        source_type = SourceType.PRIMARY_PROCUREMENT
    elif "roadshow.cnstock.com" in url or "unitree.com" in url or "github.com/google-deepmind" in url:
        source_type = SourceType.PRIMARY_OFFICIAL

    if "#供应商" in loc:
        locator = "PDF p.142，表‘报告期内前五名原材料供应商采购情况’；供应商以匿名代号及其他公司列示，未出现本候选公司名称"
    elif "#客户" in loc:
        locator = "PDF p.273，重大销售合同表：中移（杭州）信息技术有限公司，合同金额不超过3,970.35万元"
    elif "#股东-红杉中国" in loc:
        locator = "PDF pp.60–61，红杉中国相关股东及发行前合计持股7.1149%"
    elif "#股东-美团" in loc:
        locator = "PDF pp.58–59、p.260，美团上市主体间接持股路径及7.6114%口径"
    elif "#竞争对手" in loc:
        locator = "PDF‘市场竞争格局’章节；全文检索对应公司名称"
    elif "deepseek-investor" in loc:
        locator = "PDF p.3，战略配售投资者获配结果表：深度求索933,399股、2.31%、锁定36个月"
    elif "deepseek" in loc and "roadshow.cnstock.com" in url:
        locator = "路演问答：检索‘公司已与DeepSeek签署战略合作备忘录’"
    elif "同济" in name:
        locator = "成交公告正文：宇树G1 EDU 1台；预算19.5万元；成交17万元；供应商为幻飞智控科技（上海）有限公司"
    elif "中国铁塔" in name:
        locator = "采购结果公告：宇树科技响应被否决"
    elif "港交所" in name:
        name = "越疆科技关于深圳证券交易所IPO审核问询函的回复（港交所海外监管公告）"
        locator = "PDF同业及竞争格局相关章节；按公司名称检索"
    elif url in WEB_LOCATORS:
        locator = WEB_LOCATORS[url]
    else:
        raise ValueError(f"缺少精确 evidence locator：{name} {url}")
    if not is_specific_locator(locator):
        raise ValueError(f"evidence locator 不可执行：{name} {locator}")
    return EvidenceRef(
        source_type=source_type,
        source_name=name,
        url=url,
        published_date=date.fromisoformat(pub),
        evidence_locator=locator,
        origin_id=url,
        note=f"本地研究摘要：{loc}",
    )


def _subtype(rid: str, rtype: RelationType) -> RelationSubtype:
    if rid in CANDIDATES:
        if rtype == RelationType.SUPPLIER:
            return RelationSubtype.CANDIDATE_SUPPLIER
        if rid == "r-chinatelecom-tower":
            return RelationSubtype.REJECTED_BID
        return RelationSubtype.ECOSYSTEM_COMPATIBILITY
    if rtype == RelationType.SUPPLIER:
        return RelationSubtype.CONFIRMED_SUPPLIER
    if rtype == RelationType.CUSTOMER:
        return {
            "r-chinamobile": RelationSubtype.PARENT_GROUP,
            "r-stategrid": RelationSubtype.END_USER,
            "r-tongji": RelationSubtype.END_USER,
        }.get(rid, RelationSubtype.DIRECT_BUYER)
    if rtype == RelationType.INVESTOR_OR_INVESTEE:
        return {
            "r-sequoia-inv": RelationSubtype.DIRECT_SHAREHOLDER,
            "r-deepseek-inv": RelationSubtype.STRATEGIC_PLACEMENT,
        }.get(rid, RelationSubtype.FUND_LOOKTHROUGH)
    if rtype == RelationType.PEER:
        if rid in {"r-ubtech-peer", "r-dobot-peer"}:
            return RelationSubtype.FINANCIAL_COMPARABLE
        if rid in {"r-yunshen-peer", "r-leju-peer", "r-zhiyuan-peer"}:
            return RelationSubtype.PRODUCT_COMPETITOR
        return RelationSubtype.TECHNOLOGY_BENCHMARK
    if rid in {"r-tianjin-partner", "r-chengdu-partner", "r-changchun-partner"}:
        return RelationSubtype.GOVERNMENT_AGREEMENT
    return RelationSubtype.FORMAL_AGREEMENT


def rel(rid, rtype, obj, status, indirect, statement, evidences,
        start=None, end=None, uncertainty=Uncertainty.LOW):
    if rid == "r-dobot-peer":
        obj = "HK.02432"
    tier = RelevanceTier.CANDIDATE if rid in CANDIDATES else (RelevanceTier.CORE if rid in CORE else RelevanceTier.SUPPLEMENTARY)
    support = ClaimSupport.UNSUPPORTED if rid in CANDIDATES else (ClaimSupport.INDIRECT if rid in INDIRECT_SUPPORT else ClaimSupport.DIRECT)
    if rid in CANDIDATES:
        status, uncertainty, start = Status.UNKNOWN, Uncertainty.HIGH, None
    if rid == "r-deepseek-inv":
        indirect, uncertainty = False, Uncertainty.LOW
    if rid in {"r-kingfa-inv", "r-zhongke-inv"}:
        status, uncertainty = Status.INFERENCE, Uncertainty.MEDIUM
    if rid in {"r-chinamobile", "r-stategrid", "r-tongji"}:
        indirect = True
    if rtype == RelationType.INVESTOR_OR_INVESTEE and rid != "r-deepseek-inv":
        start = None
    if rid in {"r-green-harmonic", "r-mingzhi", "r-orbbec", "r-beite", "r-bester", "r-meihu", "r-ruixin", "r-nasda", "r-robotec", "r-wolan"}:
        statement = f"{ENTITIES[obj].name}曾被列为宇树供应链候选，但招股书p.142未披露该名称，当前不能确认供货关系。"
    statement = STATEMENT_OVERRIDES.get(rid, statement)
    r = Relationship(
        relationship_id=rid,
        subject_entity_id="SH.688836",
        object_entity_id=obj,
        relation_type=rtype,
        relation_subtype=_subtype(rid, rtype),
        status=status,
        claim_support=support,
        effective_start=start,
        effective_end=end,
        is_indirect=indirect,
        uncertainty=uncertainty,
        entity_direction_certainty=95 if rid not in CANDIDATES else 80,
        natural_statement=statement,
        evidence=evidences,
        relevance_tier=tier,
    )
    score_relationship(r)
    return r


CNINFO = "https://dataclouds.cninfo.com.cn/sjother2/documents/2026/2026-05-25/3d7fc0538abe281340a95c9c77a90525.pdf"
REL = f"{RAW}/cninfo_unitree_prospectus.md"
WEAK = f"{RAW}/media_supplier_weak.md"
INV = f"{RAW}/media_investor_indirect.md"
WOLONG_SUP = f"{RAW}/media_wolong_supplier.md"
CUST = f"{RAW}/caixin_customer.md"
PEER = f"{RAW}/broker_peer_supplychain.md"
PEER_EXACT = "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0622/2026062201645_c.pdf"
PARTNER_TECH = f"{RAW}/partner_nvidia_deepseek.md"
PARTNER_GOV = f"{RAW}/partner_government.md"

# ----------------------------------------------------------------------------
# 关系库
# ----------------------------------------------------------------------------
RELATIONS = [
    # ---- supplier candidates（招股书 p.142 未披露这些名称）----
    rel("r-green-harmonic", RelationType.SUPPLIER, "SH.688017", Status.UNKNOWN, False, "绿的谐波供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-mingzhi", RelationType.SUPPLIER, "SH.603728", Status.UNKNOWN, False, "鸣志电器供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-orbbec", RelationType.SUPPLIER, "SH.688322", Status.UNKNOWN, False, "奥比中光供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-beite", RelationType.SUPPLIER, "SH.603009", Status.UNKNOWN, False, "北特科技供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-bester", RelationType.SUPPLIER, "SZ.300580", Status.UNKNOWN, False, "贝斯特供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-meihu", RelationType.SUPPLIER, "SH.603319", Status.UNKNOWN, False, "美湖智造供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-ruixin", RelationType.SUPPLIER, "SH.603893", Status.UNKNOWN, False, "瑞芯微供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-nasda", RelationType.SUPPLIER, "SZ.002180", Status.UNKNOWN, False, "纳思达供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-robotec", RelationType.SUPPLIER, "HK.02498", Status.UNKNOWN, False, "速腾聚创供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    rel("r-wolan", RelationType.SUPPLIER, "SZ.002245", Status.UNKNOWN, False, "蔚蓝锂芯供应关系候选",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#供应商")]),
    # ---- supplier（两家媒体支持；业务量级未披露）----
    rel("r-wolong-sup", RelationType.SUPPLIER, "SH.600580", Status.FACT, False, "卧龙电驱向宇树供应无框力矩电机或关节相关部件",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "凤凰网财经", "https://finance.ifeng.com/c/8tzPjLIGAof", "2026-06-15", f"{WOLONG_SUP}#关键事实"),
         ev(SourceType.AUTHORITATIVE_MEDIA, "新华报业网", "https://www.xhby.net/content/s699aeb4ce4b0d38d54d20ee9.html", "2026-02-01", f"{WOLONG_SUP}#关键事实")],
        start=date(2026, 6, 15)),
    # ---- supplier（低量级事实与未证实候选）----
    rel("r-changsheng", RelationType.SUPPLIER, "SZ.300718", Status.FACT, False, "长盛轴承向宇树供货，但机器人相关收入占比不足1%",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "21世纪经济报道", "https://www.21jingji.com/article/20250222/7db4c71ce3ab393b4333183712860fee.html", "2025-02-22", f"{WEAK}#长盛轴承")],
        start=date(2025, 2, 18)),
    rel("r-kingfa-sup", RelationType.SUPPLIER, "SH.600143", Status.INFERENCE, False, "金发科技具备向宇树供应轻量化材料的可能性，未披露营收占比",
        [ev(SourceType.INDUSTRY_RESEARCH, "新浪财经产业链梳理", "https://finance.sina.com.cn/stock/hyyj/2025-02-17/doc-inekufee4035232.shtml", "2025-02-17", f"{WEAK}#金发科技-二级梳理")],
        start=date(2026, 8, 5), uncertainty=Uncertainty.MEDIUM),
    # ---- customer ----
    rel("r-chinamobile", RelationType.CUSTOMER, "SH.600941", Status.FACT, True, "中移（杭州）与宇树签有不超过3970.35万元的销售合同；关系映射至上市母公司中国移动",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "中国证券报·中证金牛座/东方财富", "https://finance.eastmoney.com/a/202507123455289035.html", "2025-07-12", f"{CUST}#中国移动"),
         ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#客户")],
        start=date(2025, 7, 11)),
    rel("r-stategrid", RelationType.CUSTOMER, "STATE.国家电网", Status.FACT, True, "国网铁岭供电公司使用宇树机器人开展营业厅服务和变电站巡检",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "人民网辽宁频道", "http://ln.people.com.cn/n2/2026/0205/c400024-41494376.html", "2026-02-05", f"{CUST}#国家电网体系")],
        start=date(2026, 1, 1)),
    rel("r-chinatelecom-tower", RelationType.CUSTOMER, "HK.00788", Status.UNKNOWN, False, "中国铁塔曾公开采购四足机器人，宇树参与投标但响应被否；当前不能确认已形成客户关系",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "中国铁塔电子采购平台", "https://ebid.chinatowercom.cn/zgtt/gggs/003004/20250801/db82d15d-b1fd-4075-aea8-59cd40e31f80.html", "2025-08-01", f"{CUST}#中国铁塔-投标边界")],
        start=date(2025, 8, 1), uncertainty=Uncertainty.HIGH),
    rel("r-huadian", RelationType.CUSTOMER, "STATE.华电", Status.FACT, False, "华电电力科学研究院的宁夏无人值守场站人形巡检机器人项目由宇树中标",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "经济观察网", "https://www.eeo.com.cn/2026/0115/779669.shtml", "2026-01-15", f"{CUST}#华电")],
        start=date(2026, 1, 15)),
    rel("r-tongji", RelationType.CUSTOMER, "EDU.同济大学", Status.FACT, True, "同济大学通过成交供应商采购一台宇树 G1 EDU",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "同济大学采购与招标管理办公室", "https://czb.tongji.edu.cn/sggl/cgw/news.jsp?lmbh=JJJGGG&wid=202606270138319108", "2026-06-27", f"{CUST}#高校科研客户-G1-EDU")],
        start=date(2026, 6, 27)),
    # ---- investor_or_investee（外部→宇树，含间接穿透）----
    rel("r-langke-inv", RelationType.INVESTOR_OR_INVESTEE, "SZ.300543", Status.FACT, True, "朗科智能经产业基金间接持有宇树约0.0379%股权（2026-08-10口径；历史口径约0.0458%）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "证券时报", "https://www.stcn.com/article/detail/1467261.html", "2024-12-25", f"{INV}#朗科智能-历史口径"),
         ev(SourceType.AUTHORITATIVE_MEDIA, "人民财讯/证券时报", "https://www.stcn.com/article/detail/4070279.html", "2026-08-11", f"{INV}#朗科智能-最新口径")],
        start=date(2024, 12, 25)),
    rel("r-kingfa-inv", RelationType.INVESTOR_OR_INVESTEE, "SH.600143", Status.INFERENCE, True, "金发科技经金石成长基金间接投资宇树，简单乘算约0.42%",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "证券时报", "https://www.stcn.com/article/detail/1535518.html", "2025-02-20", f"{INV}#金发科技")],
        start=date(2025, 2, 20)),
    rel("r-wolong-inv", RelationType.INVESTOR_OR_INVESTEE, "SH.600580", Status.FACT, True, "卧龙电驱经基金间接持有宇树股权（同时为电机供应商）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "证券时报·数据宝", "https://www.stcn.com/article/detail/2659309.html", "2025-07-21", f"{INV}#卧龙电驱")],
        start=date(2026, 3, 1)),
    rel("r-sangfor-inv", RelationType.INVESTOR_OR_INVESTEE, "SZ.300454", Status.FACT, True, "深信服经股权平台间接持有宇树（财务投资）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "证券时报", "https://www.stcn.com/article/detail/1512508.html", "2025-01-29", f"{INV}#深信服")],
        start=date(2026, 9, 1)),
    rel("r-zhongke-inv", RelationType.INVESTOR_OR_INVESTEE, "SZ.300496", Status.INFERENCE, True, "中科创达经安创科技间接投资宇树，简单乘算约0.0198%",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "人民财讯/证券时报", "https://www.stcn.com/article/detail/1559321.html", "2025-03-03", f"{INV}#中科创达")],
        start=date(2026, 9, 1)),
    rel("r-jihua-inv", RelationType.INVESTOR_OR_INVESTEE, "SH.603980", Status.FACT, True, "吉华集团经容腾基金间接持有宇树约0.02%（财务投资，暂无业务合作）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "证券时报", "https://www.stcn.com/article/detail/1469072.html", "2024-12-26", f"{INV}#吉华集团")],
        start=date(2026, 9, 1)),
    rel("r-zhongji-inv", RelationType.INVESTOR_OR_INVESTEE, "SZ.300308", Status.FACT, True, "中际旭创经基金间接持有宇树（财务投资）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "人民财讯/证券时报", "https://www.stcn.com/article/detail/2763758.html", "2025-07-27", f"{INV}#中际旭创")],
        start=date(2026, 9, 1)),
    rel("r-sequoia-inv", RelationType.INVESTOR_OR_INVESTEE, "UNLISTED.红杉中国", Status.FACT, False, "招股书将宁波红杉与厦门雅恒合称“红杉中国”；二者为一致行动人，发行前合计直接持有宇树7.1149%股份",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#股东-红杉中国")],
        start=date(2026, 5, 25)),
    rel("r-meituan-inv", RelationType.INVESTOR_OR_INVESTEE, "HK.03690", Status.FACT, True, "招股书披露Meituan/美团（03690.HK）发行前间接持有宇树7.6114%股份",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）", CNINFO, "2026-05-25", f"{REL}#股东-美团")],
        start=date(2026, 5, 25)),
    rel("r-deepseek-inv", RelationType.INVESTOR_OR_INVESTEE, "UNLISTED.DeepSeek", Status.FACT, False, "DeepSeek直接参与宇树IPO战略配售",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技首次公开发行股票并在科创板上市发行结果公告", "https://static.cninfo.com.cn/finalpage/2026-08-14/1225472623.PDF", "2026-08-14", f"{PARTNER_TECH}#deepseek-investor")],
        start=date(2026, 8, 14), uncertainty=Uncertainty.MEDIUM),
    # ---- peer（竞争对手）----
    rel("r-ubtech-peer", RelationType.PEER, "HK.09880", Status.FACT, False, "优必选为宇树国内人形机器人直接竞品（已量产交付）",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）竞争格局", CNINFO, "2026-05-25", f"{REL}#竞争对手"),
         ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")]),
    rel("r-tesla-peer", RelationType.PEER, "US.TSLA", Status.FACT, False, "特斯拉 Optimus 为宇树海外人形机器人对标",
        [ev(SourceType.PRIMARY_REGULATORY, "宇树科技招股说明书（上会稿）竞争格局", CNINFO, "2026-05-25", f"{REL}#竞争对手")]),
    rel("r-dobot-peer", RelationType.PEER, "HK.02432", Status.FACT, False, "越疆科技为协作机器人可比公司",
        [ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")],
        start=date(2026, 8, 25)),
    rel("r-yunshen-peer", RelationType.PEER, "UNLISTED.云深处", Status.FACT, False, "云深处为四足/具身智能竞品",
        [ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")],
        start=date(2026, 8, 25)),
    rel("r-leju-peer", RelationType.PEER, "UNLISTED.乐聚", Status.FACT, False, "乐聚为华为合作人形机器人竞品",
        [ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")],
        start=date(2026, 8, 25)),
    rel("r-zhiyuan-peer", RelationType.PEER, "UNLISTED.智元", Status.FACT, False, "智元机器人为人形机器人新锐竞品",
        [ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")],
        start=date(2026, 8, 25)),
    rel("r-figure-peer", RelationType.PEER, "UNLISTED.Figure", Status.FACT, False, "Figure AI 为海外人形机器人对标",
        [ev(SourceType.PRIMARY_REGULATORY, "越疆科技审核问询函回复（港交所海外监管公告）", PEER_EXACT, "2026-06-22", f"{PEER}#peer")],
        start=date(2026, 8, 25)),
    # ---- partner（战略合作，subject 恒为宇树）----
    rel("r-nvidia-partner", RelationType.PARTNER, "NVDA", Status.FACT, False, "宇树与 NVIDIA 达成战略合作，联合推出 Isaac GR00T 参考设计人形机器人 H2 Plus（宇树本体 + 英伟达 Jetson Thor 算力 + GR00T 软件栈）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "CGTN 报道", "https://news.cgtn.com/news/2026-06-01/NVIDIA-Unitree-unveil-new-humanoid-powered-by-Isaac-GR00T-1NCWlv6VRde/index.html", "2026-06-01", f"{PARTNER_TECH}#nvidia"),
         ev(SourceType.AUTHORITATIVE_MEDIA, "宇树 H2 Plus 官方产品页", "https://www.unitree.com/cn/H2plus/", "2026-06-01", f"{PARTNER_TECH}#nvidia")],
        start=date(2026, 6, 1)),
    rel("r-deepseek-partner", RelationType.PARTNER, "UNLISTED.DeepSeek", Status.FACT, False, "宇树与DeepSeek签署战略合作备忘录，合作涉及通用AI、具身智能与大模型",
        [ev(SourceType.PRIMARY_OFFICIAL, "上海证券报·中国证券网 IPO 路演", "https://roadshow.cnstock.com/ipo/688836", "2026-08-07", f"{PARTNER_TECH}#deepseek")],
        start=date(2026, 8, 7)),
    rel("r-tianjin-partner", RelationType.PARTNER, "GOV.天津市", Status.FACT, False, "宇树与天津市/天津经开区签署战略合作协议，聚焦具身智能场景落地（安防巡检、消防救援、工业运维等）",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "人民网天津频道", "http://tj.people.com.cn/n2/2026/0527/c375366-41593167.html", "2026-05-27", f"{PARTNER_GOV}#tianjin")],
        start=date(2026, 5, 27)),
    rel("r-chengdu-partner", RelationType.PARTNER, "GOV.成都市", Status.FACT, False, "宇树与成都市签署战略合作协议，在具身智能研发、场景创新、数据采集、产教融合等方面全方位合作",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "人民网四川频道", "http://sc.people.com.cn/n2/2026/0725/c345167-41649738.html", "2026-07-25", f"{PARTNER_GOV}#chengdu")],
        start=date(2026, 7, 24)),
    rel("r-changchun-partner", RelationType.PARTNER, "GOV.长春净月高新区", Status.FACT, False, "宇树与长春净月高新区签署战略合作协议，共建 AI 教育示范区、具身智能数据采集中心等",
        [ev(SourceType.AUTHORITATIVE_MEDIA, "新浪财经（来源：机器人全球资讯）", "https://finance.sina.com.cn/wm/2026-09-03/doc-iniqnyae1083016.shtml", "2026-09-03", f"{PARTNER_GOV}#changchun")],
        start=date(2026, 8, 25)),
    rel("r-deepmind-partner", RelationType.PARTNER, "UNLISTED.GoogleDeepMind", Status.INFERENCE, False, "Google DeepMind 公开的 MuJoCo Playground 支持 Unitree G1/其模型生态；但宇树非其官宣商业合作伙伴，仅为技术生态弱关联",
        [ev(SourceType.INDUSTRY_RESEARCH, "Google DeepMind GitHub", "https://github.com/google-deepmind/mujoco_playground", "2025-01-15", f"{PARTNER_TECH}#deepmind-official")],
        start=date(2026, 9, 1), uncertainty=Uncertainty.MEDIUM),
]


def main():
    DATA.mkdir(exist_ok=True)
    ents = {k: v.model_dump(mode="json") for k, v in ENTITIES.items()}
    rels = [r.model_dump(mode="json") for r in RELATIONS]
    (DATA / "entities.json").write_text(
        json.dumps({"as_of": str(AS_OF), "entities": ents}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (DATA / "relations.json").write_text(
        json.dumps({"as_of": str(AS_OF), "count": len(rels), "relations": rels},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    core = sum(1 for r in RELATIONS if r.relevance_tier == RelevanceTier.CORE)
    supp = sum(1 for r in RELATIONS if r.relevance_tier == RelevanceTier.SUPPLEMENTARY)
    candidate = sum(1 for r in RELATIONS if r.relevance_tier == RelevanceTier.CANDIDATE)
    nv = sum(1 for r in RELATIONS if r.needs_human_validation)
    print(f"实体 {len(ents)} 个，关系 {len(rels)} 条")
    print(f"  ├─ 核心(core)        ：{core} 条")
    print(f"  ├─ 补充(supplementary)：{supp} 条")
    print(f"  └─ 候选(candidate)    ：{candidate} 条（默认不作为已确认关系展示）")
    print(f"需人工继续验证：{nv} 条")
    print(f"输出：{DATA/'entities.json'}  {DATA/'relations.json'}")


if __name__ == "__main__":
    main()
