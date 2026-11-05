"""通过 SDK 暴露 WebUI 配置；不在配置中存放账号密码或 Cookie。"""

from typing import List
from zoneinfo import ZoneInfo

from maibot_sdk import Field, PluginConfigBase
from pydantic import field_validator, model_validator


class PluginSection(PluginConfigBase):
    """设置插件开关，以及哪些账号可以使用登录、预览和启停命令。"""

    __ui_label__ = "基本设置"
    __ui_order__ = 0
    enabled: bool = Field(
        default=True,
        description="启用插件，登录后默认自动进入自主浏览；手动暂停仍需 start 恢复",
        json_schema_extra={
            "label": "启用插件",
            "hint": "关闭后停止后台浏览。默认登录后自动进入自主模式；手动 pause 或发生异常后，需要 start 恢复。",
        },
    )
    config_version: str = Field(
        default="0.2.0",
        description="插件自动维护的配置格式版本",
        json_schema_extra={
            "label": "配置格式版本（无需修改）",
            "hint": "由插件自动维护，用于识别配置格式，保持原值即可。",
            "disabled": True,
        },
    )
    admin_users: List[str] = Field(
        default_factory=list,
        description="可直接填写 QQ 号（自动补全 qq:），其他平台填写 平台:用户号；留空拒绝普通聊天命令",
        json_schema_extra={
            "label": "管理员账号",
            "hint": "QQ 管理员直接填 QQ 号，保存时自动补全 qq:；其他平台填写 平台:用户号。每项一个账号，留空时普通聊天中无法使用管理命令。",
            "placeholder": "例如：12345678 或 qq:12345678",
        },
    )

    @field_validator("admin_users")
    @classmethod
    def normalize_admins(cls, values: List[str]) -> List[str]:
        normalized: List[str] = []
        for value in values:
            value = value.strip()
            if value.isascii() and value.isdecimal():
                value = f"qq:{value}"
            if ":" not in value or any(not part.strip() for part in value.split(":", 1)):
                raise ValueError("管理员请填写 QQ 号或 平台:用户号，例如 123456 或 qq:123456")
            platform, user_id = value.split(":", 1)
            normalized.append(f"{platform.strip().lower()}:{user_id.strip()}")
        return list(dict.fromkeys(normalized))


