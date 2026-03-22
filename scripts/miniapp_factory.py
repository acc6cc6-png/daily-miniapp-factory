from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


TZ = timezone(timedelta(hours=8))


FACTORY_SOURCE_GROUPS: dict[str, tuple[str, ...]] = {
    "product": ("producthunt", "github-trending-today", "hackernews"),
    "operator": ("36kr-quick", "36kr-renqi", "ithome", "techcrunch-ai", "cnbc-tech"),
    "market": ("wallstreetcn-hot", "cls-hot", "cls-depth", "cnbc-business", "guardian-business"),
    "demand": ("zhihu", "toutiao", "thepaper", "xueqiu-hotstock"),
}

SOURCE_GROUP_LABELS = {
    "product": "产品榜单与开发者社区",
    "operator": "科技媒体与创业动向",
    "market": "市场与商业变动",
    "demand": "真实用户讨论与消费意图",
}

SOURCE_WEIGHTS = {
    "producthunt": 1.45,
    "github-trending-today": 1.4,
    "hackernews": 1.35,
    "techcrunch-ai": 1.3,
    "cnbc-tech": 1.2,
    "36kr-renqi": 1.2,
    "36kr-quick": 1.1,
    "ithome": 1.05,
    "wallstreetcn-hot": 1.25,
    "cls-hot": 1.22,
    "cls-depth": 1.28,
    "cnbc-business": 1.18,
    "guardian-business": 1.08,
    "zhihu": 1.08,
    "toutiao": 0.88,
    "thepaper": 0.95,
    "xueqiu-hotstock": 0.92,
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
    "电影票房",
    "恋情",
    "ag",
    "lol",
    "cos",
    "周边",
    "预告",
    "抽卡",
    "手游",
)

INTENT_TERMS = (
    "用户",
    "客户",
    "商家",
    "企业",
    "卖家",
    "创作者",
    "团队",
    "开发者",
    "老板",
    "岗位",
    "求职",
    "采购",
    "转化",
    "复购",
    "流量",
    "投放",
    "成本",
    "利润",
    "收益",
    "交付",
    "需求",
)

PAIN_TERMS = (
    "涨价",
    "下滑",
    "压力",
    "难",
    "太慢",
    "缺",
    "问题",
    "焦虑",
    "降本",
    "提效",
    "卡住",
    "复杂",
    "碎片化",
    "分散",
    "混乱",
    "排队",
    "等待",
)

COMMERCIAL_TERMS = (
    "广告",
    "商品",
    "售价",
    "客服",
    "电商",
    "小店",
    "私域",
    "带货",
    "会员",
    "订阅",
    "收入",
    "盈利",
    "变现",
    "增长",
    "线索",
    "成交",
    "复盘",
    "运营",
)

CHANGE_TERMS = (
    "发布",
    "上线",
    "开源",
    "更新",
    "升级",
    "接入",
    "开放",
    "支持",
    "推出",
    "新增",
    "定价",
    "调价",
    "政策",
    "规则",
    "平台",
)

ACTION_TERMS = (
    "生成",
    "自动",
    "workflow",
    "agent",
    "copilot",
    "助手",
    "搭建",
    "部署",
    "发布",
    "翻译",
    "剪辑",
    "比价",
    "训练",
    "改写",
    "推荐",
)

DISPLAY_TERMS = {
    "agent": "Agent",
    "api": "API",
    "workflow": "流程",
    "automation": "自动化",
    "copilot": "副驾",
    "translate": "多语",
    "subtitle": "字幕",
    "video": "视频",
    "跨境": "跨境",
    "商家": "商家",
    "电商": "电商",
    "客服": "客服",
    "私域": "私域",
    "参数": "参数",
    "价格": "价格",
    "购机": "换新",
    "简历": "简历",
    "面试": "面试",
    "求职": "求职",
    "热点": "热点",
    "内容": "内容",
    "发布": "发布",
    "调价": "调价",
    "平台": "平台",
    "规则": "规则",
    "更新": "更新",
    "开源": "开源",
    "手机": "手机",
    "汽车": "汽车",
    "新品": "新品",
    "offer": "Offer",
}

DEFAULT_PREFIXES = {
    "change-translation-console": "平台",
    "merchant-reaction-engine": "商家",
    "agent-kit-foundry": "Agent",
    "crossborder-delivery-relay": "多语",
    "decision-intel-radar": "换新",
    "career-acceleration-lab": "求职",
}

