---
name: B站浏览手记
description: 继承麦麦宿主主题、按天连读的浏览手记界面
colors:
  primary: "var(--maibot-primary,#2563b4)"
  primary-foreground: "var(--maibot-primary-foreground,#fff)"
  foreground: "var(--maibot-foreground,#202c3b)"
  background: "var(--maibot-background,#f7f8fa)"
  surface: "var(--maibot-surface,#fff)"
  soft: "var(--maibot-soft,#edf1f6)"
  muted: "var(--maibot-muted,#576779)"
  border: "var(--maibot-border,#d6dde5)"
  destructive: "var(--maibot-destructive,#9b3030)"
typography:
  headline:
    fontFamily: "var(--maibot-font-body,system-ui,sans-serif)"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.4
  title:
    fontFamily: "var(--maibot-font-body,system-ui,sans-serif)"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.75
  body:
    fontFamily: "var(--maibot-font-body,system-ui,sans-serif)"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.75
  thought:
    fontFamily: "var(--maibot-font-body,system-ui,sans-serif)"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.9
  label:
    fontFamily: "var(--maibot-font-body,system-ui,sans-serif)"
    fontSize: ".875rem"
    fontWeight: 400
    lineHeight: 1.75
rounded:
  control-and-inset: "8px"
spacing:
  compact: "8px"
  inline: "12px"
  inset: "16px"
  entry-start: "20px"
  page-inline: "24px"
  entry-end: "28px"
  section: "32px"
components:
  button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control-and-inset}"
    padding: "7px 12px"
  button-hover:
    backgroundColor: "{colors.soft}"
  button-disabled:
    textColor: "{colors.muted}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control-and-inset}"
    padding: "7px 12px"
  related:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.control-and-inset}"
    padding: "13px 16px"
  evidence:
    textColor: "{colors.muted}"
    typography: "{typography.label}"
  management:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.control-and-inset}"
    padding: "18px"
  notice:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.control-and-inset}"
    padding: "16px"
  notice-error:
    textColor: "{colors.destructive}"
  entry:
    textColor: "{colors.foreground}"
    padding: "20px 0 28px"
---

# Design System: B站浏览手记

## Overview

**Creative North Star: "按天连读"**

这是宿主插件页内的阅读界面：正文先于管理，日期串联长短自然的感想，视频作为来源引用。视觉沿用麦麦宿主的主题与正文字体，以同底色、留白、细分隔线和相邻色阶组织内容。

本记录提取自实际 `journal.html`，并对照 `PRODUCT.md`、`docs/JOURNAL_DESIGN.md` 及桌面浅色、手机浅色、手机深色截图。沿用已确认的方向描述，不新增品牌命名或设计方案。截图中的海洋生物内容是合成资料，不代表线上浏览经历。

**Key Characteristics:**
- 宿主主题优先，明暗主题共享结构。
- 日期、感想正文、来源与旧手记关联构成阅读层次。
- 无卡片阴影，以相邻色阶表达引用与按需管理。
- 手机单列，保留原生日期输入、按钮与折叠交互。

取证截图：`C:/Users/NekoLaska/AppData/Local/Temp/opencode/bilibili-journal-qa/` 下的 `journal-1440.png`、`journal-390.png`、`journal-dark-390.png`。截图用于核对构图与主题变化；精确数值以当前 CSS 及其最终覆盖为准。

## Colors

配色是宿主的语义映射，不是插件自己的固定品牌色；frontmatter 保存实际 CSS 变量表达式。

### Primary
- **宿主主色（primary）**：来源链接、键盘焦点轮廓、输入光标和选区底色。
- **主色上文字（primary-foreground）**：选中文字的前景色；普通按钮并不使用实心主色填充。

### Neutral
- **正文（foreground）**与**页面底色（background）**：承载连续阅读。
- **控件表面（surface）**：普通按钮、日期和搜索输入。
- **相邻底色（soft）**：旧感想引用、管理展开区、空态与提示，以及可用按钮悬停。
- **次级文字（muted）**：运行状态、时间、引用标签、来源作者、分享说明与禁用按钮文字。
- **细边界（border）**：控件描边和相邻手记分隔线。

错误提示使用语义色 **destructive**，不是第二套装饰强调色。

**The Host Theme Rule.** 始终使用现有 `--maibot-*` 主题变量；逗号后的 fallback 只在宿主未提供变量时生效，不是固定品牌色。`color-scheme` 默认 light，根元素带 `dark` 类时为 dark；插件没有另一套硬编码暗色调色板。

## Typography

**Body Font:** 宿主 `--maibot-font-body`，缺省为系统无衬线字体。标题、正文、按钮与表单共用这一字族，没有外部字体、独立展示字体或等宽标签体系。

### Hierarchy
- **Headline**：页面标题；尺寸与行高见 `headline`。粗体来自原生标题默认行为。
- **Title**：日期分组；见 `title`，在正文之前建立清晰时间边界。
- **Body**：运行状态、管理内容及一般段落；见 `body`。
- **Thought**：感想正文；桌面见 `thought`，手机行高调整为 1.85。保留输入换行，不强行等长或截断。
- **Label**：时间、话题元信息、来源、依据折叠项与分享说明；见 `label`。日期/搜索工具区也使用这一字号，刷新和管理操作继承正文大小。

标题没有额外字距装饰。正文和长标题允许在必要处换行，旧感想与引用保留自然段。

## Layout

当前最终 CSS 将居中页面最大宽度设为 **920px**（含内边距），桌面内边距为上下 28px、左右 24px。1440px 截图中正文区域由页面框自然限定。手记是连续文档流，相邻条目之间有细线，没有网格卡片或侧栏。