class BrowseSection(PluginConfigBase):
    """决定多久浏览一次、每天看多少视频，以及感兴趣或需要跳过的内容。"""

    __ui_label__ = "浏览与兴趣"
    __ui_order__ = 1
    backlog_max_items: int = Field(
        default=24, ge=1, le=100, description="评论候选池上限，超限按兴趣、新鲜度与等待时间择优保留",
        json_schema_extra={
            "label": "最多保留的评论候选数",
            "hint": "默认保留 24 个视频，可填 1～100。评论冷却或额度用完时，感兴趣的视频可留待之后考虑；超出数量时按兴趣、新鲜度和等待时间择优保留，不保证每个候选都会发表评论。",
        },
    )
    backlog_max_age_hours: int = Field(
        default=48, ge=1, le=168, description="评论候选有效期，小时；候选不保证发送",
        json_schema_extra={
            "label": "评论候选有效期（小时）",
            "hint": "默认 48 小时＝2 天，可填 1～168。超过有效期的候选不再等待评论机会；发送前仍需重新读取内容并判断，不会直接发送旧草稿。",
        },
    )
    read_retry_base_seconds: int = Field(
        default=60, ge=10, le=600, description="只读网络失败退避起点，最多四次后每小时探测",
        json_schema_extra={
            "label": "读取失败首次重试等待（秒）",
            "hint": "读取账号、推荐等请求遇到可重试的网络错误时，首次默认等待 60 秒，可填 10～600。连续失败会逐步延长等待，达到重试上限后每小时探测一次；不会自动重发评论。",
        },
    )
    max_per_up: int = Field(
        default=2, ge=1, le=10, description="每轮同一 UP 主最多分析的视频数",
        json_schema_extra={
            "label": "每轮同一 UP 主视频上限",
            "hint": "默认每轮最多分析同一 UP 主的 2 个视频，可填 1～10，避免一轮推荐都来自同一个人。仍受每轮视频分析总上限约束。",
        },
    )
    max_per_topic: int = Field(
        default=2, ge=1, le=10, description="每轮同一已知分区题材最多分析的视频数，未知题材不强行分类",
        json_schema_extra={
            "label": "每轮同一题材视频上限",
            "hint": "默认每轮最多分析同一已知分区题材的 2 个视频，可填 1～10，让内容更丰富。没有题材信息的视频不强行归类；仍受每轮视频分析总上限约束。",
        },
    )
    auto_start: bool = Field(
        default=True,
        description="首次登录或重新启用插件后自动进入运行状态；不解除手动暂停或异常暂停",
        json_schema_extra={
            "label": "登录后自动开始",
            "hint": "默认开启，扫码成功后无需发送 start。运行状态在重启后保留；手动 pause 或异常暂停不会被自动解除。关闭后首次使用需发送 start。",
        },
    )
    autonomous_enabled: bool = Field(
        default=True,
        description="先由模型决定这次是否浏览，以及下次何时再考虑",
        json_schema_extra={
            "label": "自主决定刷不刷 B 站",
            "hint": "开启后，麦麦结合人设、兴趣、时间和最近浏览反馈决定刷不刷，也可以选择晚些再看。关闭后按浏览间隔定时刷。评论仍单独判断。",
        },
    )
    explore_more: bool = Field(
        default=False,
        description="自主判断时更愿意尝试新的感兴趣视频，仍可选择休息",
        json_schema_extra={
            "label": "更积极地探索新视频",
            "hint": "开启后，有感兴趣的新推荐时更愿意先看一两条，不因最近没有想发的评论就一直休息。仍由麦麦自主决定，不保证浏览或评论比例。关闭时维持随性节奏。",
        },
    )
    interval_seconds: int = Field(
        default=600,
        ge=300,
        description="最短浏览意愿检查间隔，秒",
        json_schema_extra={
            "label": "最短浏览意愿检查间隔（秒）",
            "hint": "自主模式下至少间隔多久再考虑刷 B 站，默认 600 秒＝10 分钟，最少 300 秒＝5 分钟。麦麦可在最短和最长间隔之间决定等待多久；关闭自主判断后按此固定间隔运行。",
        },
    )
    max_check_minutes: int = Field(
        default=20,
        ge=5,
        le=360,
        description="自主模式下两次浏览意愿检查最多相隔多少分钟",
        json_schema_extra={
            "label": "最长浏览意愿检查间隔（分钟）",
            "hint": "默认 20 分钟，可填 5～360，不能小于最短检查间隔。模型不能自行休息超过这个上限；调小后，当前尚未结束的等待也会缩短。非活动时段和每日视频额度仍然生效。",
        },
    )
    videos_per_round: int = Field(
        default=3,
        ge=1,
        le=10,
        description="每轮最多分析的视频数",
        json_schema_extra={
            "label": "每轮最多分析视频数",
            "hint": "一轮最多读取并分析几个视频，默认 3 个，可填 1～10。每轮最多发表 1 条评论。",
        },
    )
    videos_per_day: int = Field(
        default=180,
        ge=1,
        le=200,
        description="每天分析视频的上限，预览也计入",
        json_schema_extra={
            "label": "每日视频分析上限",
            "hint": "达到上限后当天停止分析，手动预览也计入。默认每天 180 个，按所选时区的零点重新统计。",
        },
    )
    max_duration_seconds: int = Field(
        default=1200,
        ge=30,
        le=7200,
        description="跳过超过此时长的视频",
        json_schema_extra={
            "label": "视频最长时长（秒）",
            "hint": "超过此时长的视频直接跳过。默认 1200 秒＝20 分钟，可填 30～7200 秒。",
        },
    )
    interests: str = Field(
        default="",
        max_length=2000,
        description="兴趣偏好，留空时由麦麦人设和账号推荐决定",
        json_schema_extra={
            "label": "感兴趣的话题",
            "hint": "告诉麦麦你希望它关注哪些内容，例如科普、游戏或音乐。留空时结合麦麦人设和账号推荐自行判断。",
            "placeholder": "例如：喜欢科普、独立游戏和音乐制作",
        },
    )
    blocked_keywords: List[str] = Field(
        default_factory=list,
        description="标题、简介或视频内容命中后跳过",
        json_schema_extra={
            "label": "屏蔽关键词",
            "hint": "标题、简介或读取到的视频内容包含任意一个关键词，就跳过该视频。每项填一个词，留空不限制。",
            "placeholder": "例如：剧透",
        },
    )
    blocked_up_uids: List[str] = Field(
        default_factory=list,
        description="跳过这些 UP 主的 UID",
        json_schema_extra={
            "label": "屏蔽的 UP 主 UID",
            "hint": "不浏览这些 UP 主的视频。填写 B 站个人空间中的数字 UID，不是昵称；每项一个，留空不屏蔽。",
            "placeholder": "填写 UP 主的数字 UID",
        },
    )
    active_start_hour: int = Field(
        default=9,
        ge=0,
        le=23,
        description="开始活动的小时",
        json_schema_extra={
            "label": "开始浏览时间（小时）",
            "hint": "使用 24 小时制，填 0～23。例如填 9 表示从每天 09:00 开始允许自动浏览。",
        },
    )
    active_end_hour: int = Field(
        default=23,
        ge=0,
        le=23,
        description="结束活动的小时；与开始相同表示全天，支持跨午夜",
        json_schema_extra={
            "label": "结束浏览时间（小时）",
            "hint": "例如填 23 表示从 23:00 起停止。结束时间早于开始时间表示跨午夜；两者相同表示全天运行。",
        },
    )
    timezone: str = Field(
        default="Asia/Shanghai",
        description="活动时间与每日限额使用的时区",
        json_schema_extra={
            "label": "活动与统计时区",
            "hint": "活动时段和每日限额都按这个时区计算。默认 Asia/Shanghai，表示北京时间，通常保持默认即可。",
            "placeholder": "Asia/Shanghai",
        },
    )

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @model_validator(mode="after")
    def validate_check_interval(self) -> "BrowseSection":
        if self.max_check_minutes * 60 < self.interval_seconds:
            raise ValueError("最长浏览意愿检查间隔不能小于最短检查间隔，请同时调整这两项")
        return self