THEMES: list[dict[str, Any]] = [
    {
        "id": "change-translation-console",
        "name_suffix": "变化转译台",
        "tagline": "把平台、产品和行业变化直接翻成今天要执行的动作包。",
        "market_shift": "变化速度已经快过大多数团队的理解和执行速度。",
        "demand_gap": "大家缺的不是又一篇新闻解读，而是今天该改什么、发什么、接什么的执行答案。",
        "keywords": (
            "涨价",
            "调价",
            "升级",
            "更新",
            "开放",
            "接入",
            "新规",
            "规则",
            "平台",
            "api",
            "发布",
            "上线",
            "workflow",
            "agent",
        ),
        "negative_terms": ("足球", "歌手", "演员", "制裁", "伊朗", "冲突", "战争", "石油"),
        "preferred_groups": ("market", "operator", "product"),
        "base_scores": {"demand": 58, "buildability": 83, "boldness": 86, "ai": 90},
        "target_users": "SaaS 创始人、运营负责人、私域操盘手、行业观察型团队。",
        "scene": "每天早上看完变化后，30 分钟内自动生成动作清单、客户通知和内部待办。",
        "first_version": "先做变化订阅、动作生成、通知模板 3 个模块，不碰复杂协同。",
        "modules": [
            {"title": "变化译码器", "detail": "把发布、涨价、规则调整、开放接口等变化统一拆成影响范围、风险点和可执行动作。"},
            {"title": "动作包生成器", "detail": "自动生成客户通知、销售话术、Landing Page 修改建议和内部执行清单。"},
            {"title": "行业模板库", "detail": "按 SaaS、私域、电商、本地服务等场景沉淀可复用模板。"},
            {"title": "追踪看板", "detail": "记录变化已读、动作是否完成、后续是否需要二次跟进。"},
        ],
        "pages": [
            {"name": "今日变化页", "purpose": "展示今天真正需要处理的变化，而不是铺满资讯。"},
            {"name": "动作生成页", "purpose": "按角色生成客户通知、销售话术和内部待办。"},
            {"name": "模板页", "purpose": "沉淀行业模板和常用动作包。"},
            {"name": "追踪页", "purpose": "查看哪些变化已处理、哪些还在堆积。"},
        ],
        "workflow": [
            "系统先按 07:00 / 12:30 对应时间窗抓取变化信号，再去重、分类、标记影响范围。",
            "用户打开后直接看到今天必须处理的变化，而不是一屏新闻。",
            "选中某条变化后，一键生成客户通知、执行清单和页面修改建议。",
            "执行结果沉淀进模板库，下一次同类变化直接复用。",
        ],
        "frontend": "先做 H5 + 微信小程序的变化列表、动作模板和一键复制交付页，减少复杂输入。",
        "backend": "后端用 FastAPI 聚合信号、调用模型做变化翻译、保存动作模板与执行记录。",
        "distribution": "从 SaaS 创始人群、私域增长社群、行业操盘手群切入，以“每天 7 点给你今天该动的 3 件事”做传播。",
        "monetization": "按行业专题和团队席位订阅收费，附加企业内部模板库增购。",
        "prompt_goal": "做一个每天 7 点把行业变化翻译成动作包的产品首版",
    },
    {
        "id": "merchant-reaction-engine",
        "name_suffix": "生意动作机",
        "tagline": "不是帮商家看热点，而是帮商家今天就把热点变成订单动作。",
        "market_shift": "流量更碎、商品更同质，商家需要的是即时动作而不是更多灵感。",
        "demand_gap": "市场在找能立刻变成文案、客服回复和活动页的执行工具。",
        "keywords": (
            "商家",
            "电商",
            "商品",
            "客服",
            "小店",
            "团购",
            "带货",
            "私域",
            "成交",
            "转化",
            "评论",
            "优惠",
            "活动",
        ),
        "negative_terms": ("球员", "演唱会", "股市"),
        "preferred_groups": ("demand", "operator", "market"),
        "base_scores": {"demand": 61, "buildability": 86, "boldness": 80, "ai": 88},
        "target_users": "小商家、私域团购主理人、本地零售店主、轻电商品牌。",
        "scene": "每天早上生成一套可直接发出去的活动动作包，不再临时想标题和话术。",
        "first_version": "先做话题建议、文案生成、评论提炼，不碰复杂 ERP。",
        "modules": [
            {"title": "生意机会雷达", "detail": "把消费讨论、平台动向和热点话题合成今天可借力的销售切口。"},
            {"title": "活动动作包", "detail": "自动产出活动标题、海报文案、客服快捷回复和社群口播稿。"},
            {"title": "评论转卖点", "detail": "把用户评论和问答提炼成卖点、异议和 FAQ。"},
            {"title": "复盘回收站", "detail": "记录哪些话术出单、哪些活动没反应，方便第二天继续优化。"},
        ],
        "pages": [
            {"name": "今日动作页", "purpose": "展示今天最值得发的活动方向和推荐动作。"},
            {"name": "商品工作台", "purpose": "管理商品卖点、差评、常见问题和素材。"},
            {"name": "文案生成页", "purpose": "生成海报文案、活动标题、客服回复和社群话术。"},
            {"name": "复盘页", "purpose": "记录活动结果，形成下一轮动作建议。"},
        ],
        "workflow": [
            "系统合并消费讨论、产品动向和商家相关变化，识别今天值得借的切口。",
            "用户选择商品后，系统生成活动文案、客服回复和社群口播稿。",
            "生成内容一键复制出去，避免老板每天重写一遍。",
            "活动结果回流后，系统给出明天继续跟进还是停止投放的建议。",
        ],
        "frontend": "优先做手机端单手可完成的商家工作台，重点是模板切换、快速复制和结果回看。",
        "backend": "后端负责评论归因、热点匹配、模板管理和简单成效记录。",
        "distribution": "从本地商家群、私域运营训练营、电商卖家群切入，用“今天直接能发的活动动作包”获客。",
        "monetization": "按店铺数和动作包次数收费，高级版开放评论洞察与客服自动回复。",
        "prompt_goal": "做一个帮商家在当天把热点变成订单动作的工具首版",
    },
    {
        "id": "agent-kit-foundry",
        "name_suffix": "装配厂",
        "tagline": "把新 Agent、新 API、新开源能力翻成可卖、可跑的垂直小产品。",
        "market_shift": "AI 能力发布越来越快，但真正能变成业务价值的装配层仍然稀缺。",
        "demand_gap": "团队不是缺 Agent 新闻，而是缺一个能 1 小时拼出行业工作流的制造台。",
        "keywords": (
            "agent",
            "workflow",
            "automation",
            "api",
            "open source",
            "开源",
            "memory",
            "deploy",
            "coding",
            "copilot",
            "assistant",
        ),
        "negative_terms": ("歌手", "足球"),
        "preferred_groups": ("product", "operator"),
        "base_scores": {"demand": 55, "buildability": 79, "boldness": 91, "ai": 94},
        "target_users": "一人公司、独立开发者、小团队产品经理、自动化顾问。",
        "scene": "早上看到新能力，下午就能拼成一个垂直工作流 Demo 去试单。",
        "first_version": "先做垂直模板市场、表单式节点配置、运行回放，不碰复杂权限体系。",
        "modules": [
            {"title": "行业模板市场", "detail": "直接提供销售跟进、客服总结、内容分发、报价整理等现成模板。"},
            {"title": "节点装配器", "detail": "通过表单串起模型、知识源、Webhook、通知和输出格式。"},
            {"title": "运行回放", "detail": "看到每次输入、输出和失败节点，方便快速改模板。"},
            {"title": "交付打包器", "detail": "把模板导出成 H5、小程序骨架或可售卖的服务包。"},
        ],
        "pages": [
            {"name": "模板首页", "purpose": "展示今天最值得拼装的垂直 Agent 模板。"},
            {"name": "装配页", "purpose": "配置输入、模型、知识源和输出动作。"},
            {"name": "运行回放页", "purpose": "查看执行记录和失败节点。"},
            {"name": "交付页", "purpose": "导出 Demo、模板包和复用说明。"},
        ],
        "workflow": [
            "系统先把新发布的 Agent / API / 开源能力聚合成可装配能力列表。",
            "用户从模板首页挑一个最接近业务的方向进入装配页。",
            "填入知识源和输出动作后，立即生成可运行 Demo。",
            "跑通后将模板打包，继续卖给客户或做成自己的微 SaaS。",
        ],
        "frontend": "前端重点是模板卡片、节点配置和运行回放，首发更适合 H5 + 小程序轻配置台。",
        "backend": "后端负责工作流编排、日志存储、模型调用、外部 API 对接和模板版本管理。",
        "distribution": "从独立开发者社区、AI 自动化社群、产品经理群切入，用“今天就能拼一个能卖的 Agent”获客。",
        "monetization": "按模板数、调用量和团队席位收费，另卖行业专用模板包。",
        "prompt_goal": "做一个把新 AI 能力快速装配成垂直产品的系统首版",
    },
    {
        "id": "crossborder-delivery-relay",
        "name_suffix": "多语交付站",
        "tagline": "把内容、多语、平台适配和交付包一次性做完。",
        "market_shift": "跨平台分发与多语输出成本在下降，但多数团队的交付链路仍然断裂。",
        "demand_gap": "用户不想再外包切字幕、改文案、做封面，他们想直接拿到可发布包。",
        "keywords": (
            "translate",
            "language",
            "subtitle",
            "voice",
            "video",
            "multilingual",
            "跨境",
            "出海",
            "配音",
            "字幕",
            "localization",
        ),
        "negative_terms": ("债市", "冲突"),
        "preferred_groups": ("product", "operator", "market"),
        "base_scores": {"demand": 53, "buildability": 71, "boldness": 84, "ai": 89},
        "target_users": "跨境卖家、出海内容团队、短视频代运营、海外营销团队。",
        "scene": "同一条内容需要在多个语言和多个平台当天交付时，系统直接出完整发布包。",
        "first_version": "先做字幕抽取、多语改写、发布包导出，不做复杂剪辑器。",
        "modules": [
            {"title": "字幕抽取器", "detail": "上传视频或音频后自动抽出字幕初稿和时间轴。"},
            {"title": "多语改写器", "detail": "按平台语气生成英文、日文、韩文等版本，不只是字面翻译。"},
            {"title": "发布包导出", "detail": "一次输出字幕文件、封面文案、标题、标签和配音稿。"},
            {"title": "交付清单", "detail": "记录每个平台已交付版本与更新时间，方便团队协作。"},
        ],
        "pages": [
            {"name": "上传页", "purpose": "导入素材并选择目标语言与平台。"},
            {"name": "改写工作台", "purpose": "校对字幕、切换语言和调整语气。"},
            {"name": "发布包页", "purpose": "导出字幕、封面文案、标签和配音稿。"},
            {"name": "交付页", "purpose": "追踪每个平台的已交付版本。"},
        ],
        "workflow": [
            "用户上传素材后选择语言和目标平台。",
            "系统自动生成字幕、多语文案和平台差异化版本。",
            "确认后导出完整发布包，而不是单独导出一份字幕。",
            "后续所有版本统一沉淀到交付清单，减少返工。",
        ],
        "frontend": "前端重点是上传、对照编辑和导出体验，先做 H5，再做小程序轻编辑入口。",
        "backend": "后端负责音频抽取、ASR、翻译、任务队列和对象存储。",
        "distribution": "围绕跨境卖家群、内容代运营社群、海外营销团队做投放，用“当天直接交付多语发布包”切入。",
        "monetization": "按分钟数和导出次数计费，团队版按席位收费。",
        "prompt_goal": "做一个帮团队当天交付多语内容包的产品首版",
    },
    {
        "id": "decision-intel-radar",
        "name_suffix": "决策雷达",
        "tagline": "抓住新品、价格和对比信号，替用户省掉反复查资料的时间。",
        "market_shift": "新品密集发布、价格波动更快，用户决策成本正在升高。",
        "demand_gap": "市场缺的不是更多测评，而是更快完成选择、收藏和提醒的决策工具。",
        "keywords": (
            "小米",
            "手机",
            "汽车",
            "参数",
            "价格",
            "起售",
            "上市",
            "续航",
            "配置",
            "对比",
            "新品",
        ),
        "negative_terms": ("股市", "债市"),
        "preferred_groups": ("market", "operator", "demand"),
        "base_scores": {"demand": 49, "buildability": 88, "boldness": 72, "ai": 78},
        "target_users": "换新用户、数码消费人群、汽车增购用户、测评账号。",
        "scene": "新品扎堆发布时，用户想几分钟内做出是否关注、是否等待、是否下单的判断。",
        "first_version": "先做参数聚合、对比视图、购买建议和价格提醒，不碰交易闭环。",
        "modules": [
            {"title": "新品聚合", "detail": "自动抓取新品参数、价格、卖点和媒体摘要。"},
            {"title": "对比视图", "detail": "按预算、性能、续航、空间等维度直接横向对比。"},
            {"title": "购买建议", "detail": "针对不同人群给出推荐理由、避坑提示和等待建议。"},
            {"title": "价格提醒", "detail": "收藏后接收调价、版本更新和替代选择提醒。"},
        ],
        "pages": [
            {"name": "新品页", "purpose": "展示今天真正值得看的新品和热对比。"},
            {"name": "对比页", "purpose": "并排查看参数、价格和适用人群。"},
            {"name": "收藏页", "purpose": "管理关注产品和提醒条件。"},
        ],
        "workflow": [
            "系统聚合新品与价格变化，并按人群和预算打标签。",
            "用户选中两个或多个产品后进入对比页。",
            "系统输出适合人群、优缺点和等待建议。",
            "用户收藏后持续收到调价与替代提醒。",
        ],
        "frontend": "前端核心是参数对比卡片、预算筛选和收藏提醒，天然适合小程序首发。",
        "backend": "后端主要做内容聚合、价格同步和规则化推荐，工程复杂度较低。",
        "distribution": "从数码社群、购车群、测评合作账号切入，以“几分钟完成选择”做传播。",
        "monetization": "导购分成、品牌赞助位和高级提醒服务。",
        "prompt_goal": "做一个帮助用户快速完成换新决策的工具首版",
    },
    {
        "id": "career-acceleration-lab",
        "name_suffix": "上岸训练舱",
        "tagline": "把岗位变化、简历改写和模拟提问串成闭环，不再只看招聘信息。",
        "market_shift": "求职竞争仍强，用户要的是准备效率和反馈闭环，而不是更多岗位资讯。",
        "demand_gap": "市场需要一个能把 JD、简历、追问和复盘串起来的训练工具。",
        "keywords": (
            "就业",
            "面试",
            "简历",
            "offer",
            "实习",
            "求职",
            "岗位",
            "招聘",
            "职场",
            "简历",
        ),
        "negative_terms": ("股市", "冲突"),
        "preferred_groups": ("demand", "operator"),
        "base_scores": {"demand": 51, "buildability": 87, "boldness": 76, "ai": 86},
        "target_users": "应届生、转岗用户、职业教育社群、求职训练营。",
        "scene": "看到岗位变化后，立刻把简历、模拟问答和复盘都跑一遍。",
        "first_version": "先做岗位解析、简历快改、模拟追问和复盘清单，不做招聘平台。",
        "modules": [
            {"title": "岗位译码器", "detail": "导入 JD 后自动拆出关键能力、关键词和风险项。"},
            {"title": "简历快改", "detail": "根据目标岗位改写项目表述和成果句式。"},
            {"title": "模拟追问", "detail": "生成多轮面试问题、追问和答题建议。"},
            {"title": "复盘清单", "detail": "沉淀每次表现、待补能力和下一次冲刺任务。"},
        ],
        "pages": [
            {"name": "岗位导入页", "purpose": "输入岗位链接或 JD 文本。"},
            {"name": "简历工作台", "purpose": "修改项目表述并对照岗位要求。"},
            {"name": "模拟面试页", "purpose": "进行多轮问答和评分。"},
            {"name": "复盘页", "purpose": "沉淀错题和后续准备清单。"},
        ],
        "workflow": [
            "用户先导入岗位描述并上传简历。",
            "系统标记能力缺口并给出简历快改建议。",
            "随后进入模拟追问，生成更接近真实面试的问答链。",
            "结束后输出复盘清单和下一步补强建议。",
        ],
        "frontend": "前端核心是表单导入、双栏对照和问答聊天流，适合小程序轻交互。",
        "backend": "后端负责岗位解析、简历版本存储和模拟问答生成。",
        "distribution": "从求职群、训练营、高校就业社群切入，用“当天就能开始练”的定位传播。",
        "monetization": "按周会员、岗位专题包和高阶训练营联名收费。",
        "prompt_goal": "做一个帮用户当天完成求职准备闭环的产品首版",
    },
]

