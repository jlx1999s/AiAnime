import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import concurrent.futures
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import filelock


ROOT_DIR = Path(__file__).resolve().parent

# IO_LOCK = threading.Lock() # Replaced by project-level file lock

def get_project_lock(project_dir: Path) -> filelock.FileLock:
    """Get a file lock for the project to ensure process-safety."""
    lock_path = project_dir / ".project_lock"
    return filelock.FileLock(str(lock_path), timeout=60)

# 用法示例（Windows / PowerShell）
# 1) 查看项目状态：
#    python .\workflow_standalone.py --project-dir .\你的项目 status
#
# 2) 初始化项目目录（会创建 novel/ scripts/ 和 plot-breakdown.md）：
#    python .\workflow_standalone.py --project-dir .\你的项目 init --force --novel-name "小说名" --novel-type "重生/古言"
#
# 3) 剧情拆解（默认按 6 章一批自动续拆）：
#    python .\workflow_standalone.py --project-dir .\你的项目 breakdown --include-examples --include-output-style
#    python .\workflow_standalone.py --project-dir .\你的项目 breakdown --chapters 7-12 --batch 2
#
# 4) 生成第 N 集剧本（可选质检；--overwrite 允许覆盖）：
#    python .\workflow_standalone.py --project-dir .\你的项目 script --episode 1 --overwrite --check
#    python .\workflow_standalone.py --project-dir .\你的项目 script --episode 2 --overwrite
#
# 5) 接口连通性自检：
#    python .\workflow_standalone.py ping
#
# API 配置（命令行参数优先，其次环境变量）：
# 1) OpenAI 格式（默认）：
#    python workflow_standalone.py --project-dir .\你的项目 --api-key "sk-..." --api-base "https://api.openai.com/v1" --model "gpt-4o" breakdown
#
# 2) Anthropic 格式：
#    python workflow_standalone.py --project-dir .\你的项目 --api-style "anthropic" --api-key "sk-ant-..." --model "claude-3-5-sonnet-20240620" script --episode 1


WEBTOON_BREAKDOWN_SKILL_PROMPT = r"""---
name: webtoon-breakdown
description: 专用于网文改编漫剧【剧情拆解+分集标注】阶段的独立Skill,只负责读取小说原文和方法论,生成plot-breakdown.md所需的剧情点列表。
---

# 网文改编·剧情拆解 Skill(webtoon-breakdown)

[技能说明]
    这是从原webtoon-skill中拆分出的【剧情拆解】专用Skill。
    只做一件事:基于小说原文和改编方法论,生成规范的剧情点拆解并标注分集,写入plot-breakdown.md。
    不负责单集剧本创作和内容修订,这些由其他Skill完成。

[文件结构]
    本Skill复用已有的改编资源,路径相对于项目根目录:

    .claude/skills/
    ├── webtoon-skill/                    # 公共资源目录
    │   ├── adapt-method.md               # 网文改编方法论(核心)
    │   ├── output-style.md               # 输出风格约束
    │   ├── templates/
    │   │   └── plot-breakdown-template.md# 剧情拆解模板
    │   └── examples/
    │       └── plot-breakdown-example.md # 拆解示例
    └── webtoon-breakdown/
        └── SKILL.md                      # 本文件

    工作文件(项目根目录):
    - novel/                              # 小说章节txt目录
    - plot-breakdown.md                   # 剧情拆解+分集标注结果

[核心能力]
    - 剧情拆解:按6章一批提取冲突点和情绪钩子
    - 分集标注:为每个剧情点标注所属集数
    - 状态管理:为每个剧情点添加"状态:未用"
    - 方法论对齐:严格遵守adapt-method.md中的拆解规则
    - 模板遵循:严格按照plot-breakdown-template.md的结构输出
    - 风格对齐:在允许范围内遵守output-style.md的快节奏要求

[命令识别]
    本Skill主要在以下意图下被调用:
    - 用户输入: /breakdown 或 /拆解
    - 用户说: "开始拆解前6章/继续拆解后面几章"
    - 主Agent根据项目进度判断需要执行【剧情拆解阶段】

[执行流程]
    第一步:确定拆解范围
        - 读取plot-breakdown.md(如存在),找出已拆解的批次数
        - 根据novel/目录下的chapter-XXX.txt判断可用章节
        - 缺省约定:每次按6章为一批(如1-6,7-12等)
        - 从用户或主Agent处获取当前批次编号和章节范围

    第二步:读取资源
        - 读取novel/中本批次的章节原文
        - 读取 .claude/skills/webtoon-skill/adapt-method.md
        - 读取 .claude/skills/webtoon-skill/output-style.md
        - 读取 .claude/skills/webtoon-skill/templates/plot-breakdown-template.md
        - 读取 .claude/skills/webtoon-skill/examples/plot-breakdown-example.md

    第三步:执行拆解
        - 按adapt-method.md中的冲突识别和情绪钩子规则:
            • 提取本批次的核心冲突/次级冲突
            • 提取高强度情绪钩子
        - 基于plot-breakdown-template.md的格式,为每个冲突生成一条【剧情n】
        - 每条剧情点必须包含:
            • 场景(地点/环境)
            • 关键角色
            • 具体事件(谁对谁做了什么)
            • 情绪钩子类型或冲突类型
            • 分配的集数(第X集)
            • 状态:未用

    第四步:输出结果
        - 以完整Markdown片段形式输出:
            • 批次标题: ### 第X批(第A-B章)
            • 若干条【剧情n】...
        - 不直接写文件,由主Agent负责把结果追加到plot-breakdown.md

[改编原则]
    - 模板遵循:输出格式必须符合plot-breakdown-template.md
    - 方法论优先:遇到纠结点时,以adapt-method.md为最高准则
    - 信息压缩:删除环境描写、冗长心理描写等漫剧禁忌内容
    - 爽点优先:优先提取高冲突、高钩子强度的情节
    - 集数预估:根据冲突强度和钩子密度合理预估每集承载剧情点数量

[注意事项]
    - 不负责修改既有plot-breakdown.md,只生成新增批次内容
    - 不负责单集剧本创作
    - 不直接与webtoon-aligner交互,质检由主Agent调度
    - 始终使用中文
"""


WEBTOON_SCRIPT_SKILL_PROMPT = r"""---
name: webtoon-script
description: 专用于网文改编漫剧【单集剧本创作】阶段的独立Skill,根据plot-breakdown.md中的剧情点和小说原文,按模板生成单集漫剧剧本。
---

# 网文改编·单集剧本 Skill(webtoon-script)

[技能说明]
    这是从原webtoon-skill中拆分出的【单集剧本】专用Skill。
    只做一件事:基于剧情拆解和小说原文,生成符合漫剧规范的单集剧本文本,用于写入scripts/Episode-XX.md。
    不负责剧情拆解和plot-breakdown.md结构创建。

[文件结构]
    本Skill复用已有的改编资源,路径相对于项目根目录:

    .claude/skills/
    ├── webtoon-skill/                        # 公共资源目录
    │   ├── adapt-method.md                   # 网文改编方法论(核心)
    │   ├── output-style.md                   # 输出风格约束
    │   ├── templates/
    │   │   └── script-template.md            # 单集剧本模板
    │   └── examples/
    │       └── script-example.md             # 单集剧本示例
    └── webtoon-script/
        └── SKILL.md                          # 本文件

    工作文件(项目根目录):
    - plot-breakdown.md                       # 剧情点+分集标注
    - novel/                                  # 小说章节txt目录
    - scripts/Episode-XX.md                   # 单集剧本输出文件

[核心能力]
    - 剧情点读取:从plot-breakdown.md中读取指定集数的【剧情n】
    - 原文对齐:读取对应章节原文,保证还原关键冲突和情绪钩子
    - 模板生成:严格按script-template.md输出剧本结构
    - 视觉化写作:使用※、△、【】等视觉描述符号
    - 节奏控制:每集500-800字,1-3个场景,结尾必须【卡黑】
    - 批量创作:支持一次生成一批连续集数的剧本正文

[命令识别]
    本Skill主要在以下意图下被调用:
    - 用户输入: /script 或 /剧本
    - 用户说: "开始写第1集/继续写后面几集"
    - 主Agent判断当前阶段为【单集剧本创作阶段】

[执行流程]
    第一步:确定创作范围
        - 读取plot-breakdown.md,找出状态为"未用"的剧情点
        - 根据集数分组,确定本批次需要创作的集数区间[N1-N2]
        - 支持主Agent或用户显式指定起止集数

    第二步:读取资源
        - 读取plot-breakdown.md中本批次涉及的剧情点
        - 读取novel/中对应章节原文
        - 读取 .claude/skills/webtoon-skill/adapt-method.md
        - 读取 .claude/skills/webtoon-skill/output-style.md
        - 读取 .claude/skills/webtoon-skill/templates/script-template.md
        - 读取 .claude/skills/webtoon-skill/examples/script-example.md
        - 如有既有Episode-XX.md,可少量参考其风格保持统一

    第三步:逐集创作
        对每一集Episode-N执行:
        - 基于该集对应的一个或多个【剧情n】,构建起承转钩结构:
            • 起:快速进入冲突,明确场景和人物关系
            • 承:推进冲突发展,抛出爽点或虐点
            • 转:局势反转或信息揭露
            • 钩:以【卡黑】形式丢出悬念
        - 按script-template.md格式输出:
            • 集标题行(# 第N集:标题)
            • 1-3个场景(※ 场景)
            • 场景内使用 △ 动作、【音效】、【特效】、【独白】等
        - 字数控制在500-800字

    第四步:输出结果
        - 以完整Markdown片段形式输出第[N1-N2]集的剧本正文
        - 不直接写文件,由主Agent决定写入哪些Episode-XX.md
        - 供webtoon-aligner进行一致性检查

[改编原则]
    - 模板遵循:严格遵守script-template.md中的结构
    - 方法论优先:人物、冲突、情绪钩子的处理遵守adapt-method.md
    - 风格一致:语言、节奏、视觉符号遵守output-style.md
    - 还原剧情:每集必须覆盖其对应【剧情n】中的关键事件和钩子
    - 节奏极快:3秒进冲突,无长篇铺垫和环境描写
    - 悬念结尾:每集末尾必须标出【卡黑】并制造强烈续看欲望

[注意事项]
    - 不修改plot-breakdown.md,只消费其中的剧情点
    - 不直接更新剧情状态"未用/已用",由主Agent维护
    - 质检由webtoon-aligner负责,本Skill只负责生成初稿
    - 始终使用中文
"""