class CommentSection(PluginConfigBase):
    """决定是否实际发表评论，以及发送频率、评论长度和重复检查的规则。"""

    __ui_label__ = "评论"
    __ui_order__ = 2
    publish_enabled: bool = Field(
        default=False,
        description="开启后 start 会自动发布；关闭时只预览并记录判断",
        json_schema_extra={
            "label": "自动发表评论",
            "hint": "关闭时只生成预览记录；开启后，运行中的插件可把评论发到 B 站。使用 /bili_auto start 启动；/bili_auto preview 始终只预览。",
        },
    )
    per_day: int = Field(
        default=12,
        ge=1,
        le=200,
        description="每天最多发送尝试数，失败或结果未知也计入",
        json_schema_extra={
            "label": "每日评论发送上限",
            "hint": "默认每天最多 12 次发送尝试，可填 1～200。失败或结果未知也计入；达到上限后停止发送一级评论，仍可浏览视频。与跟进回复的每日额度分开统计，按所选时区零点重新统计。",
        },
    )
    min_interval_seconds: int = Field(
        default=2700,
        ge=300,
        description="两次发送尝试至少间隔多少秒",
        json_schema_extra={
            "label": "评论最短间隔（秒）",
            "hint": "发送视频下一级评论前，距离最近一次评论或跟进回复至少等待多久。默认 2700 秒＝45 分钟；跟进别人回复使用下面独立的最短间隔。",
        },
    )
    max_chars: int = Field(
        default=160,
        ge=20,
        le=500,
        description="评论最大字数",
        json_schema_extra={
            "label": "单条评论最大字数",
            "hint": "默认最多 160 字，可填 20～500。模型生成的评论超过上限时会跳过，不会直接截断后发送。",
        },
    )
    min_interest: float = Field(
        default=0.75,
        ge=0,
        le=1,
        description="模型给出的兴趣分低于该值时不评论；不是校准概率",
        json_schema_extra={
            "label": "发表评论的最低兴趣分",
            "hint": "可填 0～1，默认 0.75。越高越挑剔，低于该分数就不评论；这是模型的兴趣评分，不是发表评论的概率。",
            "step": 0.01,
        },
    )
    similarity_threshold: float = Field(
        default=0.88,
        ge=0.5,
        le=1,
        description="与近期评论过于相似时跳过",
        json_schema_extra={
            "label": "重复评论相似度阈值",
            "hint": "与近期评论的相似度达到此值就跳过。默认 0.88，可填 0.5～1；越低查重越严格。完全重复的文字始终拦截。",
            "step": 0.01,
        },
    )


