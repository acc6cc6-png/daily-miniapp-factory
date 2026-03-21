from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


FACTORY_SOURCE_GROUPS: dict[str, tuple[str, ...]] = {
    "product": ("producthunt", "github-trending-today", "hackernews"),
    "tech": ("36kr-quick", "36kr-renqi", "ithome", "techcrunch-ai", "cnbc-tech"),
    "social": ("zhihu", "weibo", "bilibili-hot-search", "toutiao"),
}

SOURCE_GROUP_LABELS = {
    "product": "产品榜单与开发者社区",
    "tech": "科技媒体与行业快讯",
    "social": "中文热点与用户讨论",
}

SOURCE_WEIGHTS = {
    "producthunt": 1.4,
    "github-trending-today": 1.35,
    "hackernews": 1.3,
    "techcrunch-ai": 1.3,
    "cnbc-tech": 1.15,
    "36kr-renqi": 1.2,
    "36kr-quick": 1.1,
    "ithome": 1.05,
    "zhihu": 1.15,
    "weibo": 0.75,
    "bilibili-hot-search": 0.8,
    "toutiao": 0.85,
}

NOISE_TERMS = (
    "足球",
    "中超",
    "球员",
    "歌手",
    "综艺",
    "演唱会",
    "明星",
    "八卦",
    "狼队",
    "ag",
    "星期六",
    "预告",
)

COMMERCIAL_TERMS = (
    "广告",
    "商品",
    "售价",
    "客服",
    "商家",
    "电商",
    "卖家",
    "用户",
    "流量",
    "转化",
    "增长",
    "部署",
    "api",
    "订阅",
    "成本",
    "收入",
    "盈利",
    "变现",
    "shop",
    "merchant",
)

ACTION_TERMS = (
    "发布",
    "上线",
    "写",
    "publish",
    "translate",
    "deploy",
    "导入",
    "生成",
    "助手",
    "agent",
    "automation",
    "voice",
    "video",
)

HOT_TERMS = (
    "热搜",
    "热门",
    "trending",
    "top",
    "爆款",
    "排行",
    "viral",
    "trend",
)

WHY_TODAY_CLOSERS = {
    "trend-content-studio": "这说明用户不是单纯想追热点，而是在找更快把热点变成可发内容的工具。",
    "merchant-growth-copilot": "这说明商家不是只想知道发生了什么，而是想更快把热点和讨论转成成单素材。",
    "video-translate-assistant": "这说明用户不是只想看懂内容，而是想更快把视频转成可直接发布的多语版本。",
    "agent-workflow-launchpad": "这说明团队不是只想围观新 Agent，而是想更快把能力装配成业务流程。",
    "device-compare-radar": "这说明用户在找更快完成换新决策、而不是继续在参数海里反复横跳的工具。",
    "job-interview-lab": "这说明求职用户想要的不只是岗位信息，而是更快完成准备和复盘的训练工具。",
}