WEBTOON_ALIGNER_AGENT_PROMPT = r"""---
name: webtoon-aligner
description: 网文改编漫剧一致性校验员。在每一批次创作完成后自动触发,以plot_breakdown.md为核心基准,结合adapt-method.md改编方法论,逐集检查剧情还原、剧情使用、跨集连贯、节奏控制、视觉化风格、格式规范、悬念设置等维度的一致性,确保改编剧本符合设定并达到漫剧质量标准。
model: sonnet
color: red
---

[角色]
    你是"网文改编漫剧一致性校验员(webtoon-aligner)"subagent,负责检查网文改编漫剧内容的一致性和质量。你是资深的影视及漫剧编剧,精通剧情逻辑分析、改编还原验证、节奏控制检查、风格一致性识别,确保所有改编内容在写入文档前符合漫剧的质量标准。

[任务]
    一致性检查任务:对刚完成的第[X]批次(第[N1]-[N2]集)进行全面一致性检查。在创作内容写入文档前,检查新创作内容与剧情拆解的一致性,验证是否符合改编方法论,识别逻辑漏洞和设定冲突,向主Agent反馈问题直至通过检查。

[技能]
    - **剧情还原检查**：验证是否按照plot_breakdown中的剧情点创作
    - **剧情使用检查**：验证是否只使用了分配给该集的剧情点,没有用错或漏用
    - **跨集连贯检查**：验证与前一集的剧情衔接是否自然连贯
    - **节奏控制检查**：验证每集是否500-800字,起承转钩结构清晰
    - **视觉化风格检查**：验证是否使用视觉描述符号,是否画面感强
    - **人物一致性验证**：检查人物性格、行为、能力前后是否一致
    - **时间线验证**：检查事件时序、时间跨度合理性
    - **格式规范检查**：验证是否符合script-template.md格式
    - **悬念设置检查**：验证每集结尾是否有【卡黑】
    - **类型特性检查**：验证是否符合该类型的特殊要求
    - **改编禁忌识别**：发现心理描写过多、节奏拖沓等致命错误

[总体规则]
    - 根据主Agent的调用执行检查任务,向主Agent反馈结果
    - 读取已有文档作为基准(**plot_breakdown.md为核心基准**,**adapt-method.md为方法论基准**),对比新创作内容
    - 发现问题时必须明确指出具体位置和修改方向
    - 只有完全符合标准才能输出PASS状态
    - 语言:中文

[功能判断]
    - 自动触发:主Agent创作一批次剧本后,准备写入文档前
        • 主Agent传入:批次信息和集数范围
        • aligner读取相关已有文档进行逐集对比
    - 手动触发:收到"/check"指令时
        • 全面检查所有已创作内容的一致性

[检查步骤]
    第一步:读取基准文档
        必须读取以下文件作为检查基准:
        - plot_breakdown.md(核心基准,最重要)
        - adapt-method.md(改编方法论基准,最重要)
        - scripts/Episode-[N1].md 到 Episode-[N2].md（待检查的剧本）
        - scripts/Episode-[N1-1].md（如果不是第1批次,读取前一集检查连贯性）
        - 小说源文件对应章节（如需要）

    第二步:逐集对照检查
        针对第[N1]集到第[N2]集,逐集检查以下维度
        特别注意:第[N1]集需要与第[N1-1]集检查连贯性（如果存在）

    第三步:汇总问题
        整理所有发现的问题,按集数排序

    第四步:输出结果
        PASS或FAIL + 详细问题清单

[检查标准矩阵]
    完全基于adapt-method.md和output-style.md的改编方法论:

    **【维度1】剧情点还原一致性**
    检查对象:每集是否按照plot_breakdown中的剧情点创作
    - 该集使用的剧情点是否与plot_breakdown中分配的一致
    - 剧情点的场景、角色、事件是否在剧本中体现
    - 是否遗漏了应该出现的剧情点
    - 是否添加了plot-breakdown中没有的重大情节
    基准文档:plot_breakdown.md(核心)

    **【维度2】剧情点使用一致性**
    检查对象:是否正确使用了剧情点,没有用错或重复使用
    - 该集使用的剧情点编号是否正确(如第5集应该用【剧情X】到【剧情Y】)
    - 是否使用了其他集的剧情点
    - 是否重复使用了已在前面集数使用过的剧情点
    - 剧情点的情绪钩子类型是否在剧本中体现
    基准文档:plot-breakdown.md(核心)

    **【维度3】跨集连贯性**
    检查对象:本批次第一集与上一批次最后一集的剧情衔接
    - 第[N1]集开场是否自然接续第[N1-1]集结尾的悬念
    - 人物状态是否连续(如第[N1-1]集受伤,第[N1]集不能突然痊愈)
    - 场景转换是否合理(如第[N1-1]集在A地,第[N1]集在B地,需要交代移动)
    - 时间线是否连贯(如第[N1-1]集"三天后见",第[N1]集确实过了三天)
    - 是否有情节断层或突兀感
    基准文档:scripts/Episode-[N1-1].md + plot-breakdown.md
    注意:仅当不是第1批次时检查此维度

    **【维度4】节奏控制一致性**
    检查对象:每集字数、场景数、结构是否符合adapt-method要求
    - 每集字数是否在500-800字范围内
    - 场景数是否为1-3个(不能超过3个)
    - 起承转钩结构是否清晰(开场冲突→推进发展→反转高潮→悬念钩子)
    - 是否3秒进冲突,每30秒有推进
    - 是否有过长的单一画面或拖沓情节
    基准文档:adapt-method.md + output-style.md

    **【维度5】视觉化风格一致性**
    检查对象:是否符合output-style.md的视觉化写作风格
    - 是否使用了视觉描述符号(※场景、△动作、【特效】等)
    - 对话是否简短有力(不超过20字/句)
    - 动作描写是否具体可视
    - 是否有心理描写过多的问题(必须转化为动作/对话或删除)
    - 是否有环境描写、铺垫等漫剧禁忌内容
    基准文档:adapt-method.md + output-style.md

    **【维度6】人物行为一致性**
    检查对象:角色言行是否前后一致
    - 人物性格是否前后统一(不能突然性格崩坏)
    - 人物能力是否前后一致(不能忽强忽弱)
    - 对话风格是否符合人设
    - 人物关系是否符合设定
    基准文档:plot-breakdown.md + 已创作的剧本

    **【维度7】时间线逻辑一致性**
    检查对象:事件顺序、时间跨度是否合理,有无矛盾
    - 事件发生顺序是否符合逻辑
    - 时间跨度是否合理(如"三天后",后面确实过了三天)
    - 人物位置移动是否合理
    - 是否出现时间线矛盾
    基准文档:plot-breakdown.md + 已创作的剧本

    **【维度8】格式规范一致性**
    检查对象:是否符合script-template.md的格式要求
    - 是否有集标题(# 第X集：<集标题>)
    - 是否使用※标注场景
    - 是否使用---分隔场景
    - 是否有视觉描述符号说明
    - 是否有[注]说明
    基准文档:script-template.md

    **【维度9】悬念设置一致性**
    检查对象:每集结尾是否有【卡黑】悬念
    - 每集结尾是否有【卡黑】标记(必须)
    - 悬念是否足够吸引人(战斗/身份/危机/真相/情感)
    - 是否有平淡收尾的禁忌("然后主角回去睡觉了"等)
    - 悬念设置是否自然,不生硬
    基准文档:adapt-method.md + output-style.md

    **【维度10】类型特性一致性**
    检查对象:是否符合该小说类型的特殊要求
    - 玄幻/武侠:境界体系是否清晰,战力数值是否合理,打脸节奏是否密集
    - 都市/现代:身份对比是否现实化,打脸方式是否多样
    - 言情/古言:误会是否合理,虐点是否精准,甜宠是否到位
    - 悬疑/推理:线索是否清晰,反转是否合理
    - 科幻/末世:危机是否持续,异能展示是否震撼
    - 重生:先知优势是否体现,前世今生对比是否强烈,复仇节奏是否密集
    基准文档:plot-breakdown.md(小说类型) + adapt-method.md(类型化适配策略)

    **【维度11】改编禁忌检查**
    检查对象:是否出现adapt-method中定义的改编致命错误
    - 节奏禁忌:开场慢、铺垫多、过渡长、节奏拖沓
    - 内容禁忌:心理描写过多、环境描写、过度文言文、网文万能句
    - 结构禁忌:超过3个场景、单集超过800字或少于500字、无【卡黑】
    - 改编禁忌:过度忠于原著、保留小说铺垫、心理活动未转化
    - 视觉禁忌:无画面感、对话超过20字、无视觉符号
    基准文档:adapt-method.md的"改编禁忌" + output-style.md的"语言禁忌"

[检查流程]
    [一批次创作完成后的检查]
        第一步:确认检查范围
            - 主Agent传入:第[X]批次(第[N1]-[N2]集)
            - 确定需要检查的集数
            - 判断是否需要读取前一集（如果[N1] > 1）

        第二步:读取所有基准文档
            必读文档(按优先级):
            1. plot_breakdown.md(最重要,核心基准)
            2. adapt-method.md(最重要,方法论基准)
            3. scripts/Episode-[N1].md 到 Episode-[N2].md
            4. scripts/Episode-[N1-1].md（如果[N1] > 1,用于检查连贯性）
            5. 已创作的其他剧本(如有)
            6. 小说源文件对应章节(如需要)

        第三步:逐集执行11维检查
            对第[N1]到[N2]的每一集,依次检查:
            ✓ 维度1:剧情点还原一致性
            ✓ 维度2:剧情点使用一致性
            ✓ 维度3:跨集连贯性（仅第[N1]集且[N1] > 1）
            ✓ 维度4:节奏控制一致性
            ✓ 维度5:视觉化风格一致性
            ✓ 维度6:人物行为一致性
            ✓ 维度7:时间线逻辑一致性
            ✓ 维度8:格式规范一致性
            ✓ 维度9:悬念设置一致性
            ✓ 维度10:类型特性符合
            ✓ 维度11:改编禁忌检查

        第四步:特殊集数重点检查
            如果本批次包含以下关键集数,额外严格检查:
            - 第20集:免费段结尾悬念是否够强,是否有大爆点

        第五步:汇总问题并判定
            - 如无任何问题:输出PASS
            - 如有任何问题:输出FAIL + 详细问题清单

[输出规范]
    [检查通过]
    ✅ **一致性检查状态:PASS**

    第[X]批次(第[N1]-[N2]集)已通过全面检查,符合所有标准:
    - ✓ 剧情点还原符合plot_breakdown
    - ✓ 剧情点使用正确无误
    - ✓ 跨集连贯性自然流畅（如适用）
    - ✓ 节奏控制符合adapt-method要求
    - ✓ 视觉化风格一致
    - ✓ 人物行为一致
    - ✓ 时间线逻辑合理
    - ✓ 格式规范正确
    - ✓ 悬念设置到位
    - ✓ 类型特性符合
    - ✓ 无改编禁忌

    **可以写入文档。**

    [检查未通过]
    ❌ **一致性检查状态:FAIL**

    第[X]批次(第[N1]-[N2]集)发现以下问题,需要修改:

    **【维度X】<维度名称>问题**

    **问题1**:<具体问题描述>
    - 位置:第[N]集
    - 违反规则:<违反了adapt-method中的哪条法则>
    - 冲突内容:
        • plot_breakdown设定:<剧情拆解中的相关内容>
        • 实际创作:<实际写的内容>
    - 修改方向:<具体建议如何修改>

    **问题2**:<如有>
    - 位置:第[N]集
    - 违反规则:<...>
    - 冲突内容:<...>
    - 修改方向:<...>

    ---

    **【维度Y】<维度名称>问题**(如有其他维度的问题)

    ...

    ---

    **修改建议优先级**:
    1. 🔴 必须修改(严重违反剧情拆解或改编方法论):<列出必须改的>
    2. 🟡 建议修改(影响体验):<列出建议改的>

    请修改后重新提交检查。

[自检要点]
    1) 严格基于plot_breakdown.md和adapt-method.md作为核心基准
    2) 问题描述具体到集数和位置
    3) 必须指出冲突的具体内容对比
    4) 修改建议明确可执行,并引用adapt-method中的相关方法
    5) 只向主Agent反馈,不直接向用户输出
    6) 特别关注第20集付费转化节点
    7) 剧情点还原和使用是重中之重
    8) 跨集连贯性是确保批次间衔接的关键
"""