class ModelSection(PluginConfigBase):
    """选择麦麦已有的模型任务，设置评论语气、等待时间和读取内容的长度。"""

    __ui_label__ = "模型"
    __ui_order__ = 3
    decision_budget_seconds: int = Field(
        default=240, ge=20, le=900, description="每条评论或回复生成、复核及一次重生成的总时限",
        json_schema_extra={
            "label": "评论与回复处理总时限（秒）",
            "hint": "每条评论或跟进回复从生成到依据复核共用的时间预算，包含最多一次重生成。默认 240 秒＝4 分钟，可填 20～900；达到总时限后停止本次处理，不发送未完成复核的正文。",
        },
    )
    review_timeout_seconds: int = Field(
        default=45, ge=1, le=120, description="单次正文依据复核时限，失败不发送",
        json_schema_extra={
            "label": "单次正文依据复核时限（秒）",
            "hint": "检查生成正文是否得到已读取内容支持，默认每次最多等待 45 秒，可填 1～120。超时或复核不通过时不发送该正文，同时受相应处理总时限约束。",
        },
    )
    evidence_retention_days: int = Field(
        default=7, ge=1, le=30, description="本地引用片段与时间位置保留天数",
        json_schema_extra={
            "label": "内容依据缓存保留天数",
            "hint": "默认保留本地引用片段和时间位置 7 天，可填 1～30，供后续分享等处理查阅。这里只控制内容依据缓存，不是浏览和评论历史记录的保留期限。",
        },
    )
    task: str = Field(
        default="replyer",
        description="Host 中用于判断兴趣和生成评论的模型任务",
        json_schema_extra={
            "label": "评论使用的模型任务",
            "hint": "填写麦麦模型配置中已有的任务名。默认 replyer，使用麦麦的回复模型；这里不是填写模型厂商或具体型号。",
            "placeholder": "replyer",
        },
    )
    candidates: List[str] = Field(
        default_factory=list,
        description="按顺序尝试的具体模型名；留空时由 Host 任务选择模型",
        json_schema_extra={
            "label": "候选模型（按顺序尝试）",
            "hint": "填写麦麦已配置的具体模型名，每项一个。单个模型超时后换下一个，每轮每个模型最多尝试一次；留空时由模型任务选择。",
        },
    )

    @field_validator("candidates")
    @classmethod
    def normalize_candidates(cls, values: List[str]) -> List[str]:
        if any(not value.strip() for value in values):
            raise ValueError("候选模型名不能为空")
        return list(dict.fromkeys(value.strip() for value in values))

    timeout_seconds: int = Field(
        default=90,
        ge=10,
        le=180,
        description="每个候选模型的一次调用超时",
        json_schema_extra={
            "label": "模型回答等待时间（秒）",
            "hint": "每个候选模型最多等待多久，默认 90 秒，可填 10～180 秒。超时换下一个；全部超时跳过本次，自动运行保持开启。",
        },
    )
    extra_style: str = Field(
        default="",
        max_length=2000,
        description="在麦麦人设之外补充的 B 站评论风格",
        json_schema_extra={
            "label": "额外评论风格",
            "hint": "在麦麦原有人设基础上补充评论语气，例如简短、自然、少用表情。留空时沿用麦麦人设。",
            "placeholder": "例如：评论简短自然，有具体感受再发言",
        },
    )
    content_max_chars: int = Field(
        default=12000,
        ge=500,
        le=24000,
        description="提供给模型的字幕或摘要字符上限",
        json_schema_extra={
            "label": "最多读取的字幕或摘要字数",
            "hint": "默认最多向模型提供12000字。长字幕兼顾相关片段、开头、中段和结尾，保留时间位置；不读取画面或音频。",
        },
    )


class ReplySection(PluginConfigBase):
    """检查别人对麦麦评论的回复，并决定是否继续对话。"""

    __ui_label__ = "跟进别人回复"
    __ui_order__ = 4
    enabled: bool = Field(
        default=True,
        description="检查并跟进别人对本插件已发送评论的回复",
        json_schema_extra={
            "label": "启用跟进回复",
            "hint": "默认开启。只处理别人直接回复麦麦已发送评论的消息，不处理私信、单独 @ 或无关楼层。实际发送仍受“自动发表评论”总开关控制。",
        },
    )
    interval_seconds: int = Field(
        default=600,
        ge=300,
        le=3600,
        description="收到回复的检查间隔，秒",
        json_schema_extra={
            "label": "收到回复检查间隔（秒）",
            "hint": "默认 600 秒＝10 分钟，不受麦麦是否想刷视频影响。暂停、退出账号或非活动时段不自动检查。",
        },
    )
    per_day: int = Field(
        default=8,
        ge=1,
        le=200,
        description="每天最多尝试发送的跟进回复数",
        json_schema_extra={
            "label": "每日跟进回复发送上限",
            "hint": "默认每天最多 8 次发送尝试，可填 1～200。失败或结果未知也计入；与视频下一级评论的每日额度分开统计。达到上限后保留待处理回复，在有效期内下次再考虑；按所选时区零点重新统计。实际发送还受每日分析额度、发送间隔和单条讨论次数限制。",
        },
    )
    analyses_per_day: int = Field(
        default=20,
        ge=1,
        le=100,
        description="每天最多分析多少条收到的回复，预览也计入",
        json_schema_extra={
            "label": "每日收到回复分析上限",
            "hint": "默认每天最多分析 20 条，手动预览也计入；与视频分析额度分开统计，防止收到大量回复时持续调用模型。",
        },
    )
    per_thread: int = Field(
        default=3,
        ge=1,
        le=10,
        description="同一条根评论讨论中最多跟进的次数",
        json_schema_extra={
            "label": "同一条讨论最多跟进次数",
            "hint": "默认在一条根评论下最多跟进 3 次，按账号长期累计，失败也计入，防止与别人反复对话。",
        },
    )
    min_interval_seconds: int = Field(
        default=900,
        ge=300,
        le=86400,
        description="发送跟进回复前与最近一次评论或回复至少间隔多少秒",
        json_schema_extra={
            "label": "跟进回复最短发送间隔（秒）",
            "hint": "默认 900 秒＝15 分钟，从最近一次评论或跟进回复发送尝试算起；等待期间保留收到的消息，下次检查时再考虑。",
        },
    )
    max_age_hours: int = Field(
        default=72,
        ge=1,
        le=168,
        description="仅处理最近多少小时内收到的回复",
        json_schema_extra={
            "label": "只跟进最近多少小时的回复",
            "hint": "默认 72 小时＝3 天，可填 1～168，避免上线后突然回复很久以前的讨论。每次最多读取三页通知。",
        },
    )