BLUEPRINTS: list[dict[str, Any]] = [
    {
        "id": "trend-content-studio",
        "name": "热点内容工坊",
        "positioning": "把今天的热点自动拆成标题、脚本、封面和分发文案的轻量增长工具",
        "keywords": (
            "translate",
            "visual",
            "video",
            "publish",
            "post",
            "content",
            "article",
            "blog",
            "ads",
            "promotion",
            "广告",
            "脚本",
            "文案",
            "封面",
            "热点",
            "热搜",
            "话题",
            "多语言",
            "assistant",
            "creator",
        ),
        "negative_terms": ("债市", "黄金", "制裁", "冲突", "逮捕"),
        "preferred_groups": ("product", "tech", "social"),
        "base_scores": {"demand": 54, "launch": 92, "viral": 88, "commercial": 82, "fit": 96},
        "need": "创作者、品牌和小商家每天都知道要追热点，但从线索到标题、脚本、封面、平台改写这一段最耗时。",
        "core_features": [
            {"title": "热点拆题台", "detail": "把热榜、产品榜单和科技快讯自动归并成可跟进的话题包，并给出推荐切入角度。"},
            {"title": "一键出内容", "detail": "基于选中的热点自动生成标题、短视频脚本、朋友圈文案、公众号导语和直播口播提纲。"},
            {"title": "多平台改写", "detail": "同一份内容可切成微信、小红书、抖音、公众号等不同语气和长度版本。"},
            {"title": "内容素材库", "detail": "保存热点、生成记录、封面文案和常用提示词，便于团队复用和复盘。"},
        ],
        "pages": [
            {"name": "首页 / 今日机会", "purpose": "展示今日热点榜、机会分和推荐切入角度。"},
            {"name": "选题详情页", "purpose": "查看热点摘要、适合人群、推荐内容形式和参考链接。"},
            {"name": "内容生成页", "purpose": "选择平台模板后生成标题、脚本、封面文案和行动口号。"},
            {"name": "素材库", "purpose": "管理已收藏热点、常用模板和历史生成记录。"},
        ],
        "interactions": [
            "用户打开首页后先看到系统给出的今日热点机会榜。",
            "点击某个热点后进入详情页，选择目标平台和内容形态。",
            "系统生成标题、脚本、封面文案和 CTA，用户可继续改写或收藏。",
            "生成结果进入素材库，后续可二次编辑、导出图片文案或复制发布。",
        ],
        "frontend": "首发用 Taro 或 uni-app 同时覆盖微信小程序和 H5，核心是热点卡片流、内容编辑器和模板切换组件。",
        "backend": "后端用 FastAPI 或 Next.js API Routes，负责聚合热点、调用大模型生成文案、存储模板和用户历史。",
        "audience": "内容创作者、私域运营、品牌新媒体、小商家老板。",
        "promotion": "从公众号运营群、短视频训练营、私域操盘手社群切入，先用“今日热点一键成稿”做首波传播。",
        "monetization": "基础版按日限次，专业版按月订阅，企业版可开放团队素材库和品牌模板。",
    },
    {
        "id": "merchant-growth-copilot",
        "name": "商家增长副驾",
        "positioning": "把热点、商品评论和活动文案串起来的小店增长助手",
        "keywords": ("商品", "售价", "山姆", "客服", "摊主", "广告", "电商", "商家", "转化", "小店", "带货", "团购", "私域"),
        "negative_terms": ("球员", "战争", "债市"),
        "preferred_groups": ("social", "tech"),
        "base_scores": {"demand": 50, "launch": 88, "viral": 76, "commercial": 91, "fit": 93},
        "need": "很多小商家知道热点和优惠在变，但不会把这些信号转成活动页、客服话术和成单文案。",
        "core_features": [
            {"title": "热点带货建议", "detail": "根据今天的热点和消费讨论推荐可蹭的活动切口与话术。"},
            {"title": "评论提炼", "detail": "把用户评论和问答总结成卖点、疑虑和 FAQ。"},
            {"title": "活动文案生成", "detail": "自动生成拼团文案、优惠页标题、社群海报文案和客服快捷回复。"},
            {"title": "复盘看板", "detail": "记录活动表现，便于持续优化标题、促销和回复模板。"},
        ],
        "pages": [
            {"name": "机会首页", "purpose": "显示今天值得借力的话题、平台情绪和推荐活动模板。"},
            {"name": "商品工作台", "purpose": "管理商品卖点、差评摘要和用户疑问。"},
            {"name": "文案生成页", "purpose": "生成活动标题、客服回复、社群海报文案。"},
            {"name": "复盘页", "purpose": "查看历史活动、文案表现和复用建议。"},
        ],
        "interactions": [
            "用户先选择店铺类型和主推商品。",
            "系统结合热点与历史评论生成活动方向和转化建议。",
            "用户选中模板后一键生成活动页文案、海报标题和客服话术。",
            "发布后将数据回填到复盘页，形成下一轮优化素材。",
        ],
        "frontend": "前端重点做商品卡片、模板库和一键复制操作，保证老板手机上也能快速完成。",
        "backend": "后端负责评论归因、热点推荐、模板管理和简单的成单事件统计。",
        "audience": "本地零售店、小红书店主、私域团购商家、轻电商品牌。",
        "promotion": "从本地商家群、私域运营社群和电商卖家训练营切入，以“活动文案 3 分钟出稿”做转化。",
        "monetization": "按店铺数订阅，附加评论洞察包和客服自动回复包收费。",
    },
    {
        "id": "video-translate-assistant",
        "name": "视频多语翻译助手",
        "positioning": "面向跨境卖家和创作者的视频字幕翻译、配音和封面文案工具",
        "keywords": ("translate", "language", "subtitle", "voice", "video", "multilingual", "跨境", "出海", "配音", "字幕"),
        "negative_terms": ("债市", "冲突"),
        "preferred_groups": ("product", "tech"),
        "base_scores": {"demand": 48, "launch": 66, "viral": 84, "commercial": 87, "fit": 77},
        "need": "跨境卖家和视频创作者需要更快地把中文内容转成多语种版本，但剪辑和配音外包太慢也太贵。",
        "core_features": [
            {"title": "字幕抽取", "detail": "上传视频后自动抽取音轨与字幕初稿。"},
            {"title": "多语翻译", "detail": "一键生成英文、日文、韩文等字幕版本，并保留口语风格。"},
            {"title": "配音脚本", "detail": "输出可直接录制的配音文本和封面标题建议。"},
            {"title": "发布包导出", "detail": "导出字幕文件、短文案、封面文案和标签建议。"},
        ],
        "pages": [
            {"name": "上传页", "purpose": "导入视频并选择语言与目标平台。"},
            {"name": "翻译工作台", "purpose": "校对字幕、切换语言和调整语气。"},
            {"name": "导出页", "purpose": "导出字幕、封面文案、配音稿和发布标签。"},
        ],
        "interactions": [
            "用户上传视频后先选目标语言和平台。",
            "系统生成字幕初稿并支持逐句校对。",
            "确认后自动给出配音稿、封面文案和发布标签。",
            "用户导出后直接回到剪辑工具或发布后台。",
        ],
        "frontend": "前端重点是上传、字幕对照编辑和导出体验，适合先做 H5 + 小程序轻编辑版本。",
        "backend": "后端需要音频抽取、ASR、翻译和对象存储，初期可以走异步任务队列。",
        "audience": "跨境卖家、出海内容团队、短视频代运营。",
        "promotion": "围绕出海社群、跨境卖家交流群和视频代运营渠道做投放。",
        "monetization": "按分钟数计费，叠加团队席位和多语包收费。",
    },
    {
        "id": "agent-workflow-launchpad",
        "name": "Agent 工作流速搭器",
        "positioning": "帮团队把热门 Agent 能力快速装配成可复用工作流的轻量工具",
        "keywords": ("agent", "api", "memory", "deploy", "coding", "workflow", "automation", "open source", "assistant", "工具", "openclaw"),
        "negative_terms": ("歌手", "足球"),
        "preferred_groups": ("product", "tech"),
        "base_scores": {"demand": 49, "launch": 80, "viral": 72, "commercial": 78, "fit": 61},
        "need": "团队看到很多 Agent 新产品，但从发现能力到真正跑通业务流程，中间仍然缺一个低门槛装配层。",
        "core_features": [
            {"title": "模板工作流", "detail": "提供客服、日报、线索清洗、会议摘要等现成模板。"},
            {"title": "节点装配", "detail": "通过表单方式配置模型、知识库、通知和输出格式。"},
            {"title": "运行日志", "detail": "查看每次工作流输入、输出和失败节点。"},
            {"title": "一键复用", "detail": "把工作流分享给团队成员继续二次编辑。"},
        ],
        "pages": [
            {"name": "模板首页", "purpose": "展示热门 Agent 工作流和推荐场景。"},
            {"name": "编排页", "purpose": "配置输入、节点和输出目标。"},
            {"name": "运行记录页", "purpose": "查看执行结果和失败日志。"},
        ],
        "interactions": [
            "用户从模板首页选一个最接近业务的工作流。",
            "在编排页填写模型、知识源和触发方式。",
            "试运行通过后保存为团队模板。",
            "后续可直接复制模板做小改后上线。",
        ],
        "frontend": "前端重点是可视化步骤卡片与模板市场，适合 H5 首发。",
        "backend": "后端负责工作流编排、日志存储、外部 API 调用和权限管理。",
        "audience": "中小团队运营、客服、增长和产品经理。",
        "promotion": "用模板市场和“5 分钟搭一个 Agent 流程”来获客。",
        "monetization": "按工作流调用量和团队席位计费。",
    },
    {
        "id": "device-compare-radar",
        "name": "数码对比雷达",
        "positioning": "抓新品参数、价格和卖点，帮用户快速做购机购车决策的轻工具",
        "keywords": ("小米", "比亚迪", "智能手机", "汽车", "参数", "上市", "新款", "宽胎", "马力", "续航", "起售"),
        "negative_terms": ("股市", "债市"),
        "preferred_groups": ("tech", "social"),
        "base_scores": {"demand": 44, "launch": 90, "viral": 72, "commercial": 80, "fit": 86},
        "need": "新品信息分散在媒体和社区里，普通用户很难快速看懂真正有差异的参数和值不值得换新。",
        "core_features": [
            {"title": "新品聚合", "detail": "自动聚合新品参数、价格、卖点和媒体摘要。"},
            {"title": "对比视图", "detail": "按预算、场景、续航、性能等维度横向对比。"},
            {"title": "购买建议", "detail": "针对不同人群给出推荐理由和避坑提示。"},
            {"title": "降价提醒", "detail": "收藏后接收降价和版本更新提醒。"},
        ],
        "pages": [
            {"name": "新品首页", "purpose": "展示最近热议新品和热门对比。"},
            {"name": "对比页", "purpose": "并排查看参数、价格和适用场景。"},
            {"name": "收藏页", "purpose": "管理关注产品和价格提醒。"},
        ],
        "interactions": [
            "用户选择预算和品类后进入新品页。",
            "点击任意两个产品进入对比页。",
            "系统生成适合人群、优缺点和避坑建议。",
            "用户收藏后等待后续降价或更新提醒。",
        ],
        "frontend": "前端以对比卡片和参数表为核心，适合小程序直接切入。",
        "backend": "后端主要做内容聚合、价格同步和规则化推荐，工程复杂度较低。",
        "audience": "数码消费人群、汽车增购用户、内容测评账号。",
        "promotion": "可从评测号合作、购车群和数码社区切入。",
        "monetization": "导购分成、品牌广告位和高级提醒服务。",
    },
    {
        "id": "job-interview-lab",
        "name": "面试练习舱",
        "positioning": "把岗位需求、简历问题和模拟提问串起来的求职训练小程序",
        "keywords": ("就业", "面试", "简历", "offer", "实习", "求职", "岗位", "招聘", "职场"),
        "negative_terms": ("股市", "黄金", "冲突"),
        "preferred_groups": ("social", "tech"),
        "base_scores": {"demand": 47, "launch": 86, "viral": 70, "commercial": 81, "fit": 91},
        "need": "求职用户能拿到很多岗位信息，却缺一个把简历改写、模拟追问和复盘串起来的轻量训练工具。",
        "core_features": [
            {"title": "岗位解析", "detail": "导入 JD 后自动拆出核心能力、关键词和风险点。"},
            {"title": "简历快改", "detail": "根据岗位要求改写项目表述和成就句式。"},
            {"title": "模拟追问", "detail": "生成多轮面试问题并给出答题建议。"},
            {"title": "复盘清单", "detail": "记录每次面试表现和待补能力。"},
        ],
        "pages": [
            {"name": "岗位导入页", "purpose": "输入岗位链接或 JD 文本。"},
            {"name": "简历工作台", "purpose": "修改项目表述并对照岗位要求。"},
            {"name": "模拟面试页", "purpose": "进行多轮问答和评分。"},
            {"name": "复盘页", "purpose": "沉淀错题和后续准备清单。"},
        ],
        "interactions": [
            "用户先输入岗位描述并上传简历。",
            "系统标记关键能力缺口并给出改写建议。",
            "随后进入模拟问答，生成追问和答题提示。",
            "结束后输出复盘清单和下一步补强建议。",
        ],
        "frontend": "前端核心是表单导入、双栏对照和问答聊天流，适合小程序轻交互。",
        "backend": "后端负责岗位解析、简历版本存储和模拟问答生成。",
        "audience": "应届生、转岗用户、职业教育社群。",
        "promotion": "从求职群、训练营和高校就业社群切入。",
        "monetization": "按周会员、岗位包和一对一精修附加服务收费。",
    },
]