def build_miniapp_factory(
    config: dict[str, Any],
    raw_by_source: dict[str, list[dict[str, Any]]],
    now: datetime,
    history_dir: Path | None = None,
) -> dict[str, Any]:
    pool = collect_signal_items(raw_by_source, now)
    recent_ids = load_recent_creation_ids(history_dir)

    candidates = [score_theme(theme, pool, recent_ids) for theme in THEMES]
    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = select_candidates(candidates)
    if not selected:
        selected = [fallback_candidate(now)]

    creations = [build_creation(candidate, now) for candidate in selected]
    top_evidence = build_top_evidence(selected)
    daily_brief = build_daily_brief(selected, now)
    scorecard = build_scorecard(selected, top_evidence)

    factory = {
        "title": "AI 自动造物系统",
        "subtitle": "每天 07:00 / 12:30 根据对应时间窗自动生成新的重点变化与可造方向。",
        "generatedAt": clock(now),
        "scheduledAt": "07:00 / 12:30 Asia/Shanghai",
        "windowLabel": build_window_label(now),
        "mode": "heuristic",
        "summary": daily_brief["headline"],
        "scorecard": scorecard,
        "dailyBrief": daily_brief,
        "primaryCreationId": creations[0]["creationId"],
        "todayCreations": creations,
        "evidenceSignals": top_evidence,
        "engine": build_engine_meta(pool, recent_ids, config),
    }

    client = create_openai_client()
    if client is not None and top_evidence:
        try:
            enrich_factory_with_ai(client, factory, selected, now)
            factory["mode"] = "ai"
        except Exception as exc:  # noqa: BLE001
            print(f"[miniapp-factory][ai] failed -> {exc}")

    return factory