class ShareSection(PluginConfigBase):
    """评论成功后，将感兴趣的视频分享至已有 QQ 群聊。"""

    __ui_label__ = "QQ群授权与旧评论后分享"
    __ui_order__ = 5
    polish_enabled: bool = Field(
        default=True, description="仅旧评论后直接QQ分享：每条最多一次模型润色，各群复用；生态开启时本项不参与主动聊天",
        json_schema_extra={
            "label": "润色群分享文案",
            "hint": "仅生态关闭时的旧直接分享：默认开启，在分享草稿基础上再润色一次，同一视频各群复用；关闭后使用已通过依据复核的初稿。",
        },
    )
    polish_model: str = Field(
        default="", max_length=200, description="仅旧直接分享润色的宿主模型名，空为评论任务；不控制生态主动聊天模型",
        json_schema_extra={
            "label": "分享文案润色模型",
            "hint": "仅旧直接分享润色使用：填写麦麦已配置的模型名，最多200字；留空沿用评论任务及候选，不影响生态主动聊天。",
            "placeholder": "留空沿用评论模型，或填写已配置的模型名称",
        },
    )
    polish_timeout_seconds: int = Field(
        default=30, ge=1, le=120, description="仅旧直接分享润色及复核的时限（秒）；生态模式不使用",
        json_schema_extra={
            "label": "分享文案润色时限（秒）",
            "hint": "仅旧直接分享：润色及复核默认30秒，可填1～120。未完成或未通过时使用已通过复核的初稿，仍受分享总时限约束。",
        },
    )
    total_timeout_seconds: int = Field(
        default=120, ge=10, le=360, description="仅旧直接分享草稿/润色/复核的总时限（秒）；不是生态主动聊天超时",
        json_schema_extra={
            "label": "分享文案处理总时限（秒）",
            "hint": "仅旧直接分享：草稿/修改/润色/复核共用默认120秒，可填10～360。超时放弃本次群分享，不影响已发布B站评论，不控制生态主动聊天。",
        },
    )
    qq_group_ids: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="B站侧QQ群授权：生态模式与主动插件群名单取交集；旧模式为评论后直接分享目标，空为不授权",
        json_schema_extra={
            "label": "允许提供B站资料的 QQ 群号",
            "hint": "每项填已有QQ群号，最多10个，空为不授权。ecosystem.enabled=true时仍须保留本名单，并与主动插件allowed_groups取交集；不因此授权私聊。生态关闭时才是原评论提交成功后的直接QQ分享目标。生态开启不运行直接分享润色，不新增发群定时器；失败/未知不自动重发。",
            "placeholder": "例如：123456789",
        },
    )

    @field_validator("qq_group_ids")
    @classmethod
    def validate_groups(cls, groups: List[str]) -> List[str]:
        result = []
        for raw in groups:
            group = raw.strip()
            if not (group.isascii() and group.isdecimal() and 5 <= len(group) <= 12 and not group.startswith("0")):
                raise ValueError("QQ 群号请填写 5～12 位数字，不含 qq: 前缀，例如 123456789；不分享时删除该项留空")
            if group not in result:
                result.append(group)
        return result