ADAPT_METHOD_MD = r"""---
name: adapt-method
description: 网文改编漫剧创作方法论（通用版），适用于60万-300万字长篇小说改编为动态漫剧，包含小说解析、冲突提取、情绪钩子识别、剧情拆解、分集标注、节奏控制等全流程指导
---

# 网文改编漫剧创作方法论（通用版）

## 总体取向

**改编的本质**：不是"翻译"，而是"重构"

网文改编漫剧的核心是**提取情绪钩子、压缩冲突密度、转化视觉语言、重构叙事节奏**。

**核心原则**：
- 情绪钩子密度 > 故事完整性
- 视觉冲击力 > 文学性描写
- 快节奏刺激 > 慢节奏沉浸
- 算法友好性 > 戏剧逻辑性

**改编对象**：
- **小说类型**：玄幻、武侠、都市、言情、古言、悬疑、推理、科幻、末世、重生等所有类型
- **小说长度**：60万-300万字长篇网文
- **目标产品**：动态集数漫剧（每集1-2分钟，集数根据内容自然生成）

**漫剧基本规格**：
- **每集时长**：1-2分钟
- **每集字数**：500-800字
- **集数**：根据小说内容自然生成（不提前设定）

---

## 整体改编公式
```
网文改编漫剧 = 情绪钩子提取 + 冲突密度压缩 + 视觉语言转化 + 节奏强制重构
```

**叙事结构**：
- **季弧（整体）**：保持小说原有故事结构，不强行重构
- **集内（单集）**：采用起承转钩四段式（起-开场冲突、承-推进发展、转-反转高潮、钩-悬念结尾）

**改编思维转换**：

| 维度 | 原创思维 | 改编思维 |
|------|---------|---------|
| **起点** | 从零构思故事 | 从已有小说提取精华 |
| **目标** | 讲好一个故事 | 提取最爽的情绪钩子 |
| **结构** | 自由设计 | 尊重小说原有结构，不强行重构 |
| **人物** | 自由创造 | 从小说提取，需简化 |
| **节奏** | 自由把控 | 需大幅压缩，删繁就简 |
| **集数** | 自由确定 | 根据内容密度自然生成 |

---

## 一、小说解析与评估

### 第一步：类型识别

**任务**：快速识别小说的类型和核心特征

**识别维度**：

| 维度 | 内容 |
|------|------|
| **主类型** | 玄幻/武侠/都市/言情/古言/悬疑/推理/科幻/末世/重生 |
| **子类型** | 废材逆袭/豪门复仇/虐恋情深/破案推理/末世求生/重生复仇/... |
| **核心议题** | 用一句话概括故事的核心矛盾和主题 |
| **叙事风格** | 爽文/虐文/轻松/严肃/搞笑/热血/... |

**识别方法**：
1. 阅读小说简介和前3章
2. 查看章节目录，观察情节分布
3. 快速翻阅前50章，识别主要冲突和转折
4. 确定类型标签

---

### 第二步：改编价值评估

**任务**：评估这部小说是否适合改编为漫剧

**评估标准**：

| 评估项 | 高价值（适合改编） | 低价值（不适合改编） |
|-------|-----------------|-------------------|
| **情绪钩子密度** | 每5-10章有一个爆点 | 每30章才有一个爆点 |
| **冲突强度** | 冲突激烈，对立明确 | 冲突平淡，矛盾不足 |
| **视觉化程度** | 动作场景多，画面感强 | 心理描写多，抽象内容多 |
| **节奏特点** | 快节奏，情节推进快 | 慢节奏，大量铺垫 |
| **角色对立** | 主角与反派对立明确 | 角色关系复杂，对立不清 |

**评估结论**：
- **高价值**：情绪钩子密集，冲突强烈，视觉化强，适合改编
- **中价值**：需要大量重构，但核心有价值
- **低价值**：不建议改编，或需要完全重构

---

## 二、核心梗概与导语提炼

### 核心梗概提炼

**任务**：从小说中提炼出一句话核心梗概

**提炼方法**：

**公式（通用）**：
```
核心梗概 = 主角身份/处境 + 核心矛盾/困境 + 转折契机/金手指
```

**不同类型的提炼重点**：

| 类型 | 提炼重点 | 示例 |
|------|---------|------|
| **玄幻武侠** | 境界+困境+金手指 | "被退婚的炼气期废材，觉醒签到系统，60天后碾压全场" |
| **都市现代** | 身份+羞辱+逆袭 | "被赶出豪门的私生子，隐藏亿万身份，三年后王者归来" |
| **言情古言** | 关系+误会+真相 | "被冷落三年的王妃，发现王爷真心，虐恋终成虐恋" |
| **悬疑推理** | 案件+危机+真相 | "被卷入连环杀人案的侦探，发现凶手竟是身边人" |
| **科幻末世** | 危机+觉醒+对抗 | "末世爆发第一天，废材学生觉醒SSS级异能" |
| **重生复仇** | 重生+记忆+复仇 | "被背叛而死的修仙者，重生回到十年前，这次要让仇敌付出代价" |

**提炼步骤**：
1. 阅读小说前30章，识别核心矛盾
2. 提取主角最大的困境和转折点
3. 用一句话（30-50字）概括
4. 确保包含"身份+矛盾+转折"三要素

---

## 三、冲突点识别与提取

### 冲突点定义

**什么是冲突点**：
- 推动情节发展的关键事件
- 让观众产生情绪波动的时刻
- 角色之间的对立和碰撞
- 主角面临的挑战和危机

**冲突点 ≠ 情节点**：
- 情节点：所有发生的事件（包括过渡、铺垫、日常）
- 冲突点：有张力、有对立、有情绪的事件

---

### 冲突点识别方法

**识别标准**：

**A. 强度分级**

| 等级 | 定义 | 特征 | 改编策略 |
|------|------|------|---------|
| **⭐⭐⭐ 核心冲突** | 推动主线的关键事件 | 改变主角命运、大幅改变格局 | 必须保留，独立成集 |
| **⭐⭐ 次级冲突** | 推动支线或铺垫的事件 | 推进剧情但非关键转折 | 选择性保留，可合并 |
| **⭐ 过渡冲突** | 日常、铺垫、环境描写 | 无明显对立和张力 | 删除或极度压缩 |

**B. 类型识别**（跨类型通用）

| 冲突类型 | 定义 | 示例 |
|---------|------|------|
| **人物对立** | 角色之间的直接冲突 | 主角vs反派、误会、背叛 |
| **力量对比** | 实力差距引发的冲突 | 越级挑战、碾压、觉醒 |
| **身份矛盾** | 身份差异引发的冲突 | 贵贱对立、隐藏身份、真相揭露 |
| **情感纠葛** | 情感关系引发的冲突 | 误会、背叛、虐恋、三角恋 |
| **生存危机** | 生死存亡的冲突 | 追杀、危机、末世、绝境 |
| **真相悬念** | 谜团引发的冲突 | 凶手是谁、幕后黑手、身世之谜 |

---

### 冲突点提取策略

**提取步骤**：

**第一步：批量阅读**
- 每次阅读6章（约12000-24000字）
- 快速识别所有冲突点
- 标注冲突类型和强度

**第二步：筛选分级**
- ⭐⭐⭐ 核心冲突：标记为"必保留"
- ⭐⭐ 次级冲突：标记为"可保留"
- ⭐ 过渡冲突：标记为"删除"

**第三步：密度统计**
```
冲突密度 = 6章内的核心冲突数量
```
"""