def collect_signal_items(raw_by_source: dict[str, list[dict[str, Any]]], now: datetime) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    window_start = session_window_start(now)
    window_end = session_window_end(now)

    for group, source_ids in FACTORY_SOURCE_GROUPS.items():
        for source_id in source_ids:
            for rank, item in enumerate(raw_by_source.get(source_id, [])[:24], start=1):
                title = clean_text(item.get("title"))
                if not title or is_noise_title(title):
                    continue

                normalized = normalize_text(title)
                if normalized in seen_titles:
                    continue
                if not looks_relevant(normalized, group):
                    continue

                published_at = clean_text(item.get("publishedAt")) or None
                published_dt = parse_timestamp(published_at)
                if published_dt is not None and published_dt < window_start:
                    continue
                if published_dt is not None and published_dt > window_end:
                    continue

                seen_titles.add(normalized)
                items.append(
                    {
                        "title": title,
                        "normalized": normalized,
                        "url": clean_text(item.get("url")) or "#",
                        "source": clean_text(item.get("sourceLabel")) or source_id,
                        "sourceId": source_id,
                        "group": group,
                        "publishedAt": published_at,
                        "rank": rank,
                        "sourceWeight": SOURCE_WEIGHTS.get(source_id, 1.0),
                    }
                )

    return items