`docs/JOURNAL_DESIGN.md` 的早期正文 78ch 约定已被实际页面末尾的 `.entry{max-width:none}` 覆盖；本记录采用最终实现，不把 78ch 或初始页面 1024px 当作现行限制。

标题和刷新按钮分列，可换行；日期工具靠左，搜索在桌面靠右。工具区间隙 8px，通常元信息/操作组间隙 12px。日期组上方留 32px，下方留 10px；条目内边距见 `entry`。正文上下留 10px/14px，旧感想上下留 14px，管理区上方留 32px。

唯一响应断点为 **max-width:640px**：页面内边距改为 20px 16px，搜索独占一行并伸展，条目下内边距改为 24px，管理信息从标签/值双列变成单列。桌面日期输入最大宽度 165px，搜索输入宽 190px；手机搜索输入通过 flex 分配剩余宽度。二维码宽 220px，并受容器最大宽度限制。

## Elevation & Depth

界面没有 box-shadow、渐变、背景模糊或抬升动效。深度来自 soft 与 background 的相邻色阶、控件细描边和条目分隔线；键盘焦点使用外轮廓而不是阴影。浅色与深色截图保留相同层次。

## Shapes

柔和小圆角只用于控件、旧感想引用、管理区和提示/空态，统一使用 `control-and-inset`。正文条目本身没有圆角外壳。描边为 1px 实线；没有胶囊标签、装饰徽章或封面图片。折叠项保留原生 disclosure 标记。

## Components

### Buttons
- 普通描边按钮是唯一已实现的视觉变体，刷新、日期切换、查找、翻页与管理命令共享表面/边框规则；不另造“主按钮”。
- 最小高度 44px，内边距见 `button`；可用按钮 hover 改用 soft。
- 全局 `:focus-visible` 使用主色 2px 轮廓，偏移 3px。没有自定义 active 效果或 transition。
- 查询或命令处理中，所有按钮禁用；禁用文字转 muted，使用默认光标且不响应 hover 底色变化。

### Inputs / Fields
- 日期与搜索输入沿用按钮的描边、圆角与最小高度；占位文字为 muted，光标为 primary。
- 搜索有可访问名称与 200 字符上限；日期有可见标签和可访问名称。日期选取与日历图标保留浏览器原生行为，并跟随 color-scheme。
- 加载时禁用的是按钮，输入字段本身不被统一禁用；不记录未实现的字段错误样式。

### Navigation
- 日期工具是筛选，不是 tab 导航：“今天”“全部日期”和日期输入，配合话题/视频搜索；没有选中胶囊或自定义 active 色。
- 首次读取当天，查询与日期变化重新读取；“继续往前读”仅在有后续游标时出现，追加旧记录并延续日期分组。

### Journal / Related Reading
- 单条手记顺序为时间/话题、感想、来源、关联旧感想、可选依据与分享说明。
- 感想优先使用 thought，其次 reason，再使用对应状态文案；无感、未读到正文、未完成、停止、中断、阅读中保留各自含义，不伪造感想。
- 来源是带下划线的主色链接，作者为 muted。只对有效 BV 标识构造 B站新窗口链接；正文、标题及引用以纯文本渲染。
- 旧感想是 soft 内嵌区域，标签“想起之前”在上，旧正文在下；不是独立可点击卡片。
- “读到的依据”使用原生 details，summary 为 muted、最小高度 32px，正文按需展开；此处不是按钮的 44px 规则。
- 分享结果以次级文字呈现；只有分享理由时显示“想到可以聊聊”折叠项。素材提供、未知发送与确认送达不可混写。

### Management
- “浏览与账号管理”默认折叠，标题字重 600；展开后显示恢复、暂停、扫码登录及状态详情。
- 信息标签为 muted；桌面定义列表为 110px 标签列与可伸缩内容列，手机单列。二维码仅在收到有效 PNG data URL 时显示，否则清除图片来源并隐藏。
- 管理展开且页面可见、无操作进行时，每 5 秒更新概况；换号立即清理旧手记、翻页游标和日期分组，再读取新账号内容，读取失败也不恢复旧账号视图。

### Feedback / States
- 初始标题状态为“正在读取”，内容区为“正在翻开手记…”，以 muted 表示读取中；内容区使用 aria-busy。
- 空记录：“这段时间还没有留下手记。”；未登录：“登录B站后，新的阅读经历会留在这里。”，两者使用 soft 提示区域。
- 页面提示具有 role=status；错误切换为 destructive 文字，包含实际错误信息。普通刷新失败保留已有内容，首次失败清除初始读取占位。
- 暂停状态及原因在标题下的概况文字中表达，不替换成错误弹窗。命令有忙碌门禁与反馈，旧查询响应被代次检查丢弃。
- 正文不写入浏览器持久存储；读操作不生成新内容。`hidden` 元素始终不占布局空间。

## Do's and Don'ts

### Do:
- **Do** 继承宿主主题和字体，在浅色与深色中保留同一阅读层次。
- **Do** 让真实感想保留自然长短、换行和来源，管理信息按需展开。
- **Do** 使用最终 920px 页面框、640px 手机断点和现有控件焦点规则。
- **Do** 区分空记录、未登录、失败、暂停、无感及不同分享阶段。

### Don't:
- **Don't** 把主题 fallback 色值或深色截图当作固定品牌调色板。
- **Don't** 添加卡片阴影、假纸张、装饰统计或未经实现的控件变体。
- **Don't** 把合成截图内容、旧评论预览或素材提供描述成真实新手记或确认送达。
- **Don't** 将被末尾 CSS 覆盖的 78ch 和 1024px 记为现行布局约束。