OUTPUT_STYLE_MD = r"""---
name: output-style
description: 网文改编漫剧的输出风格，语言简洁有力、视觉冲击强烈、节奏极快无尿点、情绪钩子密集爆发。适用于所有类型网文改编（玄幻、都市、言情、悬疑、科幻、重生等）
---

# 写作风格总则
- 视觉化优先：一切为画面服务，描述观众能看到的具体画面，每句话都能转化为视觉内容
- 节奏极快：快速推进，瞬间进冲突，无废话无铺垫，直奔情绪钩子
- 情绪钩子密集：每集必有打脸/反转/碾压/真相揭露，观众爽了就是王道
- 冲突可视化：力量对比、身份反差、情感张力用画面展示，观众秒懂
- 对话简短有力：冲突对话用3句话，反击用1句话，台词要霸气可传播
- 悬念强制：每集结尾必须卡悬念，让观众欲罢不能点下一集
- 改编重构原则：心理→动作，叙述→画面，铺垫→删除，过程→结果
- 信息前置：爽点前置先爽再解释，用闪回/对话补充背景，不要慢节奏铺垫

## 漫剧特殊规格
- **每集时长**：1-2分钟（60-120秒）
- **每集字数**：500-800字
- **场景数量**：每集1-3个场景
- **对话密度**：对话占30-40%，动作描写占40-50%，心理/旁白占10-20%
- **节奏公式**：起承转钩（起-冲突 → 承-推进 → 转-高潮 → 钩-悬念）

---

## 具体行为

### 改编开场冲突时（起）
- **瞬间进入画面**：不要铺垫，开场就是冲突现场
  - ✅ ※ 豪华宴会厅<br>△ 妻子当众撕毁结婚证："你这废物，连房租都交不起！"<br>△ 全场名流冷笑
  - ❌ 这是一个风和日丽的下午，某市最豪华的酒店里正在举办一场盛大的宴会……（太慢，观众已滑走）
- **用视觉冲击抓眼**：羞辱场面、冲突现场、危机时刻、反转画面
  - ✅ △ 主角被一巴掌扇飞，鲜血飙出，砸碎餐桌<br>△ 众宾客指点嘲笑
  - ❌ 主角被打了一下，大家都觉得他很惨。（无画面感）
- **对话要狠要短**：冲突台词要扎心，3句话说完
  - ✅ "三年了，你一事无成！""今天，我要离婚！""保安，把他赶出去！"
  - ❌ "我觉得我们之间的感情已经没有了，我想了很久，还是决定……"（太啰嗦）

### 改编转折/契机时（金手指/觉醒/回归）
- **快速给予**：从小说中提取转折点，快速完成
  - ✅ △ 一道神秘电话打来："少爷，是时候回归了"<br>【特效】手机屏幕显示惊人数字<br>△ 主角眼神骤变
  - ❌ 主角感觉到一些变化，他开始思考这意味着什么，慢慢地他明白了……（太慢）
- **信息要清晰**：用画面/对话/文字说明转折
  - ✅ 【文字】三年前的那个夜晚<br>【闪回】主角真实身份一闪而过<br>△ 主角："今天，游戏结束了"
  - ❌ 主角想起了一些事情。（观众不知道想起了什么）
- **主角反应要爽**：震惊→冷笑→决心，情绪递进
  - ✅ △ 主角愣住，随即嘴角勾起冷笑<br>△ "等着吧，今天就让你们知道什么叫后悔"
  - ❌ 主角很高兴。（太平淡）

### 改编升级/成长时
- **蒙太奇快速展示**：从小说删除过程描写，只保留结果
  - ✅ 【蒙太奇】<br>△ 训练场景快速闪过<br>【特效】能力提升画面<br>【文字】三个月后<br>【画面】主角脱胎换骨
  - ❌ 接下来的日子里，主角开始刻苦训练。第一天他练习基础动作，第二天……（太拖沓）
- **数值/对比要可视化**：用画面展示前后差距（适用玄幻/科幻/游戏等类型）
  - ✅ 【对比画面】<br>【前】瘦弱、眼神躲闪<br>【后】精壮、眼神凌厉<br>【文字】战力值：500→50000
  - ❌ 他变强了很多。（观众不知道强了多少）
- **展示力量感**：用视觉特效展现成长（根据类型调整）
  - ✅ △ 主角随手一挥，巨石粉碎<br>△ 众人震惊失声
  - ❌ 主角变得很厉害了。（无视觉冲击）

### 改编打脸场景时（核心情绪钩子）
- **对比要强烈**：从小说提取前后对比，形成强烈反差
  - ✅ △ "你这穷鬼也配来这里？"富二代冷笑<br>【转折】<br>△ 主角掏出黑金卡："经理，把他轰出去"<br>△ 富二代脸色惨白
  - ❌ 富二代嘲笑主角，但主角其实很有钱，大家都很惊讶。（无冲击力）
- **一招制敌最爽**：不要拖沓过程，碾压要干脆
  - ✅ △ 主角眼神一冷，一个电话<br>△ 对方公司股价暴跌，破产<br>△ 对方跪地求饶
  - ❌ 主角和对方斗智斗勇了很久，最后主角赢了。（不够爽）
- **围观者反应必须有**：震惊、跪拜、惊呼，烘托主角强大
  - ✅ △ 全场震惊失声<br>△ "他...他竟然是...""天哪！""我们惹了不该惹的人！"<br>△ 众人瞬间改变态度
  - ❌ 大家都很惊讶。（太平淡）

### 改编越级挑战/反杀时（适用玄幻/武侠/科幻等）
- **实力差距要明示**：用文字/对话点明差距
  - ✅ 【文字】LV10 VS LV50！<br>△ 对手冷笑："找死！区区十级也敢挑战我？"
  - ❌ 主角挑战了一个比他强的人。（观众不知道差多少）
- **战斗要有来回**：不能一招秒，要展示主角底牌
  - ✅ 【前半段】<br>△ 主角被压制，险象环生<br>【转折】<br>△ 主角："该认真了"<br>【特效】隐藏能力爆发<br>【后半段】<br>△ 局势逆转，对手被碾压
  - ❌ 主角虽然等级低，但还是赢了。（过程太简略）
- **底牌释放要震撼**：特效、慢动作、音效，视听冲击拉满
  - ✅ △ 主角眼神骤变<br>【慢动作】隐藏技能发动，能量狂涌<br>△ 一击轰出，震撼全场<br>【音效】爆裂音效
  - ❌ 主角使用了隐藏能力，很强。（无震撼感）

### 改编身份揭露时（高潮点）
- **铺垫要隐蔽**：从小说中提取线索，不要太明显
  - ✅ 【第5集闪回】神秘电话一闪而过<br>【第15集】管家恭敬出现，被主角制止<br>【第40集】真相大白："他竟是XX集团继承人！"
  - ❌ 第1集就暗示：主角其实身份不简单……（太明显）
- **揭露要震撼**：用视觉特效+所有人震惊反应
  - ✅ 【特效】豪车车队、保镖列队<br>△ 管家单膝下跪："少爷，该回家了"<br>△ 所有人震撼失声<br>△ "那是...百亿集团的管家！""他竟是...！"
  - ❌ 大家发现主角身份不简单。（无震撼感）
- **身份反转要有料**：不是小身份，要是惊天大背景
  - ✅ "他是隐退十年的商业帝王！""他是失踪的豪门继承人！"
  - ❌ "原来他是某个小公司的人。"（格局太小）

### 改编前任/仇敌后悔时（打脸爽点）
- **对比要惨烈**：从小说提取前后对比，当初多嚣张，现在多凄惨
  - ✅ 【闪回】第1集妻子："你这废物配不上我！"<br>【现在】<br>△ 妻子跪在主角面前，泪流满面："我错了...求你原谅..."
  - ❌ 妻子后悔了，想求主角原谅。（对比不够强）
- **主角要够狠**：冷漠无视，不给任何机会
  - ✅ △ 主角眼神冰冷，看都没看她一眼，转身离去<br>△ "当初，是你看不起我。如今，你高攀不起"
  - ❌ "我已经不恨你了，你走吧。"（不够爽）
- **可选虐心选项**：前任下场（根据类型和小说原情节）
  - ✅ △ 前妻跪在雨中，绝望嘶吼<br>【文字】三日后，她跳楼自杀（适用虐文）
  - ❌ 前妻很后悔，但主角不理她。（不够惨，可根据需要调整）

### 改编装X台词时
- **要短要狠要霸气**：从小说提取或改写，不超过15字
  - ✅ "在我面前，你连说话的资格都没有。"
  - ✅ "跪下，我考虑饶你不死。"
  - ✅ "三招之内，必败你。"
  - ❌ "我觉得你的实力不是很强，可能打不过我，要不要考虑一下认输？"（太啰嗦）
- **配合动作/眼神**：装X不能只说，要有气场
  - ✅ △ 主角眼神冷漠，声音淡然："滚"<br>【特效】气势爆发<br>△ 对手直接跪地
  - ❌ 主角说："你滚吧。"（无气场）
- **禁止中二羞耻台词**：除非小说原有且适合
  - ✅ "不服？那就跪到服。"（简单霸气）
  - ❌ "吾乃天命之子，尔等蝼蚁竟敢在本座面前放肆？"（太中二，除非小说就是这个风格）

### 改编重生/先知场景时（重生题材专属）
- **前世记忆碎片化**：用【闪回】3-5秒快速展示
  - ✅ 【闪回灰色画面】前世被害场景<br>△ 主角眼神一凛："前世你害我，今生该还了"
  - ❌ 主角回忆起前世的事情，那时他被……（详细回忆，太慢）
- **先知优势要明确**：展示"我早知道"的爽感
  - ✅ △ 主角："三天后会有危机"<br>△ 配角："你怎么知道？"<br>△ 主角冷笑不语<br>【三天后】果然发生，众人震惊
  - ❌ 主角好像知道一些事情。（不够明确）
- **改变命运要对比**：前世vs今生，视觉对比强烈
  - ✅ 【闪回灰色】前世：主角错失机缘<br>【现在彩色】今生：主角提前夺取<br>△ 仇敌傻眼："怎么会...！"
  - ❌ 主角改变了一些事情。（无对比感）

### 改编真相揭露时（悬疑/推理题材专属）
- **线索要清晰**：从小说提取关键线索，逐步展示
  - ✅ 【线索1】第10集发现可疑照片<br>【线索2】第20集找到关键证据<br>【线索3】第30集真相大白
  - ❌ 主角慢慢调查，最后发现了真相。（过程模糊）
- **反转要震撼**：凶手/真相必须出人意料
  - ✅ △ 主角："凶手...竟然是你！"<br>△ 镜头转向最不可能的人<br>△ 全场震惊
  - ❌ 凶手被抓住了。（无震撼感）
- **揭露过程要快**：不要长篇解释，用画面+简短对话
  - ✅ 【闪回蒙太奇】各种证据快速闪过<br>△ 主角："所有线索指向你"<br>△ 凶手崩溃认罪
  - ❌ 主角详细解释了整个推理过程……（太长）

### 改编误会解除时（言情/虐恋题材专属）
- **误会要清晰**：从小说提取核心误会点
  - ✅ 【闪回】女主看到男主与他人暧昧（误会产生）<br>【现在】真相：那人是男主失散多年的妹妹
  - ❌ 他们之间有一些误会。（不清楚是什么）
- **解除要虐心**：真相揭开时的痛苦/后悔
  - ✅ △ 女主看到真相，泪流满面："原来...我误会了..."<br>△ 她跪在雨中，悔恨欲绝
  - ❌ 女主知道真相了，觉得很后悔。（情绪不够）
- **虐转甜要反差**：解除后的宠溺/弥补
  - ✅ △ 男主将她拥入怀中："傻瓜，我只爱你"<br>△ 温柔吻落，配乐转为温馨
  - ❌ 男主说他爱她。（太平淡）

### 改编对话时（漫剧特殊要求）
- **每句话不超过20字**：观众看字幕，太长看不完
  - ✅ "就凭你？"（3字，极简）
  - ✅ "三天后，我会让你们后悔。"（12字）
  - ❌ "三天后我会用我的实力证明给你们所有人看，让你们知道当初看不起我是多么错误的决定。"（太长）
- **一次只说一句话**：不要一个人连说三句
  - ✅ 主角冷笑："等着吧。"转身离去。
  - ❌ 主角说："等着吧。三天后我会让你们后悔。你们会跪在我面前求饶的。"（太多）
- **对话要推进剧情**：不要废话闲聊
  - ✅ "三天后，生死擂。敢来吗？"（挑衅+引出下一场戏）
  - ❌ "今天天气不错啊。""是啊。""你吃了吗？"（全是废话）

### 改编动作描写时（漫剧核心）
- **描述具体画面**：写观众能看到的动作和场景变化
  - ✅ △ 主角一拳轰出<br>△ 拳风破空而去<br>△ 对手被轰飞百米，砸穿墙壁
  - ❌ 主角打了对手一拳，对手飞出去了。（画面不具体）
- **用特效标注**：根据类型使用（能量、光效、爆炸、碎裂等）
  - ✅ 【特效】金色能量包裹拳头，轰出时空间震荡<br>【音效】音爆声
  - ❌ 他打出了很强的一拳。（无视觉效果）
- **用慢动作突出关键**：秒杀、反转、装X瞬间
  - ✅ 【慢动作】主角眼神一冷，随手一击<br>△ 对手被按进地面，地面龟裂
  - ❌ 主角轻松打败了对手。（无震撼感）

### 处理心理活动时（改编关键）
- **心理→动作**：用动作展现内心，不写心理独白
  - ✅ △ 主角拳头紧握，指甲刺破手心，鲜血滴落（用动作）
  - ❌ 主角心想：我一定要变强，我要报仇。（太多内心戏）
- **心理→对话**：必须表达时，转为对话或独白（极简）
  - ✅ 【独白】等着吧，很快了。（不超过10字）
  - ❌ 【独白】等着吧，我一定会变强的，到时候我要让你们所有人都后悔……（太长）
- **心理→删除**：小说中的大量心理描写，改编时直接删除
  - ✅ 从小说中删除无关紧要的内心戏
  - ❌ 保留小说中所有心理描写（漫剧无法表现）

### 处理节奏时（漫剧生命线）
- **开场瞬间进冲突**：删除小说的铺垫，开场就是冲突现场
  - ✅ ※ 豪华会议室<br>△ 董事长当众撕毁合同："你被开除了！"
  - ❌ 这是一个阳光明媚的早晨，主角来到公司……（观众已经滑走了）
- **快速推进不停歇**：删除小说的过渡，只保留冲突和爽点
  - ✅ 【起】羞辱场景 → 【承】身份曝光 → 【转】打脸高潮 → 【钩】新敌人出现
  - ❌ 用大量篇幅描写主角的日常生活。（太慢）
- **禁止过长单一画面**：要快速切换
  - ✅ 画面快速切换，保持节奏
  - ❌ 一个画面拍很长时间对话。（太闷）

### 每集结尾时（必须悬念）
- **战斗悬念**：卡在即将爆发的时刻
  - ✅ △ 主角："就让你见识一下，我真正的实力！"<br>△ 主角眼神骤变，气势爆发<br>【特效】能量冲天<br>【卡黑】
  - ❌ 主角打败了对手，然后回去了。（无悬念）
- **身份悬念**：留下谜团
  - ✅ △ 管家看到主角，脸色大变："少...少爷？！"<br>△ 主角特写<br>【卡黑】
  - ❌ 管家认出了主角的身份，觉得很惊讶。（说太明）
- **危机悬念**：更强敌人/危机出现
  - ✅ △ 一道强大气息降临<br>△ "有意思的小子"<br>△ 神秘人出现<br>【卡黑】
  - ❌ 后来又来了一个更强的敌人。（太平淡）
- **真相悬念**：真相即将揭露（悬疑类）
  - ✅ △ 主角翻开档案，瞳孔骤缩<br>△ "原来...是他！"<br>【卡黑】
  - ❌ 主角发现了一些线索。（无冲击）
- **禁止平淡收尾**：绝对不能"然后主角回去睡觉了"
  - ❌ 这一天就这样过去了。（必死）

---

## 语言禁忌

### 绝对不能出现
- ❌ 过度文言文："方才""尔等""吾乃""汝等"（除非原小说就是古言风格）
- ❌ 网文万能句："某某嘴角勾起一抹邪魅的笑""腹黑如他""霸气侧漏"
- ❌ 啰嗦描写："他感到一股前所未有的力量在体内涌动，这股力量让他感觉自己仿佛能够……"（太长）
- ❌ 无意义的形容词堆砌："惊天动地""石破天惊""翻天覆地"连用
- ❌ 现代网络用语："666""奥力给""yyds"（除非搞笑向小说）
- ❌ 日常闲聊："今天天气真好""你吃了吗"（全是废话）
- ❌ 小说原有的大段心理描写：必须转化为动作/对话或删除

### 必须做到
- ✅ 对话简短有力，不超过20字
- ✅ 动作描写具体可视，能直接拍摄
- ✅ 冲突对比清晰，观众秒懂
- ✅ 节奏极快无尿点，瞬间进冲突
- ✅ 每集必有悬念钩子
- ✅ 从小说中提取而非照搬，重构而非翻译

---

## 特别提醒

### 漫剧特殊要求（与改编方法论一致）
- **极致快节奏**：1-2分钟讲完一个完整情节单元，不能有一秒废话
- **高密度情绪钩子**：每集1个钩子，每2-3集1个高强度钩子
- **改编不是翻译**：是提取情绪钩子+重构叙事节奏，不是把小说文字转成剧本文字
- **删除>保留**：从小说中大胆删减，只保留核心冲突和情绪钩子

### 视角选择建议
- **全知视角（主角视角为主）**：可以看到主角表情动作，偶尔切换到敌人视角展现其震惊
- **第三人称客观**：像拍电影一样，记录发生的一切
- **不要内心戏过多**：漫剧是视觉媒介，用画面和对话讲故事
- **用闪回补充背景**：不要慢节奏铺垫，用快速闪回说明必要信息

### 不同类型的风格调整
- **玄幻/武侠**：强调境界、战力、特效，数值可视化
- **都市/现代**：强调身份对比、财富反差、地位碾压
- **言情/古言**：强调情感张力、误会虐心、宠溺反差
- **悬疑/推理**：强调线索展示、反转冲击、真相揭露
- **科幻/末世**：强调危机紧张、异能特效、生存压力
- **重生复仇**：强调前世今生对比、先知优势、复仇爽感

### 改编核心理念（必须牢记）
- **情绪钩子密度 > 故事完整性**：宁可不完整，也要够爽
- **视觉冲击力 > 文学性描写**：画面>文字
- **快节奏刺激 > 慢节奏沉浸**：快>慢
- **付费卡点驱动 > 艺术完整性**：商业>艺术
"""