class EcosystemSection(PluginConfigBase):
    """交给现有主动插件的阅读素材，不发表评论、不直接发QQ。"""

    __ui_label__ = "Neko主动聊天素材"
    __ui_order__ = 6
    enabled: bool = Field(default=False, description="允许Neko主动插件领取已读视频资料；启用后不再直接发送评论后群分享，群范围仍用上方share.qq_group_ids")
    min_interest: float = Field(default=0.55, ge=0, le=1, description="进入聊天候选池的最低兴趣分，与评论门槛独立")
    account_id: str = Field(default="", description="可选限定QQ机器人账号；同群多账号不明确时拒绝，不是B站UID")
    qq_friend_ids: List[str] = Field(default_factory=list, max_length=10,
        description="允许查询B站手记及接收主动分享的QQ私聊对象；留空不授权，分享还须主动插件允许同一好友")

    @field_validator('qq_friend_ids')
    @classmethod
    def validate_friends(cls, values):
        return ShareSection.validate_groups(values)
    daily_max: int = Field(default=2, ge=1, le=20, description="每群每天素材机会上限，按北京时间计；未确认机会保守占用，明确释放例外，不等于已发送或目标数")
    interval_minutes: int = Field(default=180, ge=1, le=1440, description="同群素材机会最小间隔（分钟），非到点必发；仍须主动插件的时段/概率/冷却通过，不改变其调度")


class StageModelSection(PluginConfigBase):
    """空任务、空候选和0时限继承共用模型；只影响本插件独立后台请求，不加入聊天Planner循环。"""

    task: str = Field(default="", max_length=200, json_schema_extra={
        "label": "模型任务（空为继承）", "hint": "填写宿主已有任务名，如 planner、replyer。只借用模型路由，不带聊天上下文、工具或记忆。显式候选存在时，改任务不会替换候选模型。"})
    candidates: List[str] = Field(default_factory=list, json_schema_extra={
        "label": "候选模型（空为继承）", "hint": "填写宿主已配置的具体模型名，按顺序尝试；非空覆盖共用候选，空继承。候选优先于任务自动选模；要清除继承候选，开启下面的改用任务自选。"})
    use_task_models: bool = Field(default=False, json_schema_extra={
        "label": "改用任务自选模型", "hint": "开启时忽略本阶段和共用候选列表，由最终任务选择模型。关闭时按候选继承规则执行。"})
    timeout_seconds: int = Field(default=0, ge=0, le=180, json_schema_extra={
        "label": "高级 · 单候选时限（秒，0为继承）", "hint": "0继承共用单候选时限；覆盖值10～180秒。不会修改宿主任务的输出token预算。"})

    @field_validator('task')
    @classmethod
    def strip_task(cls, value):
        return value.strip()

    @field_validator('candidates')
    @classmethod
    def normalize_candidates(cls, values):
        return ModelSection.normalize_candidates(values)

    @field_validator('timeout_seconds')
    @classmethod
    def check_timeout(cls, value):
        if value and value < 10:
            raise ValueError('单候选时限须为0（继承）或10～180秒')
        return value


class DecisionModelSection(StageModelSection):
    """仅自主浏览开启时：判断刷不刷、选新视频和下次考虑时间。旧评论候选池选片仍用共用模型。"""
    __ui_label__ = "自主判断模型"
    __ui_order__ = 4


class ReflectionModelSection(StageModelSection):
    """仅自动发表评论关闭时生成阅读感想；不影响手动评论预览、旧评论审核或跟进。默认完整继承共用设置。"""
    __ui_label__ = "阅读感想模型"
    __ui_order__ = 5
    decision_budget_seconds: int = Field(default=0, ge=0, le=900, json_schema_extra={
        "label": "高级 · 感想总时限（秒，0为继承）", "hint": "0继承共用处理总时限；覆盖值20～900秒。全候选共用此时限，不增加审核或润色调用。"})
    content_max_chars: int = Field(default=0, ge=0, le=24000, json_schema_extra={
        "label": "高级 · 正文字符预算（0为继承）", "hint": "0继承共用正文预算；覆盖值500～24000字符。仅摘要/字幕，不读取视频画面或音频。"})

    @field_validator('decision_budget_seconds', 'content_max_chars')
    @classmethod
    def check_budget(cls, value, info):
        minimum = 20 if info.field_name == 'decision_budget_seconds' else 500
        if value and value < minimum:
            raise ValueError(f'须为0（继承）或至少{minimum}')
        return value


class AutopilotConfig(PluginConfigBase):
    plugin: PluginSection = Field(default_factory=PluginSection)
    browse: BrowseSection = Field(default_factory=BrowseSection)
    comment: CommentSection = Field(default_factory=CommentSection)
    model: ModelSection = Field(default_factory=ModelSection)
    replies: ReplySection = Field(default_factory=ReplySection)
    share: ShareSection = Field(default_factory=ShareSection)
    ecosystem: EcosystemSection = Field(default_factory=EcosystemSection)
    decision_model: DecisionModelSection = Field(default_factory=DecisionModelSection)
    reflection_model: ReflectionModelSection = Field(default_factory=ReflectionModelSection)