def build_miniapp_factory(
    config: dict[str, Any],
    raw_by_source: dict[str, list[dict[str, Any]]],
    now: datetime,
    history_dir: Path | None = None,
) -> dict[str, Any]:
    pool = collect_signal_items(raw_by_source, now)
    recent_blueprints = load_recent_blueprints(history_dir)

    candidates = [score_blueprint(blueprint, pool, now, recent_blueprints) for blueprint in BLUEPRINTS]
    candidates.sort(key=lambda item: item["score"], reverse=True)

    selected = candidates[0] if candidates else fallback_candidate(now)
    if candidates:
        score_floor = selected["score"] - 3.5
        for candidate in candidates:
            if candidate["scores"]["fit"] >= 75 and candidate["score"] >= score_floor:
                selected = candidate
                break
    plan = build_heuristic_plan(selected, now)
    mode = "template"

    client = create_openai_client()
    if client is not None and selected["evidence"]:
        try:
            plan = build_ai_plan(client, selected, candidates[:3], now)
            mode = "ai"
        except Exception as exc:  # noqa: BLE001
            print(f"[miniapp-factory][ai] failed -> {exc}")

    return {
        "title": "AI 自动造小程序系统",
        "subtitle": "每天从真实热点、产品趋势和用户讨论里，筛出一个最值得做的小程序方案。",
        "generatedAt": clock(now),
        "windowLabel": build_window_label(now),
        "mode": mode,
        "summary": build_factory_summary(selected),
        "scores": selected["scores"],
        "todayPlan": plan,
        "evidenceSignals": selected["evidence"],
        "candidateBoard": [build_candidate_card(item, selected["blueprint"]["id"]) for item in candidates[:3]],
        "engine": build_engine_meta(pool, recent_blueprints, config),
    }