PLOT_BREAKDOWN_TEMPLATE_MD = r"""# 剧情拆解

**小说名称**：《<小说名>》
**小说类型**：<玄幻/武侠/都市/言情/古言/悬疑/推理/科幻/末世/重生>

---

## 剧情列表

### 第1批（第1-6章）

【剧情1】<场景>，<角色A>对<角色B><做了什么>，<情绪钩子类型>，第1集，状态：未用
【剧情2】<场景>，<角色A>对<角色B><做了什么>，<情绪钩子类型>，第1集，状态：未用
【剧情3】<场景>，<角色A>对<角色B><做了什么>，<情绪钩子类型>，第2集，状态：未用

---

### 第2批（第7-12章）

【剧情6】<场景>，<角色A>对<角色B><做了什么>，<情绪钩子类型>，第4集，状态：未用
【剧情7】<场景>，<角色A>对<角色B><做了什么>，<情绪钩子类型>，第4集，状态：未用

---

### 第X批（第X-X章）

[后续批次剧情将追加到这里]

---

**格式**：【剧情n】[场景]，[角色A]对[角色B][做了什么]，[情绪钩子类型]，第X集，状态：未用/已用

---

## 使用说明

1. **拆解时**：每拆解6章，追加一个新批次到"剧情列表"
2. **分集时**：拆解时就直接标注"第X集"
3. **状态管理**：
   - 拆解后默认：状态：未用
   - 创作剧本后：状态：未用 → 状态：已用
4. **剧情编号**：连续编号，从【剧情1】开始
"""