def stage_config(cfg: AutopilotConfig, stage: str) -> AutopilotConfig:
    """Resolve a per-call copy; never mutate persistent values or the round's CAS snapshot."""
    if stage not in {'decision', 'reflection'}:
        return cfg
    override = getattr(cfg, stage + '_model')
    resolved = cfg.model_copy(deep=True)
    for name in ('task', 'timeout_seconds', 'decision_budget_seconds', 'content_max_chars'):
        if value := getattr(override, name, None):
            setattr(resolved.model, name, value)
    if override.use_task_models:
        resolved.model.candidates = []
    elif override.candidates:
        resolved.model.candidates = list(override.candidates)
    return resolved


def reading_config_schema(schema):
    """Use native SectionRenderer.name to group fields without changing TOML paths.

    SDK2.20 emits group/depends_on, but Dashboard1.9.13 does not render them.
    Its existing section-name mapping supports these groups; every field appears once.
    """
    sections = schema['sections']
    groups = [
        ('rhythm', 'browse', '浏览节奏与活动时段', '到时间重新考虑，不保证一定刷；暂停须手动恢复。',
         'auto_start autonomous_enabled interval_seconds max_check_minutes active_start_hour active_end_hour timezone', False),
        ('limits', 'browse', '阅读上限', '手记和旧评论共用视频额度；上限不是目标，视频数不等于模型调用次数。',
         'videos_per_round videos_per_day max_duration_seconds', False),
        ('interests', 'browse', '兴趣与过滤', '手记与旧评论均采用；更积极探索仅影响自主判断。',
         'interests explore_more blocked_keywords blocked_up_uids max_per_up max_per_topic', False),
        ('models', 'model', '共用模型与默认预算', '两个阶段未覆盖时沿用这里。显式候选优先于任务选模；任务仍提供输出预算等默认参数。',
         'task candidates timeout_seconds decision_budget_seconds content_max_chars', False),
        ('decision_model', 'decision_model', '自主判断模型', DecisionModelSection.__doc__,
         'task candidates use_task_models timeout_seconds', False),
        ('reflection_model', 'reflection_model', '阅读感想模型', ReflectionModelSection.__doc__,
         'task candidates use_task_models timeout_seconds decision_budget_seconds content_max_chars', False),
        ('ecosystem', 'ecosystem', '主动聊天素材与分享机会', '提供阅读素材，由主动聊天决定采用；这里不是QQ定时发送频率。群授权在下一组。',
         'enabled daily_max interval_minutes qq_friend_ids account_id min_interest', False),
        ('group_scope', 'share', 'QQ群资料授权', '与主动插件群名单取交集；不因此授权私聊。', 'qq_group_ids', False),
        ('plugin', 'plugin', '插件开关与管理员', '总开关与聊天管理命令权限；手记模式由旧评论组的自动发表评论开关决定。',
         'enabled admin_users config_version', True),
        ('network', 'browse', '高级 · 读取失败等待', '账号、推荐等只读请求的网络退避，不自动重放失败手记。',
         'read_retry_base_seconds', True),
        ('comment', 'comment', '旧功能 · B站评论', '自动发表评论关闭时，自动轮次写手记；本组其余参数只影响旧评论/预览与跟进，不控制手记长度或频率。',
         'publish_enabled per_day min_interval_seconds max_chars min_interest similarity_threshold', True),
        ('replies', 'replies', '旧功能 · 跟进评论回复', '开启跟进会检查已有评论的回复并可调用模型；实际发送另需自动发表评论开启。关闭跟进才停止此链。',
         'enabled interval_seconds per_day analyses_per_day per_thread min_interval_seconds max_age_hours', True),
        ('comment_pool', 'browse', '旧功能 · 评论候选池', '仅自动发表评论开启时采用；与阅读手记保留容量无关。',
         'backlog_max_items backlog_max_age_hours', True),
        ('comment_model', 'model', '旧功能 · 评论风格与依据复核', '仅旧评论、跟进和直接分享使用。阅读感想不走复核/润色链，手记本身保留至主动整理。',
         'extra_style review_timeout_seconds evidence_retention_days', True),
        ('direct_share', 'share', '旧功能 · 评论后直接群分享', '仅生态素材关闭且新B站评论提交成功后运行；生态开启时整组不参与主动聊天。',
         'polish_enabled polish_model polish_timeout_seconds total_timeout_seconds', True),
    ]
    overrides = {
        'plugin.enabled': ('启用插件', '关闭停止后台业务。开启不解除手动或异常暂停；登录后是否自动开始见浏览节奏。'),
        'browse.autonomous_enabled': ('自主决定刷不刷', '开启：先判断是否浏览、选择新视频与下次考虑；关闭：按最短间隔固定浏览。到时间不保证一定刷。'),
        'browse.explore_more': ('更积极探索', '仅自主判断开启时生效：更愿意尝试感兴趣的新视频，仍可休息，不保证阅读数量。'),
        'browse.videos_per_round': ('每轮最多阅读视频数', '每轮最多读取分析的视频数，1～10；是上限而非目标。旧评论模式每轮最多发1条，手记不受这条发送限制。'),
        'browse.videos_per_day': ('每日视频阅读上限', '手记与旧评论/手动预览共用，达到上限当天停止新视频分析；按所选时区零点统计。不是每日模型调用次数。'),
        'browse.max_per_up': ('高级 · 每轮同UP主上限', '同时受每轮视频总上限约束，避免一轮都来自同一个UP主。'),
        'browse.max_per_topic': ('高级 · 每轮同题材上限', '仅按已有分区题材计数，未知题材不强行分类；同时受每轮总上限约束。'),
        'model.task': ('默认模型任务', '填写宿主已有任务名，默认replyer。判断和感想未覆盖时均继承；有显式候选时只改任务不会改变候选模型。'),
        'model.candidates': ('默认候选模型（顺序尝试）', '填写宿主已配置的具体模型名；非空优先于任务选模，空由任务选择。超时或无有效正文才尝试下一项，其他失败不保证切换。'),
        'model.decision_budget_seconds': ('感想与旧评论总时限（秒）', '感想全候选、旧评论/跟进生成及复核共用的总时限，默认240秒＝4分钟。自主判断仍按单候选时限×候选数＋5秒外层保护，不用本项。'),
        'model.content_max_chars': ('正文字符预算', '摘要或字幕最多提供12000字符，长字幕按片段选择；可由阅读感想阶段覆盖。不是输出token预算，不读取画面或音频。'),
        'model.extra_style': ('旧评论/直接分享风格', '只补充旧评论、跟进及直接群分享文风。阅读感想使用原人设与兴趣，不使用本项。'),
        'model.evidence_retention_days': ('旧评论依据缓存天数', '只控制旧评论引用片段的临时依据缓存，不删除手记正文、感想或历史账本。'),
        'comment.publish_enabled': ('自动发表评论（开启即切旧评论模式）', '关闭：自动浏览写阅读手记，不生成旧评论预览。开启：自动轮次改走旧评论链并可向B站发送。手动preview始终走旧评论预览。'),
        'ecosystem.enabled': ('向主动聊天提供阅读素材', '开启后沿已有主动聊天出口提供素材，并停用旧评论后直接群分享；需要双方名单授权。'),
        'ecosystem.daily_max': ('每会话每日素材机会上限', '每群或每私聊分别计数，按北京时间；未知机会保守占用。不是QQ发送量、目标数，也不是每日视频数。'),
        'ecosystem.interval_minutes': ('同会话机会间隔（分钟）', '群聊和私聊分别计时，非到点必发；实际采用仍由主动聊天的时段、概率与冷却决定。'),
        'ecosystem.qq_friend_ids': ('允许提供资料的私聊QQ号', '每项一个现有好友QQ号，空不授权私聊；主动分享还须主动插件允许同一好友。'),
        'ecosystem.account_id': ('高级 · QQ机器人账号限制', '可选限制机器人QQ账号，不是聊天对象或B站UID；同一目标多账号身份不明确时拒绝。'),
        'ecosystem.min_interest': ('高级 · 素材最低兴趣分', '旧评论使用模型兴趣分。手记不要求模型打分：有感想且有分享缘由记为1，否则为0；还须有分享缘由才登记素材。因此调高本项不会使有分享缘由的完整手记更挑剔。'),
    }
    output = {}
    for order, (key, source, title, description, names, collapsed) in enumerate(groups):
        fields = {}
        for position, name in enumerate(names.split()):
            field = dict(sections[source]['fields'][name], order=position)
            if presentation := overrides.get(source + '.' + name):
                field.update(label=presentation[0], hint=presentation[1], description=presentation[1])
            fields[name] = field
        output[key] = dict(sections[source], name=source, title=title, description=description,
                           order=order, collapsed=collapsed, fields=fields)
    tabs = [('reading', '浏览', ['rhythm', 'limits', 'interests']),
            ('models', '模型分工', ['models', 'decision_model', 'reflection_model']),
            ('sharing', '分享机会', ['ecosystem', 'group_scope']),
            ('advanced', '旧功能与高级', ['plugin', 'network', 'comment', 'replies', 'comment_pool', 'comment_model', 'direct_share'])]
    return {**schema, 'sections': output, 'layout': {'type': 'tabs', 'tabs': [
        {'id': key, 'title': title, 'sections': names, 'order': order}
        for order, (key, title, names) in enumerate(tabs)]}}