def looks_relevant(normalized: str, group: str) -> bool:
    if group in {"product", "operator"}:
        return True
    keywords = INTENT_TERMS + PAIN_TERMS + COMMERCIAL_TERMS + CHANGE_TERMS + ACTION_TERMS
    return has_any(normalized, keywords)


def score_theme(theme: dict[str, Any], pool: list[dict[str, Any]], recent_ids: list[str]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    matched_groups: set[str] = set()
    matched_sources: set[str] = set()
    matched_terms: list[str] = []
    pain_hits = 0
    commercial_hits = 0
    action_hits = 0
    change_hits = 0

    for item in pool:
        matches = keyword_hits(item["normalized"], theme["keywords"])
        if not matches:
            continue

        negative_hits = keyword_hits(item["normalized"], theme.get("negative_terms", ()))
        evidence_score = 14 + len(matches) * 8
        evidence_score += max(0, int(item["sourceWeight"] * 7))
        evidence_score += max(0, 9 - item["rank"])

        if item["group"] in theme.get("preferred_groups", ()):
            evidence_score += 6
        if has_any(item["normalized"], PAIN_TERMS):
            pain_hits += 1
            evidence_score += 6
        if has_any(item["normalized"], COMMERCIAL_TERMS):
            commercial_hits += 1
            evidence_score += 5
        if has_any(item["normalized"], ACTION_TERMS):
            action_hits += 1
            evidence_score += 4
        if has_any(item["normalized"], CHANGE_TERMS):
            change_hits += 1
            evidence_score += 5
        if negative_hits:
            evidence_score -= len(negative_hits) * 6

        if evidence_score < 18:
            continue

        matched_groups.add(item["group"])
        matched_sources.add(item["sourceId"])
        matched_terms.extend(matches)

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
                "reason": build_signal_reason(item["title"], matches, theme),
            }
        )

    evidence.sort(key=lambda item: (item["score"], item.get("publishedAt") or ""), reverse=True)
    evidence = diversify_evidence(evidence, 6)
    unique_terms = unique_preserving_order(matched_terms)

    demand = theme["base_scores"]["demand"]
    demand += min(18, len(unique_terms) * 2)
    demand += min(16, len(matched_groups) * 7)
    demand += min(12, len(evidence) * 2)
    demand += min(10, pain_hits * 2)
    demand += min(8, commercial_hits * 2)
    if len(matched_groups) < 2:
        demand -= 10
    if not evidence:
        demand = max(20, demand - 26)

    buildability = theme["base_scores"]["buildability"]
    buildability += min(8, action_hits * 2)
    buildability += min(6, change_hits)
    if len(matched_sources) >= 3:
        buildability += 3

    boldness = theme["base_scores"]["boldness"]
    boldness += min(8, max(0, len(matched_groups) - 1) * 3)
    boldness += 4 if change_hits >= 2 else 0

    ai_leverage = theme["base_scores"]["ai"]
    ai_leverage += min(6, action_hits)
    ai_leverage += 4 if has_any(" ".join(unique_terms), ("agent", "translate", "生成", "自动")) else 0

    repeat_penalty = 0
    if theme["id"] in recent_ids[:4]:
        repeat_penalty = 18
    elif theme["id"] in recent_ids[:10]:
        repeat_penalty = 10
    elif theme["id"] in recent_ids:
        repeat_penalty = 4

    total = demand * 0.34 + buildability * 0.24 + boldness * 0.2 + ai_leverage * 0.22
    total -= repeat_penalty

    return {
        "theme": theme,
        "score": round(total, 1),
        "scores": {
            "demand": clamp_score(demand),
            "buildability": clamp_score(buildability),
            "boldness": clamp_score(boldness),
            "aiLeverage": clamp_score(ai_leverage),
        },
        "evidence": evidence,
        "matchedGroups": sorted(matched_groups),
        "matchedSources": sorted(matched_sources),
        "matchedTerms": unique_terms,
        "repeatPenalty": repeat_penalty,
    }