def collect_signal_items(raw_by_source: dict[str, list[dict[str, Any]]], now: datetime) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    window_start = (now - timedelta(hours=48)).replace(tzinfo=None)

    for group, source_ids in FACTORY_SOURCE_GROUPS.items():
        for source_id in source_ids:
            for rank, item in enumerate(raw_by_source.get(source_id, [])[:20], start=1):
                title = clean_text(item.get("title"))
                if not title or is_noise_title(title):
                    continue

                normalized = normalize_text(title)
                if normalized in seen_titles:
                    continue

                published_at = clean_text(item.get("publishedAt")) or None
                published_dt = parse_timestamp(published_at)
                if published_dt is not None and published_dt < window_start:
                    continue

                seen_titles.add(normalized)
                items.append(
                    {
                        "title": title,
                        "normalized": normalized,
                        "url": item.get("url") or "#",
                        "source": clean_text(item.get("sourceLabel")) or source_id,
                        "sourceId": source_id,
                        "group": group,
                        "publishedAt": published_at,
                        "rank": rank,
                        "sourceWeight": SOURCE_WEIGHTS.get(source_id, 1.0),
                    }
                )

    return items


def score_blueprint(
    blueprint: dict[str, Any],
    pool: list[dict[str, Any]],
    now: datetime,
    recent_blueprints: list[str],
) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    matched_groups: set[str] = set()
    matched_sources: set[str] = set()
    matched_terms: set[str] = set()
    commercial_hits = 0
    hot_hits = 0
    action_hits = 0

    for item in pool:
        matches = keyword_hits(item["normalized"], blueprint["keywords"])
        if not matches:
            continue

        negative_hits = keyword_hits(item["normalized"], blueprint.get("negative_terms", ()))
        evidence_score = 12 + len(matches) * 8
        evidence_score += max(0, int(item["sourceWeight"] * 6))
        evidence_score += max(0, 8 - item["rank"])

        if item["group"] in blueprint.get("preferred_groups", ()):
            evidence_score += 5

        if has_any(item["normalized"], COMMERCIAL_TERMS):
            commercial_hits += 1
            evidence_score += 5
        if has_any(item["normalized"], ACTION_TERMS):
            action_hits += 1
            evidence_score += 4
        if has_any(item["normalized"], HOT_TERMS):
            hot_hits += 1
            evidence_score += 3
        if negative_hits:
            evidence_score -= len(negative_hits) * 5

        if evidence_score < 16:
            continue

        matched_groups.add(item["group"])
        matched_sources.add(item["sourceId"])
        matched_terms.update(matches)

        evidence.append(
            {
                "title": item["title"],
                "url": item["url"],
                "source": item["source"],
                "sourceId": item["sourceId"],
                "group": item["group"],
                "groupLabel": SOURCE_GROUP_LABELS[item["group"]],
                "publishedAt": item["publishedAt"],
                "score": evidence_score,
                "matchTerms": matches[:3],
                "reason": build_signal_reason(item["title"], matches),
            }
        )

    evidence.sort(key=lambda item: (item["score"], item.get("publishedAt") or ""), reverse=True)
    evidence = diversify_evidence(evidence, 6)

    demand = blueprint["base_scores"]["demand"]
    demand += min(20, len(matched_terms) * 2)
    demand += min(18, len(matched_groups) * 8)
    demand += min(16, len(evidence) * 3)
    demand += min(10, commercial_hits * 2)
    demand += min(8, action_hits * 2)
    if len(matched_groups) < 2:
        demand -= 10
    if not evidence:
        demand = max(18, demand - 28)

    launch = blueprint["base_scores"]["launch"]
    viral = min(100, blueprint["base_scores"]["viral"] + min(8, hot_hits * 2))
    commercial = min(100, blueprint["base_scores"]["commercial"] + min(8, commercial_hits * 2))
    fit = blueprint["base_scores"]["fit"]

    repeat_penalty = 0
    if blueprint["id"] in recent_blueprints[:3]:
        repeat_penalty = 20
    elif blueprint["id"] in recent_blueprints[:7]:
        repeat_penalty = 12
    elif blueprint["id"] in recent_blueprints:
        repeat_penalty = 6

    total = demand * 0.38 + launch * 0.18 + viral * 0.18 + commercial * 0.18 + fit * 0.08
    total -= repeat_penalty

    return {
        "blueprint": blueprint,
        "score": round(total, 1),
        "scores": {
            "demand": clamp_score(demand),
            "launch": clamp_score(launch),
            "viral": clamp_score(viral),
            "commercial": clamp_score(commercial),
            "fit": clamp_score(fit),
        },
        "evidence": evidence,
        "matchedGroups": sorted(matched_groups),
        "matchedSources": sorted(matched_sources),
        "matchedTerms": sorted(matched_terms),
        "repeatPenalty": repeat_penalty,
        "windowLabel": build_window_label(now),
    }