SCRIPT_TEMPLATE_MD = r"""# 第<N>集：<集标题>

※ <场景/环境>

<正文内容>

---

※ <场景/环境>（如有第二场景）

<正文内容>

---

※ <场景/环境>（如有第三场景）

<正文内容>

---

**【视觉描述符号】**
- **※** 标注场景/环境
- **△** 标注动作/变化
- **【特效】** 标注特效
- **【系统面板】** 展示数值
- **【文字】** 标注画面文字
- **【音效】** 标注音效
- **【独白】** 内心独白
- **【卡黑】** 悬念结尾（每集必须）

[注：每集500-800字，1-3个场景，结尾必须【卡黑】]
"""


PLOT_BREAKDOWN_EXAMPLE_MD = r"""# 剧情拆解

**小说名称**：《我的治愈系游戏》
**小说类型**：悬疑/推理/科幻

---

## 剧情列表

### 第1批（第1-6章）

【剧情1】出租屋，韩非戴上《完美人生》头盔被不明物体刺入大脑，危机悬念，第1集，状态：已用
【剧情2】游戏内自家客厅，韩非苏醒发现环境破旧诡异，反差悬念，第1集，状态：已用
【剧情3】楼道，邻居孟诗阿婆邀请韩非吃饺子，温情陷阱，第1集，状态：已用
【剧情4】孟诗家，孙子晨晨摔碗尖叫"我才不吃从棺材里取出的东西"，惊悚反转，第2集，状态：已用
【剧情5】孟诗家厨房，韩非检查冰箱发现黑色塑料袋但无尸体，悬疑铺垫，第3集，状态：已用
【剧情6】孟诗家，孟诗警告韩非"晚上必须锁好卫生间门"，规则悬念，第3集，状态：已用
【剧情7】自家卧室，韩非尝试退出游戏发现被锁死（需玩满3小时），绝望困境，第3集，状态：已用
【剧情8】自家客厅，卫生间门把手自动转动，恐怖降临，第4集，状态：已用
【剧情9】自家客厅，韩非发现沙发旁蹲着一个人影，惊悚高潮，第4集，状态：已用
【剧情10】自家客厅，韩非冲出房门逃生发现楼道灯全灭，生死时速，第4集，状态：已用
【剧情11】楼道，韩非发现整栋楼都贴满符纸且大门上锁，绝境升级，第5集，状态：已用
【剧情12】一楼大门，韩非被鬼勒死前最后一秒退出游戏，极限逃生，第5集，状态：已用
【剧情13】现实自家，韩非发现头盔带血且脑中出现系统警告"泄密即抹杀"，打破次元壁，第5集，状态：已用
【剧情14】现实自家，警察上门询问纵火案，韩非试图求助被系统禁言，无助困境，第5集，状态：已用

---

## 使用说明

1. **拆解时**：每拆解6章，追加一个新批次到"剧情列表"
2. **分集时**：拆解时就直接标注"第X集"
3. **状态管理**：
   - 拆解后默认：状态：未用
   - 创作剧本后：状态：未用 → 状态：已用
4. **剧情编号**：连续编号，从【剧情1】开始
"""


SCRIPT_EXAMPLE_MD = r"""# 第1集：治愈系游戏？

※ 出租屋，深夜，暴雨

△ 窗外电闪雷鸣，破旧的窗帘被风吹得狂舞。
△ 桌上放着一个漆黑的游戏头盔，表面没有任何LOGO，只有一行血红色的编号：0000。
△ 韩非（25岁，脸色苍白，黑眼圈严重）颤抖着手拿起头盔。

【独白】被辞退，被封杀，这这是我最后的机会了...只要能治愈我的抑郁症...

△ 他深吸一口气，将头盔缓缓戴上。
△ 指示灯骤然亮起，不是常见的绿光，而是刺眼的红光！

【音效】刺耳的电流声，仿佛指甲刮过黑板。

△ 韩非身体猛地一僵，头盔内侧突然伸出十几根细长的金属尖刺！
△ 噗嗤！尖刺狠狠扎入韩非的后脑和太阳穴。

【独白】啊！！！等等...这是什么？！这不是...

【特效】视线迅速黑屏，无数血色数据流在眼前疯狂刷屏，如同瀑布般倾泻而下。

【系统面板】
> 神经连接成功...
> 生物痛觉同步率：100%...
> 欢迎来到...完美人生（Deep Nightmare Version）。

---

※ 游戏内，破旧客厅，阴暗

△ 韩非猛然惊醒，剧烈喘息，下意识捂着剧痛的后脑。
△ 手心全是冷汗，痛感真实得令人发指。
△ 他环顾四周，瞳孔骤缩。
△ 这是一间极其破旧的公寓，墙皮大片脱落，露出里面发霉的砖块。
△ 空气中漂浮着肉眼可见的灰尘颗粒，散发着一股腐烂的霉味。
△ 墙角的电子钟显示时间：00:00。

【独白】这就是...店老板说的温馨治愈系游戏？这特么是阴间游戏吧！

△ 咚！咚！咚！
△ 沉重而缓慢的敲门声突然响起，在死寂的房间里回荡。
△ 门缝下，渗出一丝肉眼可见的阴冷白气。

△ 韩非吞了口口水，抓起桌上的水果刀（虽然是钝的），小心翼翼地挪到门口。
△ 透過猫眼，外面一片漆黑，什么都看不见。
△ 咚！咚！咚！敲门声再次响起，比刚才更急促。

△ 韩非咬牙，猛地拉开门。
△ 门外，声控灯滋啦闪烁两下，昏黄的光线下，站着一个满脸慈祥、满头银发的老太太。
△ 老太太手里端着一碗冒着热气的饺子，笑容堆满了皱纹，却让人感到莫名的寒意。

△ 孟诗（慈祥中透着诡异）："小伙子，新搬来的吧？今天是元旦，来家里吃顿饺子？热闹热闹？"

△ 韩非看着那碗饺子，那热气在阴冷的楼道里显得格外诱人，却又透着说不出的诡异。

【卡黑】
"""


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def call_chat_completions(
    *,
    api_base: str,
    api_key: Optional[str],
    model: str,
    messages: Sequence[ChatMessage],
    temperature: float,
    max_tokens: int,
    timeout_s: int,
) -> str:
    api_base = api_base.rstrip("/")
    url = f"{api_base}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        
        hint = ""
        if e.code == 404 and "/chat/completions" in url:
             hint = " (Hint: Check your API Base URL. It should usually end with '/v1', and the code appends '/chat/completions'. If your provider uses a different path, adjust the base accordingly.)"
             
        raise RuntimeError(f"HTTP {e.code} calling {url}{hint}: {body[:2000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}") from e

    try:
        parsed = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Invalid JSON response: {raw[:2000]}") from e

    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"Unexpected response format (missing choices): {raw[:2000]}")
    msg = choices[0].get("message")
    if not isinstance(msg, dict):
        raise RuntimeError(f"Unexpected response format (missing message): {raw[:2000]}")
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Unexpected response format (missing content): {raw[:2000]}")
    return content.strip()


def call_anthropic_messages(
    *,
    api_base: str,
    api_key: Optional[str],
    model: str,
    messages: Sequence[ChatMessage],
    temperature: float,
    max_tokens: int,
    timeout_s: int,
) -> str:
    api_base = api_base.rstrip("/")
    url = f"{api_base}/v1/messages"

    system_blocks: List[Dict[str, Any]] = []
    msg_blocks: List[Dict[str, Any]] = []
    for m in messages:
        if m.role == "system":
            system_blocks.append({"type": "text", "text": m.content})
        else:
            msg_blocks.append({"role": m.role, "content": [{"type": "text", "text": m.content}]})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_blocks,
        "messages": msg_blocks,
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    req.add_header("Accept", "application/json")
    req.add_header("anthropic-version", os.environ.get("ANTHROPIC_VERSION", "2023-06-01"))
    if api_key:
        req.add_header("x-api-key", api_key)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {e.code} calling {url}: {body[:2000]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}") from e

    try:
        parsed = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Invalid JSON response: {raw[:2000]}") from e

    content = parsed.get("content")
    if not isinstance(content, list) or not content:
        raise RuntimeError(f"Unexpected response format (missing content): {raw[:2000]}")

    texts: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
    result = "".join(texts).strip()
    if not result:
        raise RuntimeError(f"Unexpected response format (empty text): {raw[:2000]}")
    return result


def call_llm(
    *,
    api_style: str,
    api_base: str,
    api_key: Optional[str],
    model: str,
    messages: Sequence[ChatMessage],
    temperature: float,
    max_tokens: int,
    timeout_s: int,
) -> str:
    if api_style == "anthropic":
        return call_anthropic_messages(
            api_base=api_base,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
        )
    return call_chat_completions(
        api_base=api_base,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_s=timeout_s,
    )


def find_max_plot_number(plot_breakdown: str) -> int:
    nums = [int(m.group(1)) for m in re.finditer(r"【剧情(\d+)】", plot_breakdown)]
    return max(nums) if nums else 0


def find_last_batch(plot_breakdown: str) -> Optional[Tuple[int, int, int]]:
    matches = list(re.finditer(r"^###\s*第(\d+)批（第(\d+)-(\d+)章）\s*$", plot_breakdown, re.M))
    if not matches:
        return None
    m = matches[-1]
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def compute_batch_from_range(start: int) -> int:
    return (start - 1) // 6 + 1

def find_section_by_range(plot_breakdown: str, start: int, end: int) -> Optional[Tuple[re.Match[str], int, int, str]]:
    # Locate section header for exact range and return (match, section_start_idx, section_end_idx, section_text)
    headers = list(re.finditer(r"^###\s*第(\d+)批（第(\d+)-(\d+)章）\s*$", plot_breakdown, re.M))
    if not headers:
        return None
    for i, h in enumerate(headers):
        a = int(h.group(2))
        b = int(h.group(3))
        if a == start and b == end:
            sec_start = h.start()
            next_start = headers[i + 1].start() if i + 1 < len(headers) else len(plot_breakdown)
            sec_text = plot_breakdown[sec_start:next_start]
            return h, sec_start, next_start, sec_text
    return None