def select_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candidates:
        return []

    selected: list[dict[str, Any]] = []
    score_floor = candidates[0]["score"] - 16
    for candidate in candidates:
        if candidate["score"] < score_floor and len(selected) >= 3:
            continue
        if candidate["scores"]["demand"] < 48:
            continue
        selected.append(candidate)
        if len(selected) >= 4:
            break

    if not selected:
        return candidates[:3]
    if len(selected) < 3:
        for candidate in candidates:
            if candidate in selected:
                continue
            selected.append(candidate)
            if len(selected) >= 3:
                break
    return selected


def build_creation(candidate: dict[str, Any], now: datetime) -> dict[str, Any]:
    theme = candidate["theme"]
    name = build_creation_name(theme, candidate)
    sources = candidate["evidence"][:3]
    source_lines = "、".join(shorten(item["title"], 16) for item in sources[:2]) or "高信号市场变化"
    groups = "、".join(SOURCE_GROUP_LABELS[group] for group in candidate["matchedGroups"])
    groups = groups or "多个高信号来源"

    because = f"因为 {groups} 里反复出现“{source_lines}”这类信号，说明 {theme['market_shift']}"
    first_version = theme["first_version"].rstrip("。")
    if first_version.startswith("先做"):
        first_version = first_version[2:].strip("， ")
    create_what = f"所以今天适合造「{name}」：{theme['tagline']} 首版范围是 {first_version}。"
    why_now = (
        f"在当前版次时间窗里，这条需求不是单点热度，而是被 {max(1, len(candidate['matchedSources']))} 个来源反复放大。"
        f" {theme['demand_gap']}"
    )

    creation = {
        "creationId": theme["id"],
        "name": name,
        "tagline": theme["tagline"],
        "because": because,
        "createWhat": create_what,
        "whyNow": why_now,
        "targetUsers": theme["target_users"],
        "scene": theme["scene"],
        "aiBuildability": build_ai_buildability(candidate["scores"]),
        "firstVersion": first_version,
        "scores": candidate["scores"],
        "coreModules": theme["modules"],
        "pageStructure": theme["pages"],
        "workflow": theme["workflow"],
        "delivery": {
            "frontend": theme["frontend"],
            "backend": theme["backend"],
            "platforms": build_platforms(candidate["scores"]),
        },
        "launchPlan": theme["distribution"],
        "monetization": theme["monetization"],
        "sources": sources,
    }
    creation["aiBuildPrompt"] = build_ai_build_prompt(creation, theme)
    return creation


def build_creation_name(theme: dict[str, Any], candidate: dict[str, Any]) -> str:
    lead = candidate["matchedTerms"][0] if candidate["matchedTerms"] else theme["id"].split("-")[0]
    prefix = DISPLAY_TERMS.get(lead.lower(), DISPLAY_TERMS.get(lead, DEFAULT_PREFIXES.get(theme["id"], "今日")))
    if theme["name_suffix"].startswith(prefix):
        return theme["name_suffix"]
    return f"{prefix}{theme['name_suffix']}"


def build_ai_buildability(scores: dict[str, int]) -> str:
    if scores["buildability"] >= 84 and scores["aiLeverage"] >= 88:
        return "可直接让 AI 生成首版"
    if scores["buildability"] >= 72:
        return "AI 先出 70%，你补数据和接口"
    return "AI 先出骨架，人工补重交付部分"


def build_platforms(scores: dict[str, int]) -> list[str]:
    if scores["buildability"] >= 82:
        return ["H5", "微信小程序", "抖音小程序"]
    return ["H5", "微信小程序"]

def build_ai_build_prompt(creation: dict[str, Any], theme: dict[str, Any]) -> str:
    modules = "\n".join(f"- {item['title']}：{item['detail']}" for item in creation["coreModules"])
    pages = "\n".join(f"- {item['name']}：{item['purpose']}" for item in creation["pageStructure"])
    flow = "\n".join(f"- {item}" for item in creation["workflow"])
    platforms = " / ".join(creation["delivery"]["platforms"])
    return f"""
你现在是 AI 产品架构师 + 全栈开发者，请直接为我生成这个产品的首版。

产品名称：{creation['name']}
产品一句话：{creation['tagline']}
为什么今天做：{creation['because']}
要创造什么：{creation['createWhat']}
目标用户：{creation['targetUsers']}
使用场景：{creation['scene']}
AI 参与方式：{creation['aiBuildability']}
首发平台：{platforms}
首版边界：{creation['firstVersion']}
产品目标：{theme['prompt_goal']}

核心模块：
{modules}

页面结构：
{pages}

关键流程：
{flow}

实现要求：
1. 先输出产品定位、用户故事、信息架构、页面清单。
2. 再输出前端方案、后端方案、数据结构、接口设计。
3. 默认首发做 H5 + 微信小程序，技术上尽量轻量、可快速上线。
4. 输出一个能继续直接开发的 MVP，不要写空泛建议。
5. 如果有适合 AI 自动生成的部分，直接给出提示词、页面文案和结构化数据示例。
""".strip()