def build_heuristic_plan(candidate: dict[str, Any], now: datetime) -> dict[str, Any]:
    blueprint = candidate["blueprint"]
    evidence = candidate["evidence"][:4]
    evidence_titles = "；".join(f"{item['source']}：{shorten(item['title'], 28)}" for item in evidence)

    why_today = (
        f"今天适合做，是因为最近 48 小时的高信号源同时在放大“{blueprint['positioning']}”这条需求。"
        f"当前命中的关键线索包括：{evidence_titles or '产品榜单、科技媒体和中文讨论都在抬升相关需求'}。"
        f"{WHY_TODAY_CLOSERS.get(blueprint['id'], '这说明用户不是单纯在看热闹，而是在找更快把信号转成结果的工具。')}"
    )

    return {
        "blueprintId": blueprint["id"],
        "name": blueprint["name"],
        "positioning": blueprint["positioning"],
        "coreNeed": blueprint["need"],
        "whyToday": why_today,
        "marketBasis": build_market_basis(candidate),
        "coreFeatures": blueprint["core_features"],
        "pageStructure": blueprint["pages"],
        "interactionLogic": blueprint["interactions"],
        "implementation": {
            "frontend": blueprint["frontend"],
            "backend": blueprint["backend"],
            "platforms": ["微信小程序", "抖音小程序", "H5", "App 基础壳"],
        },
        "audience": blueprint["audience"],
        "promotion": blueprint["promotion"],
        "monetization": blueprint["monetization"],
        "generatedAt": clock(now),
    }