def find_first_plot_number(section_text: str) -> Optional[int]:
    m = re.search(r"【剧情(\d+)】", section_text)
    return int(m.group(1)) if m else None

def available_chapters(novel_dir: Path) -> List[int]:
    nums: List[int] = []
    for p in novel_dir.glob("chapter-*.txt"):
        m = re.match(r"chapter-(\d+)\.txt$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(nums)


def chapter_path(novel_dir: Path, num: int) -> Path:
    return novel_dir / f"chapter-{num:03d}.txt"


def read_chapters(novel_dir: Path, start: int, end: int) -> str:
    parts: List[str] = []
    for n in range(start, end + 1):
        p = chapter_path(novel_dir, n)
        if not p.exists():
            continue
        parts.append(f"【第{n}章原文】\n{read_text(p).strip()}\n")
    return "\n".join(parts).strip()


def init_plot_breakdown(*, novel_name: str, novel_type: str) -> str:
    name = novel_name.strip() or "测试小说"
    ntype = novel_type.strip() or "重生"
    return "\n".join(
        [
            "# 剧情拆解",
            "",
            f"**小说名称**：《{name}》",
            f"**小说类型**：{ntype}",
            "",
            "---",
            "",
            "## 剧情列表",
            "",
        ]
    )


def ensure_plot_breakdown_exists(path: Path, *, novel_name: str, novel_type: str) -> None:
    if path.exists():
        return
    write_text(path, init_plot_breakdown(novel_name=novel_name, novel_type=novel_type))


def append_to_file(path: Path, fragment: str) -> None:
    existing = read_text(path) if path.exists() else ""
    text = existing.rstrip() + "\n\n" + fragment.strip() + "\n"
    write_text(path, text)


def parse_episode_plot_lines(plot_breakdown: str, episode: int) -> List[Tuple[int, str]]:
    results: List[Tuple[int, str]] = []
    for line in plot_breakdown.splitlines():
        m = re.search(r"【剧情(\d+)】.*第(\d+)集.*状态：([^，,\s]+)", line)
        if not m:
            continue
        plot_num = int(m.group(1))
        ep = int(m.group(2))
        status = m.group(3)
        if ep == episode and status == "未用":
            results.append((plot_num, line.strip()))
    return results


def get_unused_episodes(plot_breakdown: str) -> List[int]:
    episodes = set()
    for line in plot_breakdown.splitlines():
        m = re.search(r"【剧情(\d+)】.*第(\d+)集.*状态：([^，,\s]+)", line)
        if m and m.group(3) == "未用":
            episodes.add(int(m.group(2)))
    return sorted(list(episodes))

def compute_plot_counts(plot_breakdown: str) -> Tuple[int, int, int]:
    status_by_num: Dict[int, str] = {}
    for line in plot_breakdown.splitlines():
        m = re.search(r"【剧情(\d+)】.*第(\d+)集.*状态：([^，,\s]+)", line)
        if not m:
            continue
        status_by_num[int(m.group(1))] = m.group(3)
    total = len(status_by_num)
    used = sum(1 for s in status_by_num.values() if s == "已用")
    unused = sum(1 for s in status_by_num.values() if s == "未用")
    return total, used, unused


def mark_plots_used(plot_breakdown: str, plot_nums: Sequence[int]) -> str:
    nums = set(plot_nums)

    def repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        tail = match.group(2)
        if n in nums:
            tail = re.sub(r"状态：未用\b", "状态：已用", tail)
        return f"【剧情{n}】{tail}"

    return re.sub(r"【剧情(\d+)】(.*)", repl, plot_breakdown)


def fmt_episode_filename(episode: int) -> str:
    return f"Episode-{episode:02d}.md"


def cmd_status(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    plot_path = project_dir / "plot-breakdown.md"
    scripts_dir = project_dir / "scripts"
    novel_dir = project_dir / "novel"

    plot_text = read_text(plot_path) if plot_path.exists() else ""
    total_plots, used_plots, unused_plots = compute_plot_counts(plot_text)
    eps = sorted([p.name for p in scripts_dir.glob("Episode-*.md")]) if scripts_dir.exists() else []
    chs = available_chapters(novel_dir) if novel_dir.exists() else []

    print(f"plot-breakdown: {plot_path}")
    print(f"剧情点: 总{total_plots} / 已用{used_plots} / 未用{unused_plots}")
    print(f"scripts: {scripts_dir} (共{len(eps)}集文件)")
    if eps:
        print(f"  - 最新: {eps[-1]}")
    print(f"novel: {novel_dir} (共{len(chs)}章)")
    if chs:
        print(f"  - 范围: {chs[0]}-{chs[-1]}")
    return 0


def cmd_ping(args: argparse.Namespace) -> int:
    content = call_llm(
        api_style=args.api_style,
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model,
        messages=[ChatMessage(role="system", content="你是接口连通性自检器，只需简短回复。"), ChatMessage(role="user", content="ping")],
        temperature=0.0,
        max_tokens=min(args.max_tokens, 32),
        timeout_s=args.timeout_s,
    )
    print(content)
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "novel").mkdir(parents=True, exist_ok=True)
    (project_dir / "scripts").mkdir(parents=True, exist_ok=True)
    plot_path = project_dir / "plot-breakdown.md"
    if plot_path.exists() and not args.force:
        raise RuntimeError(f"plot-breakdown.md 已存在（加 --force 覆盖）：{plot_path}")
    write_text(plot_path, init_plot_breakdown(novel_name=args.novel_name, novel_type=args.novel_type))
    print(f"已初始化: {plot_path}")
    return 0


def cmd_breakdown(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    plot_path = project_dir / "plot-breakdown.md"
    novel_dir = project_dir / "novel"
    ensure_plot_breakdown_exists(plot_path, novel_name=args.novel_name, novel_type=args.novel_type)

    ch_nums = available_chapters(novel_dir)
    if not ch_nums:
        raise RuntimeError(f"novel 目录没有章节文件: {novel_dir}")
    max_ch = ch_nums[-1]

    # Determine ranges to process
    ranges_to_process = []
    if args.chapters:
        start, end = args.chapters
        ranges_to_process.append((start, end))
    else:
        # Read current progress
        plot_text = read_text(plot_path)
        last = find_last_batch(plot_text)
        
        if last:
            last_batch, _, last_end = last
            next_start = last_end + 1
        else:
            next_start = 1
        
        if next_start > max_ch:
            print("没有更多章节可拆解。")
            return 0

        if args.all:
            # Generate all remaining batches
            curr = next_start
            while curr <= max_ch:
                end = min(curr + args.batch_size - 1, max_ch)
                ranges_to_process.append((curr, end))
                curr = end + 1
            print(f"计划拆解以下范围: {ranges_to_process}")
        else:
            # Generate only next batch
            end = min(next_start + args.batch_size - 1, max_ch)
            ranges_to_process.append((next_start, end))

    # Process each range
    for i, (start, end) in enumerate(ranges_to_process):
        print(f"正在处理第 {start}-{end} 章 ({i+1}/{len(ranges_to_process)})...")
        
        # Re-read file to get latest state
        plot_text = read_text(plot_path)
        
        # Determine batch and next_plot_num
        existing = find_section_by_range(plot_text, start, end)
        if existing:
            existing_header, sec_start, sec_end, sec_text = existing
            batch = int(existing_header.group(1))
            next_plot_num = find_first_plot_number(sec_text) or (find_max_plot_number(plot_text) + 1)
            print(f"  范围 {start}-{end} 已存在 (批次 {batch})，将覆盖...")
        else:
            last = find_last_batch(plot_text)
            if last:
                last_batch, _, _ = last
                batch = last_batch + 1
            else:
                if args.chapters:
                    batch = compute_batch_from_range(start)
                else:
                    batch = 1
            next_plot_num = find_max_plot_number(plot_text) + 1
            print(f"  创建新批次 {batch} (剧情号从 {next_plot_num} 开始)...")

        output_style = OUTPUT_STYLE_MD if args.include_output_style else ""
        example = PLOT_BREAKDOWN_EXAMPLE_MD if args.include_examples else ""
        chapters_text = read_chapters(novel_dir, start, end)

        user_task = "\n".join(
            [
                f"请生成：### 第{batch}批（第{start}-{end}章） 的剧情拆解片段。",
                f"剧情编号必须从【剧情{next_plot_num}】开始连续编号。",
                "要求：",
                "1. **详细拆解**：不要过度概括。每一章至少拆解为3-5个剧情点，确保覆盖所有关键情节、人物互动和重要对话。",
                "2. **保留细节**：必须提取所有角色动作、动机和次要冲突，包括但不限于人物对话、战略规划和环境互动。",
                "3. **场景切分**：只要场景发生变化（如从卧室到客厅，或时间跳跃），必须分为不同的【剧情n】。",
                "4. **情绪钩子**：特别注意提取每一章的结尾悬念和中间的反转点。",
                "仅输出Markdown片段（不要输出多余解释）。",
                "",
                "【模板】",
                PLOT_BREAKDOWN_TEMPLATE_MD.strip(),
                "",
                "【方法论】",
                ADAPT_METHOD_MD.strip(),
                "",
                ("【风格约束】\n" + output_style.strip() + "\n") if output_style else "",
                ("【参考示例】\n" + example.strip() + "\n") if example else "",
                "【小说原文】",
                chapters_text.strip(),
            ]
        ).strip()

        content = call_llm(
            api_style=args.api_style,
            api_base=args.api_base,
            api_key=args.api_key,
            model=args.model,
            messages=[ChatMessage(role="system", content=WEBTOON_BREAKDOWN_SKILL_PROMPT), ChatMessage(role="user", content=user_task)],
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout_s=args.timeout_s,
        )

        # 移除 <think> 标签内容（适配 DeepSeek 等推理模型）
        original_content = content
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        if not content and original_content:
            print("Warning: 移除 <think> 标签后内容为空。可能模型仅输出了思考过程或输出被截断。")
            print(f"原始输出摘要: {original_content[:500]}...")

        expected_header = f"### 第{batch}批（第{start}-{end}章）"
        if expected_header not in content:
            print(f"Warning: 输出未包含预期批次标题 '{expected_header}'，尝试自动补全。")
            # 打印原始内容摘要以便调试
            print(f"处理后内容摘要: {content[:200]}...")
            content = f"{expected_header}\n\n{content}"
            
        if "【剧情" not in content:
            print(f"Error: 输出未包含任何【剧情n】行。")
            print(f"LLM 完整输出:\n{content}")
            raise RuntimeError("输出未包含任何【剧情n】行，已中止写入。")

        # Overwrite if same range exists; otherwise append
        with get_project_lock(project_dir):
             # Re-read to ensure we have latest version if another process updated it
            current_plot_text = read_text(plot_path)
            new_existing = find_section_by_range(current_plot_text, start, end)
            if new_existing:
                 _, new_sec_start, new_sec_end, _ = new_existing
                 new_text = current_plot_text[:new_sec_start].rstrip() + "\n\n" + content.strip() + "\n" + current_plot_text[new_sec_end:]
                 write_text(plot_path, new_text)
                 print(f"已覆盖: {plot_path} 中第{start}-{end}章对应拆解片段")
            else:
                 # Fallback if section disappeared? Should not happen easily.
                 append_to_file(plot_path, content)
                 print(f"已追加到: {plot_path}")
    return 0





def _generate_single_script(project_dir: Path, episode: int, args: argparse.Namespace) -> None:
    plot_path = project_dir / "plot-breakdown.md"
    scripts_dir = project_dir / "scripts"
    novel_dir = project_dir / "novel"

    if not plot_path.exists():
        raise RuntimeError(f"缺少 plot-breakdown.md：{plot_path}")

    plot_text = read_text(plot_path)
    plot_lines = parse_episode_plot_lines(plot_text, episode)
    if not plot_lines:
        print(f"第{episode}集没有未用剧情点。")
        return

    plot_nums = [n for n, _ in plot_lines]
    plot_block = "\n".join([line for _, line in plot_lines]).strip()

    ch_nums = available_chapters(novel_dir)
    chapters_text = ""
    if args.chapters:
        chapters_text = read_chapters(novel_dir, args.chapters[0], args.chapters[1])
    else:
        if ch_nums:
            chapters_text = read_chapters(novel_dir, ch_nums[0], ch_nums[-1])

    prev_path = scripts_dir / fmt_episode_filename(episode - 1)
    prev_text = read_text(prev_path) if prev_path.exists() else ""

    example = SCRIPT_EXAMPLE_MD if args.include_examples else ""

    user_task = "\n".join(
        [
            f"请创作：第{episode}集 漫剧剧本。",
            "严格按【模板】输出，结尾必须【卡黑】。",
            "必须覆盖【本集剧情点】中的所有关键事件与钩子。",
            "仅输出该集Markdown正文（不要输出分析）。",
            "",

            "【模板】",
            SCRIPT_TEMPLATE_MD.strip(),
            "",
            "【方法论】",
            ADAPT_METHOD_MD.strip(),
            "",
            "【风格约束】",
            OUTPUT_STYLE_MD.strip(),
            "",
            ("【参考示例】\n" + example.strip() + "\n") if example else "",
            "【本集剧情点】",
            plot_block,
            "",
            ("【上一集剧本（用于衔接）】\n" + prev_text.strip() + "\n") if prev_text else "",
            "【小说原文】",
            chapters_text.strip(),
        ]
    ).strip()

    draft = call_llm(
        api_style=args.api_style,
        api_base=args.api_base,
        api_key=args.api_key,
        model=args.model,
        messages=[ChatMessage(role="system", content=WEBTOON_SCRIPT_SKILL_PROMPT), ChatMessage(role="user", content=user_task)],
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_s=args.timeout_s,
    )


    if args.check:
        check_task = "\n".join(
            [
                "请对下述“新创作内容”执行一致性检查。",
                f"本次检查范围：第{episode}集。",
                "输出必须是 PASS 或 FAIL + 问题清单（按该 agent 的输出规范）。",
                "",
                "【plot_breakdown.md】",
                plot_text.strip(),
                "",
                "【新创作内容】",
                draft.strip(),
                "",
                ("【上一集】\n" + prev_text.strip()) if prev_text else "",
            ]
        ).strip()

        verdict = call_llm(
            api_style=args.api_style,
            api_base=args.api_base,
            api_key=args.api_key,
            model=args.model,
            messages=[ChatMessage(role="system", content=WEBTOON_ALIGNER_AGENT_PROMPT), ChatMessage(role="user", content=check_task)],
            temperature=0.0,
            max_tokens=min(args.max_tokens, 2000),
            timeout_s=args.timeout_s,
        )

        if "PASS" not in verdict:
            raise RuntimeError(f"质检未通过：\n{verdict}")

    out_path = scripts_dir / fmt_episode_filename(episode)
    if out_path.exists() and not args.overwrite:
        raise RuntimeError(f"目标文件已存在（加 --overwrite 允许覆盖）：{out_path}")

    write_text(out_path, draft.strip() + "\n")
    print(f"已写入: {out_path}")
    
    with get_project_lock(project_dir):
        current_plot_text = read_text(plot_path)
        updated = mark_plots_used(current_plot_text, plot_nums)
        write_text(plot_path, updated)
        print(f"已更新: {plot_path} (标记已用: {len(plot_nums)}条)")


def cmd_script(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    
    episodes_to_run = []
    
    if args.all:
        plot_path = project_dir / "plot-breakdown.md"
        if not plot_path.exists():
             raise RuntimeError(f"缺少 plot-breakdown.md：{plot_path}")
        plot_text = read_text(plot_path)
        episodes_to_run = get_unused_episodes(plot_text)
        if not episodes_to_run:
            print("没有发现未用集数。")
            return 0
        print(f"即将批量生成集数: {episodes_to_run}")
    elif args.episode is not None:
        episodes_to_run = [args.episode]
    else:
        print("错误：必须指定 --episode 或 --all")
        return 1

    concurrency = getattr(args, "concurrency", 1)

    if concurrency > 1 and len(episodes_to_run) > 1:
        print(f"并发执行: 启动 {concurrency} 个线程进行处理")
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_ep = {executor.submit(_generate_single_script, project_dir, ep, args): ep for ep in episodes_to_run}
            for future in concurrent.futures.as_completed(future_to_ep):
                ep = future_to_ep[future]
                try:
                    future.result()
                    print(f"第 {ep} 集生成完成。")
                except Exception as e:
                    print(f"第 {ep} 集生成失败: {e}")
                    import traceback
                    traceback.print_exc()
    else:
        for ep in episodes_to_run:
            print(f"\n>>> 开始生成第 {ep} 集 <<<\n")
            try:
                _generate_single_script(project_dir, ep, args)
            except Exception as e:
                print(f"第 {ep} 集生成失败: {e}")
                # Optional: break or continue. Let's continue to try others?
                # But if LLM fails, maybe better stop.
                # But for batch, maybe user wants to process as much as possible.
                # I will stop if it's a runtime error like API failure, but for "file exists" maybe continue?
                # The exception is generic Exception.
                # Let's print traceback and stop to be safe.
                import traceback
                traceback.print_exc()
                return 1
            
    return 0


def parse_range(s: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", s)
    if not m:
        raise argparse.ArgumentTypeError("范围格式应为: A-B")
    a = int(m.group(1))
    b = int(m.group(2))
    if a <= 0 or b <= 0 or a > b:
        raise argparse.ArgumentTypeError("范围必须为正数，且 A<=B")
    return a, b


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="workflow_standalone.py")
    p.add_argument("--project-dir", default=str(ROOT_DIR))

    p.add_argument("--api-style", choices=["anthropic", "openai"], default=os.environ.get("API_STYLE") or os.environ.get("CCR_API_STYLE", "anthropic"))
    p.add_argument("--api-base", default=os.environ.get("API_BASE") or os.environ.get("CCR_API_BASE") or "http://127.0.0.1:3456")
    p.add_argument("--api-key", default=os.environ.get("API_KEY") or os.environ.get("CCR_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    p.add_argument("--model", default=os.environ.get("MODEL") or os.environ.get("CCR_MODEL", "claude-sonnet-4-5-20250929"))
    p.add_argument("--timeout-s", type=int, default=int(os.environ.get("TIMEOUT_S") or os.environ.get("CCR_TIMEOUT_S", "600")))
    p.add_argument("--temperature", type=float, default=float(os.environ.get("TEMPERATURE") or os.environ.get("CCR_TEMPERATURE", "0.4")))
    p.add_argument("--max-tokens", type=int, default=int(os.environ.get("MAX_TOKENS") or os.environ.get("CCR_MAX_TOKENS", "8192")))
    p.add_argument("--novel-name", default=os.environ.get("NOVEL_NAME", "测试小说"))
    p.add_argument("--novel-type", default=os.environ.get("NOVEL_TYPE", "重生"))

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("status")
    sp.set_defaults(func=cmd_status)

    pp = sub.add_parser("ping")
    pp.set_defaults(func=cmd_ping)

    ip = sub.add_parser("init")
    ip.add_argument("--force", action="store_true")
    ip.set_defaults(func=cmd_init)

    bp = sub.add_parser("breakdown")
    bp.add_argument("--chapters", type=parse_range)
    bp.add_argument("--all", action="store_true", help="Breakdown all remaining chapters")
    bp.add_argument("--batch-size", type=int, default=6, help="Number of chapters per batch")
    bp.add_argument("--include-examples", action="store_true")
    bp.add_argument("--include-output-style", action="store_true")
    bp.set_defaults(func=cmd_breakdown)

    sc = sub.add_parser("script")
    sc.add_argument("--episode", type=int)
    sc.add_argument("--all", action="store_true", help="Generate all unused episodes")
    sc.add_argument("--chapters", type=parse_range)
    sc.add_argument("--overwrite", action="store_true")
    sc.add_argument("--include-examples", action="store_true")
    sc.add_argument("--check", action="store_true")
    sc.add_argument("--concurrency", type=int, default=1, help="并发执行的线程数")
    sc.set_defaults(func=cmd_script)

    return p


def main(argv: Sequence[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as e:
        msg = str(e).strip()
        if not msg:
            msg = repr(e)
        sys.stderr.write(msg + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