def build_daily_brief(candidates: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    market_shifts = []
    for candidate in candidates[:3]:
        theme = candidate["theme"]
        evidence = candidate["evidence"][:2]
        signal_text = "、".join(shorten(item["title"], 14) for item in evidence) or theme["tagline"]
        market_shifts.append(f"{signal_text} 这类信号在今天重复出现，说明 {theme['market_shift']}")

    headline = "今天不该再做资讯站，而该做能把变化直接翻成动作、交付或决策结果的产品。"
    build_policy = "优先做 AI 能快速出首版的执行型工具：先用 H5 / 微信小程序跑通，再决定是否补 App、自动化和团队协作。"
    return {
        "headline": headline,
        "marketShifts": market_shifts[:3],
        "buildPolicy": build_policy,
        "schedule": f"下一次自动生成时间：{next_run_label(now)}",
    }


def build_scorecard(candidates: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, int]:
    if not candidates:
        return {"change": 40, "demand": 40, "build": 40, "bold": 40, "ai": 40}

    avg_demand = sum(item["scores"]["demand"] for item in candidates) / len(candidates)
    avg_build = sum(item["scores"]["buildability"] for item in candidates) / len(candidates)
    avg_bold = sum(item["scores"]["boldness"] for item in candidates) / len(candidates)
    avg_ai = sum(item["scores"]["aiLeverage"] for item in candidates) / len(candidates)
    groups = {item["group"] for item in evidence}
    change = clamp_score(len(evidence) * 10 + len(groups) * 9 + 18)

    return {
        "change": change,
        "demand": clamp_score(avg_demand),
        "build": clamp_score(avg_build),
        "bold": clamp_score(avg_bold),
        "ai": clamp_score(avg_ai),
    }


def build_top_evidence(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for candidate in candidates:
        for item in candidate["evidence"]:
            key = normalize_text(item["title"])
            if key in seen_titles:
                continue
            seen_titles.add(key)
            merged.append(item)
    merged.sort(key=lambda item: (item["score"], item.get("publishedAt") or ""), reverse=True)
    return merged[:8]


def build_engine_meta(pool: list[dict[str, Any]], recent_ids: list[str], config: dict[str, Any]) -> dict[str, Any]:
    sources = []
    for group, source_ids in FACTORY_SOURCE_GROUPS.items():
        count = sum(1 for item in pool if item["group"] == group)
        sources.append(
            {
                "name": SOURCE_GROUP_LABELS[group],
                "count": count,
                "sources": [
                    config["sources"][source_id]["label"]
                    for source_id in source_ids
                    if source_id in config.get("sources", {})
                ],
            }
        )

    return {
        "sources": sources,
        "collectionRules": [
            "不再铺大众新闻，优先抓产品发布、行业变化、商家动作、用户需求这几类高价值信号。",
            "严格按 07:00 / 12:30 对应窗口取数，窗口外的旧线索自动降权或剔除。",
            "标题先去重，再按动作性、商业价值、跨源重复度加权。",
        ],
        "qualityRules": [
            "至少要求 2 个来源组都能解释这个机会，避免被单一热搜误导。",
            "自动过滤体育、明星、纯娱乐和低商业价值话题。",
            f"最近历史里已经记录了 {len(recent_ids)} 个方向，会参与去重和降权。",
        ],
        "buildRules": [
            "默认每天 07:00 和 12:30 自动生成，优先给出多个今天值得造的方向，而不是只挑 1 个。",
            "07:00 用昨收后到 07:00 的窗口；12:30 用 07:00 到 12:30 的窗口。",
            "每个方向都必须写清楚：为什么现在、造什么、谁会用、如何让 AI 继续接力。",
            "优先执行型、决策型、交付型工具，少做纯信息聚合页。",
        ],
    }


def enrich_factory_with_ai(client: Any, factory: dict[str, Any], candidates: list[dict[str, Any]], now: datetime) -> None:
    schema = {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "marketShifts": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "buildPolicy": {"type": "string"},
            "creations": {
                "type": "array",
                "minItems": len(factory["todayCreations"]),
                "maxItems": len(factory["todayCreations"]),
                "items": {
                    "type": "object",
                    "properties": {
                        "creationId": {"type": "string"},
                        "name": {"type": "string"},
                        "tagline": {"type": "string"},
                        "because": {"type": "string"},
                        "createWhat": {"type": "string"},
                        "whyNow": {"type": "string"},
                        "targetUsers": {"type": "string"},
                        "scene": {"type": "string"},
                        "firstVersion": {"type": "string"},
                        "launchPlan": {"type": "string"},
                        "monetization": {"type": "string"},
                    },
                    "required": [
                        "creationId",
                        "name",
                        "tagline",
                        "because",
                        "createWhat",
                        "whyNow",
                        "targetUsers",
                        "scene",
                        "firstVersion",
                        "launchPlan",
                        "monetization",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["headline", "marketShifts", "buildPolicy", "creations"],
        "additionalProperties": False,
    }

    response = client.responses.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
        input=build_ai_prompt(factory, candidates, now),
        text={
            "format": {
                "type": "json_schema",
                "name": "daily_creation_board",
                "strict": True,
                "schema": schema,
            }
        },
    )
    payload = json.loads(response.output_text)
    factory["summary"] = clean_text(payload["headline"])
    factory["dailyBrief"]["headline"] = clean_text(payload["headline"])
    factory["dailyBrief"]["marketShifts"] = [clean_text(item) for item in payload["marketShifts"]]
    factory["dailyBrief"]["buildPolicy"] = clean_text(payload["buildPolicy"])

    candidate_map = {item["theme"]["id"]: item for item in candidates}
    creation_map = {item["creationId"]: item for item in factory["todayCreations"]}
    for item in payload["creations"]:
        creation_id = clean_text(item["creationId"])
        creation = creation_map.get(creation_id)
        candidate = candidate_map.get(creation_id)
        if not creation or not candidate:
            continue
        creation["name"] = clean_text(item["name"])
        creation["tagline"] = clean_text(item["tagline"])
        creation["because"] = clean_text(item["because"])
        creation["createWhat"] = clean_text(item["createWhat"])
        creation["whyNow"] = clean_text(item["whyNow"])
        creation["targetUsers"] = clean_text(item["targetUsers"])
        creation["scene"] = clean_text(item["scene"])
        creation["firstVersion"] = clean_text(item["firstVersion"])
        creation["launchPlan"] = clean_text(item["launchPlan"])
        creation["monetization"] = clean_text(item["monetization"])
        creation["aiBuildPrompt"] = build_ai_build_prompt(creation, candidate["theme"])


def build_ai_prompt(factory: dict[str, Any], candidates: list[dict[str, Any]], now: datetime) -> str:
    signal_lines = []
    for candidate in candidates[:4]:
        theme = candidate["theme"]
        for item in candidate["evidence"][:2]:
            signal_lines.append(f"- [{theme['id']}] [{item['source']}] {item['title']}（来源组：{item['groupLabel']}）")

    creation_lines = []
    for item in factory["todayCreations"]:
        creation_lines.append(
            "\n".join(
                [
                    f"creationId: {item['creationId']}",
                    f"name: {item['name']}",
                    f"tagline: {item['tagline']}",
                    f"because: {item['because']}",
                    f"createWhat: {item['createWhat']}",
                    f"whyNow: {item['whyNow']}",
                    f"targetUsers: {item['targetUsers']}",
                    f"scene: {item['scene']}",
                    f"firstVersion: {item['firstVersion']}",
                    f"launchPlan: {item['launchPlan']}",
                    f"monetization: {item['monetization']}",
                ]
            )
        )

    return f"""
你是一个大胆但务实的中文 AI 产品架构师。
你不是在写新闻摘要，而是在根据真实变化生成“今天最值得造的东西”。

当前时间：{clock(now)}

真实信号：
{chr(10).join(signal_lines)}

当前启发式结果：
{chr(10).join(creation_lines)}

输出要求：
1. headline 要明确表达“今天不该继续做资讯站，而该做什么类型的产品”。
2. marketShifts 必须写成 3 条“变化判断”，不是复述新闻标题。
3. 每个 creation 都要写得更像创始人会直接拿去开干的方向。
4. because 和 createWhat 必须形成“因为...所以造...”的关系。
5. 可以大胆，但不要虚构市场数据、榜单名次或用户量。
6. 语气直接、中文、可执行。
""".strip()


def load_recent_creation_ids(history_dir: Path | None) -> list[str]:
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
    for entry in entries[:30]:
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

        factory = digest.get("miniappFactory", {})
        primary_id = clean_text(factory.get("primaryCreationId"))
        if primary_id:
            recent.append(primary_id)
            continue
        legacy_id = clean_text(factory.get("todayPlan", {}).get("blueprintId"))
        if legacy_id:
            recent.append(legacy_id)
    return recent


def fallback_candidate(now: datetime) -> dict[str, Any]:
    theme = THEMES[0]
    return {
        "theme": theme,
        "score": 60.0,
        "scores": {"demand": 54, "buildability": 80, "boldness": 84, "aiLeverage": 88},
        "evidence": [],
        "matchedGroups": ["product", "operator"],
        "matchedSources": [],
        "matchedTerms": ["平台"],
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


def build_signal_reason(title: str, matches: list[str], theme: dict[str, Any]) -> str:
    if not matches:
        return "说明今天这类需求仍在继续放大。"
    return f"标题命中“{matches[0]}”，说明 {theme['demand_gap']}"


def keyword_hits(text: str, keywords: tuple[str, ...] | list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword.lower() in text]


def has_any(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


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
            return datetime.strptime(value, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    return None


def shanghai_now(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=TZ)
    return now.astimezone(TZ)


def next_run_label(now: datetime) -> str:
    now = shanghai_now(now)
    morning = now.replace(hour=7, minute=0, second=0, microsecond=0)
    midday = now.replace(hour=12, minute=30, second=0, microsecond=0)
    if now < morning:
        return morning.strftime("%Y-%m-%d 07:00")
    if now < midday:
        return midday.strftime("%Y-%m-%d 12:30")
    return (morning + timedelta(days=1)).strftime("%Y-%m-%d 07:00")


def clock(now: datetime) -> str:
    return now.strftime("%Y-%m-%d %H:%M")


def build_window_label(now: datetime) -> str:
    now = shanghai_now(now)
    start = session_window_start(now)
    end = session_window_end(now)
    return f"{start.strftime('%m-%d %H:%M')} - {end.strftime('%m-%d %H:%M')}"


def previous_a_share_close(now: datetime) -> datetime:
    now = shanghai_now(now)
    anchor = now.replace(hour=15, minute=0, second=0, microsecond=0)
    if now < anchor:
        anchor -= timedelta(days=1)
    while anchor.weekday() >= 5:
        anchor -= timedelta(days=1)
    return anchor


def session_window_start(now: datetime) -> datetime:
    now = shanghai_now(now)
    window_end = session_window_end(now)
    morning = window_end.replace(hour=7, minute=0, second=0, microsecond=0)
    midday = window_end.replace(hour=12, minute=30, second=0, microsecond=0)
    if window_end <= morning:
        return previous_a_share_close(window_end)
    if window_end <= midday:
        return morning
    return midday


def session_window_end(now: datetime) -> datetime:
    now = shanghai_now(now)
    morning = now.replace(hour=7, minute=0, second=0, microsecond=0)
    midday = now.replace(hour=12, minute=30, second=0, microsecond=0)
    if morning <= now < midday:
        return morning
    if now >= midday:
        return midday
    return now


def clamp_score(value: float | int) -> int:
    return max(0, min(100, int(round(value))))


def create_openai_client() -> Any | None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)