def build_ai_plan(
    client: Any,
    candidate: dict[str, Any],
    top_candidates: list[dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "positioning": {"type": "string"},
            "coreNeed": {"type": "string"},
            "whyToday": {"type": "string"},
            "marketBasis": {
                "type": "array",
                "minItems": 3,
                "maxItems": 4,
                "items": {"type": "string"},
            },
            "coreFeatures": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["title", "detail"],
                    "additionalProperties": False,
                },
            },
            "pageStructure": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "purpose": {"type": "string"},
                    },
                    "required": ["name", "purpose"],
                    "additionalProperties": False,
                },
            },
            "interactionLogic": {
                "type": "array",
                "minItems": 4,
                "maxItems": 6,
                "items": {"type": "string"},
            },
            "implementation": {
                "type": "object",
                "properties": {
                    "frontend": {"type": "string"},
                    "backend": {"type": "string"},
                },
                "required": ["frontend", "backend"],
                "additionalProperties": False,
            },
            "audience": {"type": "string"},
            "promotion": {"type": "string"},
            "monetization": {"type": "string"},
        },
        "required": [
            "positioning",
            "coreNeed",
            "whyToday",
            "marketBasis",
            "coreFeatures",
            "pageStructure",
            "interactionLogic",
            "implementation",
            "audience",
            "promotion",
            "monetization",
        ],
        "additionalProperties": False,
    }

    response = client.responses.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
        input=build_ai_prompt(candidate, top_candidates, now),
        text={
            "format": {
                "type": "json_schema",
                "name": "daily_miniapp_factory_plan",
                "strict": True,
                "schema": schema,
            }
        },
    )
    payload = json.loads(response.output_text)
    return {
        "blueprintId": candidate["blueprint"]["id"],
        "name": candidate["blueprint"]["name"],
        "positioning": clean_text(payload["positioning"]),
        "coreNeed": clean_text(payload["coreNeed"]),
        "whyToday": clean_text(payload["whyToday"]),
        "marketBasis": [clean_text(item) for item in payload["marketBasis"]],
        "coreFeatures": [
            {"title": clean_text(item["title"]), "detail": clean_text(item["detail"])}
            for item in payload["coreFeatures"]
        ],
        "pageStructure": [
            {"name": clean_text(item["name"]), "purpose": clean_text(item["purpose"])}
            for item in payload["pageStructure"]
        ],
        "interactionLogic": [clean_text(item) for item in payload["interactionLogic"]],
        "implementation": {
            "frontend": clean_text(payload["implementation"]["frontend"]),
            "backend": clean_text(payload["implementation"]["backend"]),
            "platforms": ["微信小程序", "抖音小程序", "H5", "App 基础壳"],
        },
        "audience": clean_text(payload["audience"]),
        "promotion": clean_text(payload["promotion"]),
        "monetization": clean_text(payload["monetization"]),
        "generatedAt": clock(now),
    }

def build_ai_prompt(candidate: dict[str, Any], top_candidates: list[dict[str, Any]], now: datetime) -> str:
    blueprint = candidate["blueprint"]
    evidence_lines = "\n".join(
        f"- [{item['source']}] {item['title']}（来源组：{item['groupLabel']}，命中词：{', '.join(item['matchTerms']) or '信号'}）"
        for item in candidate["evidence"][:6]
    )
    alternatives = "\n".join(
        f"- {item['blueprint']['name']}：总分 {item['score']}，需求 {item['scores']['demand']}，上线速度 {item['scores']['launch']}"
        for item in top_candidates
    )
    return f"""
你是中文 AI 产品架构师兼增长负责人。你要基于“真实市场信号”输出一份今天最适合做的小程序方案。

现在时间：{clock(now)}
最终入选方案：{blueprint['name']}
预设定位：{blueprint['positioning']}
预设核心需求：{blueprint['need']}

今天命中的真实信号：
{evidence_lines}

候选池对比：
{alternatives}

输出要求：
1. 只基于这些线索做判断，不要虚构数据、榜单名次或用户数量。
2. 语气直接、可开发、可落地，不要写空话。
3. 小程序要偏轻量、成本可控、能先做微信小程序与 H5，再扩到抖音和 App。
4. whyToday 必须说明“为什么今天适合做”，带出真实市场依据。
5. implementation 中前端和后端各写一段，强调首发技术路线。
6. 全部用简体中文。
""".strip()


def build_market_basis(candidate: dict[str, Any]) -> list[str]:
    evidence = candidate["evidence"][:4]
    basis = []
    for item in evidence:
        basis.append(
            f"{item['source']} 当前出现“{shorten(item['title'], 42)}”这类信号，说明相关需求正在被放大。"
        )
    if len(candidate["matchedGroups"]) >= 2:
        groups = "、".join(SOURCE_GROUP_LABELS[group] for group in candidate["matchedGroups"])
        basis.append(f"信号同时来自 {groups}，不是单一来源的偶发热度。")
    basis.append(
        f"这条方案的上线速度分为 {candidate['scores']['launch']}，更适合用轻交互页面和模板化生成先跑通。"
    )
    return basis[:4]


def build_factory_summary(candidate: dict[str, Any]) -> str:
    blueprint = candidate["blueprint"]
    evidence = candidate["evidence"][:2]
    if not evidence:
        return f"今天先落在「{blueprint['name']}」，因为它仍然是当前最适合小程序首发、成本最低的一类方案。"
    signal_text = "、".join(shorten(item["title"], 24) for item in evidence)
    return (
        f"今天最值得做的是「{blueprint['name']}」。当前高信号源正在同时放大 {blueprint['positioning']} 这类需求，"
        f"核心触发点来自：{signal_text}。"
    )


def build_candidate_card(candidate: dict[str, Any], selected_blueprint_id: str) -> dict[str, Any]:
    blueprint = candidate["blueprint"]
    note = "今天的头号方案。"
    if blueprint["id"] != selected_blueprint_id:
        if candidate["scores"]["fit"] < 75:
            note = "信号不弱，但更像工具站或 Web 产品，不如头号方案适合小程序先发。"
        elif candidate["scores"]["launch"] < 75:
            note = "需求存在，但首发工程量更重，适合排进下一轮候选池。"
        else:
            note = "方向成立，不过今天的跨源验证和传播性略弱于头号方案。"
    return {
        "name": blueprint["name"],
        "positioning": blueprint["positioning"],
        "score": candidate["score"],
        "scores": candidate["scores"],
        "note": note,
    }


def build_engine_meta(
    pool: list[dict[str, Any]],
    recent_blueprints: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    group_summary = []
    for group, source_ids in FACTORY_SOURCE_GROUPS.items():
        count = sum(1 for item in pool if item["group"] == group)
        group_summary.append(
            {
                "name": SOURCE_GROUP_LABELS[group],
                "count": count,
                "sources": [config["sources"][source_id]["label"] for source_id in source_ids if source_id in config["sources"]],
            }
        )

    return {
        "sources": group_summary,
        "collectionRules": [
            "优先抓产品榜单、科技媒体、中文讨论三类高信号源，而不是只看单个平台热搜。",
            "同一标题会先去重，再按商业价值、动作性和跨源重复度加权。",
            "最近 48 小时优先，旧信号自动降权，保证方案更贴近今天的真实机会。",
        ],
        "qualityRules": [
            "至少要求两个来源组同时命中，避免被单一热点误导。",
            "自动过滤体育、明星、纯情绪八卦等不适合做工具产品的噪声。",
            "读取最近历史方案，对高相似方向降权，尽量减少重复生成。",
        ],
        "buildRules": [
            "优先选择微信小程序和 H5 可同时落地的方向，再考虑抖音小程序和 App 壳。",
            "优先模板化、轻数据、可订阅的产品，而不是重服务、重审核或重线下履约的产品。",
            f"当前历史记忆里已有 {len(recent_blueprints)} 条已生成方向记录，会参与去重。",
        ],
    }


def load_recent_blueprints(history_dir: Path | None) -> list[str]:
    if history_dir is None:
        return []
    index_path = history_dir / "index.json"
    if not index_path.exists():
        return []

    try:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    recent: list[str] = []
    for entry in entries[:21]:
        raw_path = clean_text(entry.get("path"))
        if not raw_path:
            continue
        digest_path = history_dir.parent.parent / raw_path
        if not digest_path.exists():
            continue
        try:
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        blueprint_id = clean_text(digest.get("miniappFactory", {}).get("todayPlan", {}).get("blueprintId"))
        if blueprint_id:
            recent.append(blueprint_id)
    return recent


def fallback_candidate(now: datetime) -> dict[str, Any]:
    blueprint = BLUEPRINTS[0]
    return {
        "blueprint": blueprint,
        "score": 60.0,
        "scores": {"demand": 48, "launch": 92, "viral": 82, "commercial": 80, "fit": 96},
        "evidence": [],
        "matchedGroups": [],
        "matchedSources": [],
        "matchedTerms": [],
        "repeatPenalty": 0,
        "windowLabel": build_window_label(now),
    }


def diversify_evidence(evidence: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    diversified: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for item in evidence:
        if item["sourceId"] in seen_sources and len(diversified) < max(3, limit - 1):
            continue
        diversified.append(item)
        seen_sources.add(item["sourceId"])
        if len(diversified) >= limit:
            break
    return diversified


def build_signal_reason(title: str, matches: list[str]) -> str:
    if not matches:
        return "说明今天这类需求仍有活跃讨论。"
    return f"标题直接命中“{matches[0]}”相关需求，适合转成轻工具功能。"


def keyword_hits(text: str, keywords: tuple[str, ...] | list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.lower() in text]


def has_any(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def is_noise_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term.lower() in normalized for term in NOISE_TERMS)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_text(value: str) -> str:
    cleaned = clean_text(value).lower()
    return cleaned.replace("–", "-").replace("—", "-")


def shorten(text: str, size: int) -> str:
    text = clean_text(text)
    return text if len(text) <= size else text[: max(0, size - 1)] + "…"


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def clock(now: datetime) -> str:
    return now.strftime("%Y-%m-%d %H:%M")


def build_window_label(now: datetime) -> str:
    start = now - timedelta(hours=48)
    return f"{start.strftime('%m-%d %H:%M')} - {now.strftime('%m-%d %H:%M')}"


def clamp_score(value: float | int) -> int:
    return max(0, min(100, int(round(value))))


def create_openai_client() -> Any | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)
