import argparse
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Any
import filelock

# 用法示例（Windows / PowerShell）
# 1) 初始化项目（自动创建 scripts/ 和 storyboard_output/ 目录）：
#    python storyboard_workflow.py init
#
# 2) 查看项目状态：
#    python storyboard_workflow.py status
#
# 3) 生成节拍拆解表（Breakdown）：
#    python storyboard_workflow.py breakdown
#
# 4) 生成九宫格提示词（Beat Board）：
#    python storyboard_workflow.py beatboard
#
# 5) 生成四宫格提示词（Sequence Board）：
#    python storyboard_workflow.py sequence
#
# 6) 生成动态提示词（Motion Prompts）：
#    python storyboard_workflow.py motion
#
# API 配置（命令行参数优先，其次环境变量）：
# 1) OpenAI 格式（默认）：
#    python storyboard_workflow.py --api-key "sk-..." --api-base "https://api.openai.com/v1" --model "gpt-4o" breakdown
#
# 2) Anthropic 格式：
#    python storyboard_workflow.py --api-style "anthropic" --api-key "sk-ant-..." --model "claude-3-5-sonnet-20240620" beatboard
BEAT_BREAKDOWN_TEMPLATE = """---
name: beat-breakdown-template
description: 节拍拆解表模板。用于从剧本/梗概中识别叙事曲线的关键拐点，选取锚点用于九宫格生成（数量按目标格数）。
---

# 节拍拆解表

## 基本信息
- 项目名称：<项目名称>
- 集数/章节：<ep01 / ch01 / 单集>
- 素材来源：<剧本 / 梗概 / 分场大纲>
- 视觉风格：<真人写实 / 3D CG / 皮克斯 / 迪士尼 / 国漫 / 日漫 / 韩漫>
- 目标媒介：<电影 / 短剧 / 漫剧 / MV / 广告>
- 画幅比例：<16:9（横屏） / 9:16（竖屏）>

## 节拍拆解

| Beat | 事件摘要 | 观众获得 | 强度 | 锚点 |
|------|---------|---------|------|------|
| 1 | <这个节拍发生了什么> | <信息/情绪/悬念> | <低/中/高> | <是/否> |
| 2 | <这个节拍发生了什么> | <信息/情绪/悬念> | <低/中/高> | <是/否> |
| 3 | <这个节拍发生了什么> | <信息/情绪/悬念> | <低/中/高> | <是/否> |
| ... | ... | ... | ... | ... |

## 锚点选取摘要

选中的锚点（对应九宫格，数量按目标格数）：

| 格子 | Beat | 拐点类型 | 事件摘要 |
|------|------|---------|---------|
| 1 | #<编号> | <世界观建立/诱因事件/转折/高潮等> | <摘要> |
| 2 | #<编号> | <拐点类型> | <摘要> |
| 3 | #<编号> | <拐点类型> | <摘要> |
| 4 | #<编号> | <拐点类型> | <摘要> |
| 5 | #<编号> | <拐点类型> | <摘要> |
| 6 | #<编号> | <拐点类型> | <摘要> |
| 7 | #<编号> | <拐点类型> | <摘要> |
| 8 | #<编号> | <拐点类型> | <摘要> |
| 9 | #<编号> | <拐点类型> | <摘要> |

如目标格数小于9，未使用的格子请写“占位”，锚点标记为“否”。

## 字段说明

### 节拍拆解表字段
- **Beat**：节拍序号，按剧情顺序编号
- **事件摘要**：这个节拍发生了什么（最小叙事单元）
- **观众获得**：观众从这个节拍获得的信息、情绪或悬念
- **强度**：节拍的情绪/戏剧强度（低/中/高）
- **锚点**：是否被选为九宫格锚点（是/否），全表应有且仅有目标格数个"是"

### 锚点选取摘要字段
- **格子**：九宫格的位置（1-9）
- **Beat**：对应的节拍编号
- **拐点类型**：叙事曲线上的功能定位
- **事件摘要**：简要描述

### 拐点类型参考
1. 世界观/基调建立
2. 主角现状与目标/缺口
3. 诱因事件（推动离开现状）
4. 第一次转折（踏入新局面）
5. 中点升级/认知反转
6. 危机/低谷（代价与受挫）
7. 高潮前集结（选择与准备）
8. 高潮对抗/结果
9. 结局/余韵（收束）

注：拐点类型仅供参考，实际选取应根据具体剧情灵活调整。
"""

BEAT_BOARD_TEMPLATE = """---
name: beat-board-template
description: Beat Board 九宫格提示词模板。提示词采用叙事描述式，参考 gemini-image-prompt-guide.md。
---

请生成一张 3x3 九宫格布局的电影分镜关键帧图像。每个格子代表一个故事节拍，9格共同构成连贯的叙事序列。所有格子必须保持风格、角色外观、光影的完全一致。请按照以下规范生成。

---

## 剧情概述
[用简洁的要点列出本段落要呈现的关键剧情]
- 
- 
- 

## 角色一致性（Character Consistency）
- [角色A]：[性别]，[年龄]，[气质]；[身形、五官描述]；[情绪弧线]；[服饰描述]；[发型描述]。
- [角色B]：[性别]，[年龄]，[气质]；[身形、五官描述]；[情绪弧线]；[服饰描述]；[发型描述]。
- [群像（如有）]：[人数、服饰统一性、表情倾向等]。
关键要求：同一角色在所有格子里脸型、发型、服饰、配饰必须 100% 一致，不换脸、不换衣。

## 视觉规范（Visual Guidelines）
整体风格：
[描述整体美术风格、渲染质量、镜头语言特点]

色彩与光影：
[描述主色调、光源类型、情绪氛围的光影表达]

材质：
[描述关键材质、环境细节]

镜头语言：
[描述本项目偏好的镜头运动、构图特点]

## 特殊约束（Constraints）
[列出本项目的特殊限制，如无可删除此部分]
- 
- 

## 九宫格布局
第1行：格1-3 / 第2行：格4-6 / 第3行：格7-9
叙事连贯，情绪递进。
当目标格数小于9时，仅前N格承载完整剧情，其余格子写“占位”，不新增剧情信息。

## Panel Breakdown（九格关键帧拆解）
[采用叙事描述式提示词，参考 gemini-image-prompt-guide.md]

1（第1行左）——【[标题]】
视角：[完整叙事描述：景别、机位、场景环境、角色位置与动作、光影氛围，融合为流畅的段落]
重点：[这一格要强调的视觉元素、细节]

2（第1行中）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

3（第1行右）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

4（第2行左）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

5（第2行中）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

6（第2行右）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

7（第3行左）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

8（第3行中）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

9（第3行右）——【[标题]】
视角：[完整叙事描述]
重点：[视觉强调点]

## 技术约束（Technical Constraints）
[列出需要AI出图时注意的技术要求]
- 
- 
"""

SEQUENCE_BOARD_TEMPLATE = """---
name: sequence-board-template
description: Sequence Board 四宫格提示词模板。用于展开九宫格中的每一格，每格生成4张连续动作/情绪的关键帧。使用九宫格对应格作为垫图输入，提示词只需描述动作/情绪/镜头变化。
---

# Sequence Board 四宫格提示词

---

## 格1展开——【[九宫格格1标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格2展开——【[九宫格格2标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格3展开——【[九宫格格3标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格4展开——【[九宫格格4标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格5展开——【[九宫格格5标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格6展开——【[九宫格格6标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格7展开——【[九宫格格7标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格8展开——【[九宫格格8标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

---

## 格9展开——【[九宫格格9标题]】

请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。

1（左上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

2（右上）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

3（左下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]

4（右下）——【[标题]】
出场人物：[人物列表]
场景：[场景名称]
视角：[景别、机位变化、角色动作、情绪状态]
重点：[视觉强调点]
"""

def normalize_sequence_counts(grid_count: Optional[int], panels_per_grid: Optional[int]) -> tuple[int, int]:
    grid = int(grid_count) if grid_count is not None else 9
    panels = int(panels_per_grid) if panels_per_grid is not None else 4
    grid = max(1, min(9, grid))
    panels = max(2, min(6, panels))
    return grid, panels

def build_sequence_board_template(grid_count: int, panels_per_grid: int) -> str:
    grid_count, panels_per_grid = normalize_sequence_counts(grid_count, panels_per_grid)
    if grid_count == 9 and panels_per_grid == 4:
        return SEQUENCE_BOARD_TEMPLATE
    lines = []
    lines.append("---")
    lines.append("name: sequence-board-template")
    lines.append(f"description: Sequence Board 提示词模板。用于展开九宫格中的每一格，每格生成{panels_per_grid}张连续动作/情绪的关键帧。使用九宫格对应格作为垫图输入，提示词只需描述动作/情绪/镜头变化。")
    lines.append("---")
    lines.append("")
    lines.append("# Sequence Board 提示词")
    for g in range(1, grid_count + 1):
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"## 格{g}展开——【[九宫格格{g}标题]】")
        lines.append("")
        if panels_per_grid == 4:
            lines.append("请基于参考图片，生成一张 2x2 四宫格布局的电影分镜关键帧图像。保持参考图片中的角色外观、场景风格、光影完全一致。4格展开一段连续的动作/情绪序列。")
        else:
            lines.append(f"请基于参考图片，生成一组连续关键帧，共{panels_per_grid}张。保持参考图片中的角色外观、场景风格、光影完全一致。")
        lines.append("")
        labels = ["左上", "右上", "左下", "右下"]
        for i in range(1, panels_per_grid + 1):
            if panels_per_grid == 4:
                label = labels[i - 1]
                lines.append(f"{i}（{label}）——【[标题]】")
            else:
                lines.append(f"{i}（第{i}格）——【[标题]】")
            lines.append("出场人物：[人物列表]")
            lines.append("场景：[场景名称]")
            lines.append("视角：[景别、机位变化、角色动作、情绪状态]")
            lines.append("重点：[视觉强调点]")
            lines.append("")
    return "\n".join(lines).strip() + "\n"

MOTION_PROMPT_TEMPLATE = """---
name: motion-prompt-template
description: Motion Prompt 动态提示词模板。每组 5 个（1 关键帧 + 4 四宫格），共 9 组 45 个。
---

# Motion Prompt 模板

[任务指令]
    读取 sequence-board-prompt.md，为每个 Beat Anchor 生成一组动态提示词：
    - 1 个关键帧动态提示词（对应九宫格该格）
    - 4 个四宫格动态提示词（对应四宫格展开）
    共 9 组，每组 5 个，共 45 个 Motion Prompt

---

# 动态提示词（Motion Prompts）

## 格1：[节拍名称]

### 关键帧
1-0: [Motion Prompt]

### 四宫格展开
1-1: [Motion Prompt]
1-2: [Motion Prompt]
1-3: [Motion Prompt]
1-4: [Motion Prompt]

---

## 格2：[节拍名称]

### 关键帧
2-0: [Motion Prompt]

### 四宫格展开
2-1: [Motion Prompt]
2-2: [Motion Prompt]
2-3: [Motion Prompt]
2-4: [Motion Prompt]

---

## 格3：[节拍名称]

### 关键帧
3-0: [Motion Prompt]

### 四宫格展开
3-1: [Motion Prompt]
3-2: [Motion Prompt]
3-3: [Motion Prompt]
3-4: [Motion Prompt]
---

## 格4：[节拍名称]

### 关键帧
4-0: [Motion Prompt]

### 四宫格展开
4-1: [Motion Prompt]
4-2: [Motion Prompt]
4-3: [Motion Prompt]
4-4: [Motion Prompt]

---

## 格5：[节拍名称]

### 关键帧
5-0: [Motion Prompt]

### 四宫格展开
5-1: [Motion Prompt]
5-2: [Motion Prompt]
5-3: [Motion Prompt]
5-4: [Motion Prompt]

---

## 格6：[节拍名称]

### 关键帧
6-0: [Motion Prompt]

### 四宫格展开
6-1: [Motion Prompt]
6-2: [Motion Prompt]
6-3: [Motion Prompt]
6-4: [Motion Prompt]

---

## 格7：[节拍名称]

### 关键帧
7-0: [Motion Prompt]

### 四宫格展开
7-1: [Motion Prompt]
7-2: [Motion Prompt]
7-3: [Motion Prompt]
7-4: [Motion Prompt]

---

## 格8：[节拍名称]

### 关键帧
8-0: [Motion Prompt]

### 四宫格展开
8-1: [Motion Prompt]
8-2: [Motion Prompt]
8-3: [Motion Prompt]
8-4: [Motion Prompt]

---

## 格9：[节拍名称]

### 关键帧
9-0: [Motion Prompt]

### 四宫格展开
9-1: [Motion Prompt]
9-2: [Motion Prompt]
9-3: [Motion Prompt]
9-4: [Motion Prompt]
"""

VOICEOVER_TABLE_TEMPLATE = """---
name: voiceover-table-template
description: 配音表模板。按四宫格画面编号生成对应配音条目。
---

李道玄：一边吸溜着面条，一边盯着造景箱，眼神中透着一种诡异的满足感。

李道玄：奇怪，明明是二十九块钱的料理包外卖，看着这群小人吃得那么香，我这碗面怎么也变得像国宴一样美味了？
"""

STORYBOARD_PLAYBOOK = """---
name: storyboard-methodology-playbook
description: 影视分镜方法论。当需要将剧本、故事梗概或分场大纲转化为 AI 出图用的分镜提示词时使用。采用分层渐进式流程：节拍拆解 → Beat Board 九宫格 → Sequence Board 四宫格，确保分镜清晰可读、简洁高效、连贯流畅，人物与场景在全流程中保持一致。
---

[第一性原则]
    清晰（Clarity）
        - 每张分镜必须让人"一眼看懂"：
            - 画面焦点是谁？
            - 发生了什么？
            - 观众获得了什么信息/情绪？
        - 所有视觉元素（布景、特效、气氛）必须服务叙事，不得喧宾夺主
        - 角色永远是画面焦点，即使为了氛围添加背景细节，也需确保观众视线首先落在角色和行为上

    简洁（Simplicity）
        - 一镜一意 / 关键帧原则：
            - 默认：一个镜头或一个剧情节拍（beat）用一张关键帧表达
            - 只有当镜头内调度复杂、或动作必须分解追踪时，才拆多格（A/B/C），并说明拆格原因
            - 当目标分镜数量较少时，允许将相邻节拍合并为一个更大的叙事段落，确保起承转合与结局完整覆盖
        - 经济性：
            - 能用一个画面讲清，就不要重复画同信息点
            - 同一信息点尽量只出现一次"重点强调"，避免冗余
            - 每个镜头都必须有明确的叙事目的，无目的镜头应删除

    连贯（Continuity）
        - 连贯性优先于花活
        - 让观众始终不迷路：
            - 空间关系稳定（轴线/左右关系）
            - 屏幕方向稳定（面向/运动方向）
            - 视线方向稳定（对话/对峙）
            - 动作衔接自然（动作中段切）
            - 避免跳接（角度与景别变化不足）

    分层/渐进式优先（Progressive Refinement）
        - 优先采用：节拍拆解 → Beat Board（九宫格总览）→ Sequence Board（四宫格展开）
        - Beat Board 的职责是"选点与定锚"，生成后作为 Sequence Board 的参考图片（垫图）
        - 四宫格生成时，以九宫格对应格作为参考图片输入，确保人物与场景一致性


[核心概念与术语]
    Story Beat（节拍）
        - 一个最小叙事单元：发生了什么 + 观众得到什么（信息/情绪/悬念）
        - 节拍强度可标注：低/中/高（用于节奏设计）
        - 节拍拆解阶段会识别出所有关键节拍，从中选取9个作为九宫格的锚点

    Shot（镜头）
        - 电影/动画剪辑的基本单位
        - 分镜的"镜头"必须能回答：拍什么、怎么拍、为什么这样拍

    Beat Board（九宫格总览板）
        - 用 9 张关键帧覆盖"叙事曲线关键拐点"
        - 目的：叙事总览清晰 + 统一视觉锚点（人物/服装/场景要素/光色气氛）
        - 工程用途：生成后作为 Sequence Board 的参考图片（垫图）
        - 数量关系：固定9格，对应9个关键叙事拐点

    Sequence Board（四宫格/可变格展开板）
        - 围绕某个九宫格中的某一格，展开段落内部的连续动作/因果推进
        - 默认四格结构：起—承—转—合
        - 格数可变：2/4/6（由复杂度决定）
        - 生成时以九宫格对应格作为参考图片（垫图），继承人物/场景/光色描述
        - 数量关系：每个九宫格格子可展开为一组四宫格，最多9组

    参考图片 / 垫图（Reference Image）
        - AI图像生成时输入的参考图片，用于保持视觉一致性
        - 在本流程中：九宫格的某一格 → 作为该格对应四宫格的垫图
        - 目的：确保四宫格继承九宫格的人物外观、服装、场景、光色
        - 技术实现：在AI出图时，将垫图作为 image reference 或 style reference 输入

    Continuity（连贯性）
        - 镜头之间的空间与动作延续规则集合（方向/轴线/视线/道具/动作/剪接点）

    Coverage（覆盖）
        - 为同一节拍/段落提供不同景别/角度的镜头组合
        - 常见：远/全景交代 → 中景互动/动作 → 近景/特写抓情绪与细节

    视觉风格（Visual Style）
        - 指整体画面的美术风格倾向
        - 常见类型：真人写实、动画风格、插画风格、赛博朋克、复古胶片等
        - 本流程默认：真人写实风格（可被用户覆盖）
        - 一旦确定，全流程（九宫格+四宫格）必须保持风格统一


[规则库]
    [叙事清晰规则]
        镜头目的（Purpose）必须明确
            - 每个镜头/关键帧至少对应一种目的（可组合）：
                - 建立环境与位置关系（建立镜头）
                - 推进因果信息（规则/线索/结果）
                - 强化情绪（表情/心理压力）
                - 强调细节（道具/线索/危险提示）
                - 制造悬念（藏与露、遮挡、主观视角）
            - 如果无法回答"这个镜头的目的是什么"，则该镜头需要修改或删除

        信息控制：藏与露
            - 不一次性把信息全交代完
            - 常用方式：
                - 遮挡/框景/留白
                - 插针式细节特写（危险提示/线索提示）
                - 先给结果反应再揭示原因（或反过来）
            - 合理留白能控制信息量，让观众对未明示的部分产生好奇，加深情绪共鸣

        节奏的"呼吸"
            - 镜头序列应有远/中/近、动/静、明/暗、快/慢的对比
            - 快节奏之后要安排呼吸点（静镜/空镜/停留镜头）以增强张力曲线
            - 长时间停留的镜头可用于突出戏剧张力或角色情感

        角色意图与状态呈现
            - 通过肢体语言、面部表情、构图暗示传达角色内在意图
            - 姿态表情映射：
                - 前倾 → 紧张/进攻/专注
                - 后仰 → 防御/震惊/抗拒
                - 低头垂肩 → 沮丧/疲惫/认输
                - 双臂交叉 → 防备/封闭
                - 握拳 → 愤怒/决心
            - 以物代人技法：不直接描绘角色，通过周围事物反应表现角色状态
                - 例：特写攥紧发白的手指、颤抖溢出的咖啡杯 → 传达紧张愤怒
                - 例：风吹散的文件、打翻的椅子 → 传达慌乱
            - 道具暗示：剑出鞘=准备战斗，掉落酒杯=震惊失控，凋零的花=希望破灭

        冲突与转折的视觉暗示
            - 关键帧强化：冲突瞬间用特写定格，绘制更详细夸张的画面
                - 火花碎片、扭曲的表情、冲击波纹等
            - 象征性意象：用隐喻画面暗示转折含义
                - 例：雨伞滑落=关系变化，贴纸飘落=信念动摇
                - 例：从阴影走向光亮=内心转变，镜子破碎=自我认知崩塌
            - 构图转变体现境遇反转：
                - 原本占据画面中心 → 被边缘化到角落
                - 原本仰视强势角色 → 变为俯视其弱势
                - 周围留白从少变多 → 孤立感增强
            - 色调/光线转变：从亮转暗或反之，强调剧情转折点

    [构图与视觉引导规则]
        单帧必须成立（每张分镜都要落地回答）
            - 主体是谁（焦点）
            - 主体在哪（位置、比例、前中后景层次）
            - 观众先看哪（视觉引导：对比、线条趋势、明暗、大小）
            - 信息藏哪/露哪（留白、遮挡、框景、景深层次）

        线条与形状的情绪语义（用于构图气质）
            - 水平线/垂直线：稳定、秩序、庄重
            - 斜线/对角线：动势、不安、冲突
            - 曲线：柔和、亲切
            - 尖锐折线：紧张、强硬
            - 圆形：完整、和谐、保护
            - 三角形：稳定（正）、危险（倒）

        对比与层次（让焦点更"抓眼"）
            - 明暗对比：聚焦主体、制造张力
            - 大小对比：建立主次关系
            - 色彩对比：冷暖、饱和度、互补色
            - 景深与层次：前景框景/遮挡、中景主体、背景信息提示

        空间情绪（压迫 vs 释放）
            - 压迫感营造：
                - 前景挤压、阴影压迫
                - 主体被角落化、环境拥挤
                - 充满紧闭空间和倾斜线条
                - 天花板/墙壁入画形成封闭感
            - 释放感营造：
                - 开阔留白、地平线可见
                - 简化背景干扰
                - 大量留白强化角色渺小与孤独感（也可传达自由）

        三分法构图（Rule of Thirds）
            - 将画面横竖各分为三等分
            - 重要主体尽量落在分割线或交点附近
            - 获得稳定且吸引注意力的构图
            - 地平线通常放在上1/3或下1/3线上

        引导线（Leading Lines）
            - 利用道路、栏杆、透视线、明暗交界线等，将视线引向主体
            - 对角线引导线可增强动势与张力
            - 曲线引导线可增加优雅与流动感

        框中取景（Frame within Frame）
            - 用门窗、树枝、走廊、拱门等形成"画中画"
            - 强化焦点、增加层次
            - 提供情境框架（氛围叙事）
            - 可暗示角色被困、被监视、与世界隔离等

        景深与深焦/浅焦（Depth of Field）
            - 浅景深：突出主体、弱化背景干扰，强化情绪或梦幻感
            - 深景深/深焦：同时呈现前景细节与背景信息，适合复杂调度与信息同框
            - 焦点转换（rack focus）：引导观众注意力从A转到B

        画面比例（纵横比）意识
            - 分镜阶段应明确最终画幅比例（如 16:9、2.39:1 等）
            - 同一构图在不同纵横比下的有效性不同，需要提前校正
            - 宽银幕(2.39:1)适合横向展现开阔景观
            - 传统比例(4:3)更适于竖直方向的主体

    [光影与色彩规则]
        光质选择
            - 柔光（soft lighting）：
                - 光影过渡平滑、阴影淡化
                - 营造温馨、平静、浪漫的效果
                - 适用：人物肖像、美好回忆、温情场景
            - 硬光（hard lighting）：
                - 产生鲜明对比和清晰阴影
                - 制造戏剧性紧张感或突出冲突氛围
                - 适用：审讯、对峙、恐怖、悬疑
"""

MOTION_METHODOLOGY = """---
name: motion-prompt-methodology
description: 图生视频动态提示词方法论。用于将静态分镜转化为 AI 视频工具（Runway、Kling、Pika 等）的动态提示词。包含镜头运动、主体动作、速度修饰、氛围风格的词汇库与转化规则。
---

# 图生视频动态提示词方法论（Motion Prompt Methodology）

[第一性原则]
    图片已见原则
        - AI 能"看到"输入图片，不需要重复描述图片内容
        - 只描述"变化"：动作、运动、情绪转变
        - 重复描述图片内容会导致运动减少或异常

    简洁优先原则
        - 最佳长度：50-200 字符（英文）
        - 聚焦 2-3 个核心元素
        - 信息过载会导致模型困惑

    具体动作原则
        - 用具体的物理动作，避免抽象概念
        - "hair flowing in wind" ✓
        - "embodies the essence of freedom" ✗

    运动限制原则
        - 镜头运动：最多 1-2 种
        - 主体运动：最多 1-2 种
        - 过多运动会产生混乱

[提示词结构]
    基本公式
        镜头运动 + 主体动作 + 速度/节奏 + 氛围/风格

    完整公式（复杂场景）
        镜头运动 + 主体动作 + 环境动态 + 速度/节奏 + 氛围/风格 + 技术参数

    示例
        基本：Camera slowly pushes in while subject turns head
        完整：Slow dolly in, subject turns head, hair flowing gently in wind, golden hour lighting, cinematic 24fps

[镜头运动词汇库]
    推拉类（Dolly）
        - dolly in / push in：推近，聚焦、紧张、亲密
        - dolly out / pull back：拉远，揭示、疏离、结束感
        - dolly zoom / vertigo effect：眩晕效果，心理冲击

    横纵摇类（Pan/Tilt）
        - pan left / pan right：横摇，环顾、跟随水平运动
        - tilt up / tilt down：纵摇，强调高度、规模、威严
        - whip pan：快速横摇，转场、惊讶

    环绕类（Orbit/Arc）
        - orbit around subject：环绕主体，立体感、动感
        - arc shot：弧形运动，戏剧性、强调
        - 180-degree orbit：半环绕，常用于对话、对峙
        - 360-degree orbit：全环绕，产品展示、英雄时刻

    跟拍类（Tracking）
        - tracking shot：跟随主体移动
        - follow from behind：背后跟拍
        - side tracking：侧面跟拍
        - leading shot：前方引导

    变焦类（Zoom）
        - zoom in：变焦推近，强调、戏剧性
        - zoom out：变焦拉远，揭示全貌
        - slow zoom：缓慢变焦，悬疑、张力

    升降类（Crane/Jib）
        - crane up / rising shot：上升，史诗感、希望
        - crane down / descending shot：下降，压迫、沉重
        - aerial / drone shot：航拍，规模、全景

    手持与稳定（Handheld/Stabilized）
        - handheld：手持，真实感、紧张、纪录片风格
        - steady / locked camera：固定机位，稳定、庄重
        - floating camera：漂浮感，梦幻、超现实

    焦点类（Focus）
        - rack focus：焦点转移，引导注意力
        - shallow depth of field：浅景深，突出主体
        - deep focus：深焦，环境信息丰富

[主体动作词汇库]
    面部动作
        - eyes open slowly：缓慢睁眼
        - subtle smile forming：微笑浮现
        - gaze shifts：目光转移
        - eyebrows raise：眉毛上扬
        - blinks naturally：自然眨眼
        - expression transitions from X to Y：表情从X转为Y

    头部动作
        - head turns：转头
        - head tilts slightly：微微歪头
        - nods slowly：缓慢点头
        - looks up / down / away：抬头/低头/移开视线

    身体动作
        - breathing motion：呼吸起伏
        - shoulders rise and fall：肩膀起伏
        - leans forward / back：前倾/后仰
        - stands up / sits down：站起/坐下
        - walks forward / toward camera：向前走/走向镜头
        - reaches out hand：伸出手

    手部动作
        - hand raises：举手
        - fingers move：手指动作
        - grips tighter：握紧
        - gestures while speaking：说话时比划

    环境互动
        - hair flowing in wind：头发随风飘动
        - clothes rustling：衣服飘动
        - fabric billowing：布料鼓起
        - water splashing：水花飞溅
        - leaves falling：落叶飘落
        - smoke rising：烟雾升起
        - dust particles floating：尘埃飘浮

[速度与强度修饰词]
    缓慢/轻柔
        - slowly, gently, gradually, softly
        - subtle, slight, delicate
        - natural, organic, barely perceptible
        - micro-movements, minimal motion

    中等/自然
        - smoothly, steadily, naturally
        - moderate, balanced, controlled
        - fluid, flowing, continuous

    快速/强烈
        - quickly, rapidly, suddenly
        - dramatic, bold, powerful, intense
        - explosive, dynamic, energetic
        - sweeping, grand, epic

[氛围与风格词汇]
    电影风格
        - cinematic, filmic, movie-quality
        - blockbuster style, Hollywood quality
        - indie film aesthetic
        - documentary style

    导演风格（参考）
        - Christopher Nolan cinematography：史诗、庄重
        - David Fincher style：悬疑、精准
        - Terrence Malick aesthetic：诗意、自然光
        - Wes Anderson style：对称、色彩饱和

    情绪氛围
        - dramatic, intense, suspenseful
        - romantic, dreamy, nostalgic
        - mysterious, eerie, haunting
        - joyful, energetic, uplifting
        - melancholic, somber, contemplative

    技术参数（可选）
        - 24fps：电影感
        - 60fps：流畅、慢动作素材
        - slow motion：慢动作
        - film grain：胶片颗粒感
        - lens flare：镜头光晕
        - bokeh：背景虚化光斑

[禁忌规则]
    绝对禁忌
        - ❌ 否定句（No movement, Don't zoom）
            → AI 不理解否定，可能产生相反效果
            → ✓ 用肯定句：The camera stays still / locked camera

        - ❌ 重复图片内容
            → 会导致运动减少或静止
            → ✓ 只描述动作变化

        - ❌ 抽象概念（embodies freedom, manifests joy）
            → AI 无法解释抽象意图
            → ✓ 用具体物理动作

        - ❌ 多重场景变化
            → 模型无法处理复杂转场
            → ✓ 单一场景、单一动作链

    避免事项
        - ⚠️ 超过 2 种镜头运动组合
        - ⚠️ 超过 2 种主体运动组合
        - ⚠️ 过长提示词（超过 300 字符）
        - ⚠️ 违反物理规律的动作
        - ⚠️ 与图片内容矛盾的描述

[提示词模板]
    人物肖像动态化
        [镜头运动], [面部动作], [环境动态], [氛围]
        示例：Slow dolly in, eyes open slowly, hair flowing gently in wind, cinematic lighting

    产品展示
        [环绕运动], [光影变化], [材质强调], [风格]
        示例：360-degree orbit around product, reflections dancing on surface, premium feel, Apple commercial style
"""

GEMINI_IMAGE_PROMPT_GUIDE = """---
name: gemini-image-prompt-guide
description: 针对 Gemini 原生图像生成（Nano Banana / Nano Banana Pro）的提示词最佳实践指南。用于生成影视分镜风格的 AI 图像。
---

[核心原则]
    叙事描述优先（Narrative Over Keywords）
        - Gemini 的核心优势是深度语言理解
        - 用完整的叙事性段落描述场景，而非逗号分隔的关键词堆叠
        - 错误示范：中景, 低角度, 冷蓝色调, 戏剧性光影
        - 正确示范：中景，略微仰拍。冷蓝色的光线打在他脸上，勾勒出深刻的阴影。

    场景化思维（Scene-Based Thinking）
        - 把每个画面当作电影中的一个镜头来描述
        - 回答：谁在哪里、做什么、环境如何、光线如何、情绪如何
        - 用短句分层描述，先整体后细节

    摄影术语融入自然语言（Photography Terms in Context）
        - 不要孤立列出术语，而是描述其效果
        - 错误：85mm镜头, 浅景深, 虚化
        - 正确：85mm人像镜头，背景柔和虚化，主体从环境中跃然而出。

    情绪与氛围具体化（Specific Mood Description）
        - 不只说"戏剧性"或"紧张"，而是描述具体的视觉表现
        - 用光影、色彩、空间关系来传达情绪
        - 例：顶光在他眼窝下刻出深深的阴影，疲惫与挫败感扑面而来。


[提示词结构模板]

    通用模板
        [景别]，[环境]。
        [主体描述]，[动作/状态]。
        [光线描述]，[光影效果]。
        [角度/构图说明]。
        [氛围/情绪]。

    写实场景模板
        写实风格，[景别]。[环境：时间、地点]。
        [主体]，[表情/动作/状态]。
        [光源]从[位置]照来，[光影效果]。
        [景深效果说明]。
        氛围[情绪]。

    动作场景模板
        [景别]，[动作]的瞬间。
        [主体]，[肢体位置、运动方向]。
        [环境元素：碎片/尘土/水花]。
        [角度]，[角度效果]。
        [光线]。氛围[情绪]。

    对话/对峙场景模板
        [景别]，[环境]。
        [人物A]与[人物B][位置关系]。
        [人物A状态]，[人物B状态]。
        [光线如何区分/连接两人]。
        [构图效果]。氛围[情绪]。

    情绪特写模板
        特写，[主体的具体部位]。
        [细节描述：皱纹/伤痕/表情/动作]。
        [光质]从[方向]照来，[光影强化情绪]。
        背景[虚化/暗化]。
        传达出[内在情绪/心理状态]。

    建立镜头模板
        [极远景/远景]，[地点/世界观]。
        [环境宏观描述：地形/建筑/天气]。
        [画面小元素：人物剪影/车辆等]。
        [光线/时间段]，[天空/云层/雾气]。
        构图强调[空旷/压迫/神秘]。氛围[情绪]。


[影视分镜提示词示例]

    示例1：紧张对峙（剧情片）
        模板类型：对话/对峙场景
        
        中景，昏暗的地下停车场。
        两个男人面对面站立。穿皱巴巴西装的男人身体前倾，咬紧下巴，姿态充满攻击性；皮夹克男人双臂交叉，表情难以捉摸。
        头顶荧光灯闪烁，刺眼的光线将两人的脸分割成明暗两半。身后混凝土柱子形成牢笼般的框架。
        略微仰拍，两人都显得气势逼人。
        冷蓝绿色调。一触即发，暴力随时可能爆发。

    示例2：温馨回忆（剧情片）
        模板类型：情绪特写
        
        特写，年轻女性的面容。
        她望向雨水划过的窗户，眼中闪着未落的泪光，嘴角却浮现一丝温柔的微笑。手中握着一张老照片，手指轻轻描摹着边缘。
        黄金时段的柔光透过窗户，温暖她的面容，在凌乱的发丝上晕出光晕。
        背景是温馨的客厅和书架，85mm镜头虚化成柔和的色块。
        苦涩而温柔，私密的回忆时刻。

    示例3：孤独远景（剧情片）
        模板类型：建立镜头
        
        极远景，无尽的灰色海滩。
        一个孤独的身影站在边缘。阴沉的天空，平坦无色的沙滩，这个人显得无比渺小。远处海浪轻轻拍打海岸。
        阴天散射光，天空与地平线无缝融合。没有其他人，没有鸟，没有生命的迹象。
        大量留白，灰色与淡蓝的低饱和色调。
        安静，沉重，深深的孤独。

    示例4：动作高潮（动作片）
        模板类型：动作场景
        
        中景，剑击的顶点瞬间。
        女战士身体扭转，剑刃向下划出钢铁残影，脸上满是坚毅。火花从撞击点飞溅——剑与刚入画的敌人盾牌相撞。尘土碎片在她周围旋转，定格在空中。
        略微倾斜的荷兰角，低机位，强调她的力量。背后轮廓光勾勒剪影，侧光展现肌肉的紧绷。
        24mm广角，夸大运动感与纵深。
        紧张，爆发。

    示例5：悬疑揭示（悬疑片）
        模板类型：情绪特写
        
        紧凑特写，侦探的面容。
        恐怖领悟的瞬间。眼睛几乎难以察觉地睁大，瞳孔收缩。一滴汗珠从太阳穴滑落。
        脸的左半隐没在深影中，右侧被单一光源照亮——每一个毛孔、每一道皱纹都清晰可见。身后完全失焦，隐约可辨犯罪现场照片的轮廓。
        浅景深隔离表情，冷淡去饱和的色调，病态的绿与灰。
        蔓延的恐惧，可怕的顿悟。

    示例6：世界观建立（奇幻/科幻）
        模板类型：建立镜头
        
        极远景，黄昏时分的浮空城市。
        巨大石质平台在云间漂浮，由不可思议的长吊桥相连。瀑布从边缘倾泻入下方虚空。数千扇小窗散发温暖的琥珀色光芒，落日将云层染成深紫与燃烧的橙。
        前景，一个旅人的剪影站在悬崖边缘仰望，渺小的身影衬托城市的巨大。体积光穿过云层缝隙。
        惊奇与敬畏，不可能世界中的冒险。

    示例7：压迫与威胁（惊悚片）
        模板类型：通用模板变体
        
        中近景，狭窄走廊。
        年轻女性被压在墙上，呼吸在冷空气中可见，眼睛惊恐地看向画外。墙壁似乎向内倾斜，剥落的机构绿。
        头顶裸露灯泡轻轻摇晃，阴影在她脸上不可预测地移动。
        高角度俯拍，她显得渺小而脆弱。深影淤积在画面角落，几乎不留头顶空间。
        病态的色调——泛黄的白、肮脏的绿、深沉的黑。
        原始的恐惧，迫在眉睫的危险。


[Gemini 特有参数说明]

    画幅比例（Aspect Ratio）
        - 可用比例：1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
        - 16:9：标准宽银幕，适合大多数影视分镜
        - 21:9：超宽银幕，适合史诗感建立镜头
        - 9:16：竖屏，适合移动端短视频
        - 在提示词中可用自然语言描述："Horizontal widescreen format" 或 "Vertical portrait orientation"

    分辨率（仅 Gemini 3 Pro / Nano Banana Pro）
        - 1K（默认）：约 1024px
        - 2K：约 2048px
        - 4K：约 4096px
        - 高分辨率适合需要放大查看细节的场景

    模型选择建议
        - Gemini 2.5 Flash Image（Nano Banana）：
            - 速度快、成本低
            - 适合快速迭代、批量生成
            - 分辨率最高 1024px
        - Gemini 3 Pro Image Preview（Nano Banana Pro）：
            - 质量更高、支持复杂指令
            - 内置 Thinking 过程优化构图
            - 支持 Google Search 实时信息
            - 支持最高 4K 分辨率
            - 适合最终成品输出


[影视术语自然语言转换参考]

    景别写法
        - 极远景 → "极远景，[地点]。" / "极远景，[环境全貌]。"
        - 远景 → "远景，[场景全貌]。"
        - 全景 → "全景，[角色]从头到脚可见。"
        - 中景 → "中景，[角色]腰部以上。"
        - 近景 → "近景，[角色]面部。"
        - 特写 → "特写，[具体部位/物件]。"
        - 极特写 → "极特写，[眼睛/嘴唇/手指等细节]。"

    角度写法
        - 平视 → "平视。" / 不写默认平视
        - 俯拍 → "俯拍，[主体]显得渺小/脆弱。"
        - 仰拍 → "仰拍，[主体]显得威严/高大。"
        - 荷兰角 → "略微倾斜的荷兰角，不安感。"
        - 主观视角 → "主观视角，[角色]眼中所见。"

    光线写法
        - 硬光 → "硬光，轮廓分明的阴影，高对比。"
        - 柔光 → "柔光包裹，阴影淡化。"
        - 逆光 → "逆光，人物轮廓发光，面部剪影。"
        - 顶光 → "顶光，眼窝下刻出深影。"
        - 侧光 → "侧光雕塑面部，半明半暗。"

    色调写法
        - 冷色调 → "冷蓝灰色调。" / "冷色调，冷漠孤立。"
        - 暖色调 → "暖金琥珀色调。" / "暖色调，舒适怀旧。"
        - 低饱和 → "低饱和，沉郁写实。"
        - 高对比 → "高对比，深黑与高光。"

    情绪写法
        - 直接用短句收尾，不需要"氛围是..."
"""

# --- Configuration ---

def get_dirs(args):
    project_dir = Path(args.project_dir).resolve() if args.project_dir else Path.cwd()
    script_dir = project_dir / "scripts"  # Aligned with script_workflow.py (plural)
    output_dir = project_dir / "storyboard_output"
    return project_dir, script_dir, output_dir

# --- File Paths (Dynamic based on args) ---
def get_file_paths(output_dir, script_file: Optional[str] = None):
    prefix = ""
    if script_file:
        base = Path(script_file).stem
        safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", base)
        prefix = f"{safe}__"
    return {
        "breakdown": output_dir / f"{prefix}beat_breakdown.md",
        "beat_board": output_dir / f"{prefix}beat_board_prompts.md",
        "sequence_board": output_dir / f"{prefix}sequence_board_prompts.md",
        "motion_prompt": output_dir / f"{prefix}motion_prompts.md",
        "voiceover_table": output_dir / f"{prefix}voiceover_table.md",
        "review_report": output_dir / f"{prefix}review_report.md"
    }

def get_storyboard_table_path(project_dir: Path, script_file: Optional[str] = None) -> Path:
    """Return per-episode storyboard table path if script_file is provided, else global."""
    if script_file:
        base = Path(script_file).stem
        safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", base)
        return project_dir / f"storyboard-table__{safe}.md"
    return project_dir / "storyboard-table.md"


# --- LLM Client ---

class LLMConfig:
    def __init__(self, args=None):
        self.api_key = getattr(args, "api_key", None) or os.environ.get("API_KEY")
        self.api_base = getattr(args, "api_base", None) or os.environ.get("API_BASE", "https://api.openai.com/v1")
        self.model = getattr(args, "model", None) or os.environ.get("MODEL_NAME", "gpt-4o")
        self.api_style = getattr(args, "api_style", None) or os.environ.get("API_STYLE", "openai")  # openai or anthropic

    def validate(self):
        if not self.api_key:
            print("Warning: API_KEY not set. Using dummy mode.")
            return False
        return True

class LLM:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.is_valid = self.config.validate()
        
        if self.is_valid:
            if self.config.api_style == "anthropic":
                try:
                    from anthropic import Anthropic
                    self.client = Anthropic(api_key=self.config.api_key, base_url=self.config.api_base)
                except ImportError:
                    print("Error: anthropic package not installed. Run: pip install anthropic")
                    self.is_valid = False
            else:
                try:
                    from openai import OpenAI
                    self.client = OpenAI(api_key=self.config.api_key, base_url=self.config.api_base)
                except ImportError:
                    print("Error: openai package not installed. Run: pip install openai")
                    self.is_valid = False

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if not self.is_valid:
            return "[DUMMY OUTPUT] LLM not configured or failed to initialize. Please check API_KEY and installed packages."

        try:
            if self.config.api_style == "anthropic":
                content = self._chat_anthropic(messages, temperature)
            else:
                content = self._chat_openai(messages, temperature)
            
            # Post-processing: Strip <think> tags (common in reasoning models like DeepSeek)
            if content:
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            
            return content
        except Exception as e:
            print(f"LLM Error: {e}")
            return f"[ERROR] Failed to generate response: {e}"

    def _chat_openai(self, messages: List[Dict[str, str]], temperature: float) -> str:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            timeout=120  # Set timeout to 120 seconds
        )
        return response.choices[0].message.content

    def _chat_anthropic(self, messages: List[Dict[str, str]], temperature: float) -> str:
        # Anthropic expects system message separate
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                filtered_messages.append(msg)
        
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=4000,
            system=system_msg,
            messages=filtered_messages,
            temperature=temperature,
            timeout=120  # Set timeout to 120 seconds
        )
        return response.content[0].text

# --- Helper Functions ---

def extract_table_names(file_path: Path) -> List[str]:
    """Extract names from the first column of a markdown table."""
    names = []
    if not file_path.exists():
        return names
    
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        in_table = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|"):
                if "---" in stripped:
                    in_table = True
                    continue
                if in_table:
                    parts = [p.strip() for p in stripped.split("|")]
                    # parts[0] is usually empty string before first |
                    if len(parts) > 2:
                        name = parts[1]
                        # Filter out header or example placeholders if generic
                        if name and name != "名称" and name != "示例" and "Name" not in name:
                            names.append(name)
    except Exception as e:
        print(f"Warning: Failed to extract names from {file_path}: {e}")
        
    return names

def parse_sequence_content(content: str) -> List[Dict]:
    """Parse sequence board prompts markdown content."""
    items = []
    lines = content.splitlines()
    
    current_grid = None
    current_panel = None
    current_text = []
    current_chars = ""
    current_scene = ""
    
    # Regex for Grid Header: ## 格1展开...
    grid_re = re.compile(r'^##\s*格(\d+)展开')
    
    # Regex for Panel Header: 1（左上）——【Title】
    # Allow 1 (Left) -- [Title] variations
    panel_re = re.compile(r'^(\d+)\s*[（(].*?[）)]\s*[—\-]+.*')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check Grid
        m_grid = grid_re.match(line)
        if m_grid:
            # Save previous if exists
            if current_grid and current_panel is not None and current_text:
                full_text = " ".join(current_text)
                items.append({
                    "grid": current_grid,
                    "panel": current_panel,
                    "prompt": full_text,
                    "chars": current_chars,
                    "scene": current_scene
                })
                current_panel = None
                current_text = []
                current_chars = ""
                current_scene = ""
            
            current_grid = m_grid.group(1)
            continue
            
        # Check Panel
        m_panel = panel_re.match(line)
        if m_panel:
            # Save previous if exists
            if current_grid and current_panel is not None and current_text:
                full_text = " ".join(current_text)
                items.append({
                    "grid": current_grid,
                    "panel": current_panel,
                    "prompt": full_text,
                    "chars": current_chars,
                    "scene": current_scene
                })
            
            current_panel = m_panel.group(1)
            current_text = []
            current_chars = ""
            current_scene = ""
            
            # Try to extract metadata from header line
            # Extract Chars
            m_chars = re.search(r'出场人物[:：]\s*(.*?)(?:\s+场景[:：]|$)', line)
            if m_chars:
                current_chars = m_chars.group(1).strip()
                
            # Extract Scene
            m_scene = re.search(r'场景[:：]\s*(.*?)(?:\s+出场人物[:：]|$)', line)
            if m_scene:
                current_scene = m_scene.group(1).strip()

            # We skip the header line in the prompt text to keep it clean
            continue
            
        # If inside a panel, collect text
        if current_grid and current_panel is not None:
            if line.startswith("---") or line.startswith("#"):
                # End of section (handled by next grid match too, but this catches end of doc or separators)
                if current_text:
                     full_text = " ".join(current_text)
                     items.append({
                        "grid": current_grid,
                        "panel": current_panel,
                        "prompt": full_text,
                        "chars": current_chars,
                        "scene": current_scene
                     })
                current_panel = None
                current_text = []
                current_chars = ""
                current_scene = ""
            else:
                # Check for metadata fields
                if line.startswith("出场人物：") or line.startswith("出场人物:"):
                    # Extract content after colon
                    parts = re.split(r'[:：]', line, 1)
                    if len(parts) > 1:
                        current_chars = parts[1].strip()
                    continue
                elif line.startswith("场景：") or line.startswith("场景:"):
                    parts = re.split(r'[:：]', line, 1)
                    if len(parts) > 1:
                        current_scene = parts[1].strip()
                    continue
                        
                current_text.append(line)
                
    # Save last one
    if current_grid and current_panel is not None and current_text:
        full_text = " ".join(current_text)
        items.append({
            "grid": current_grid,
            "panel": current_panel,
            "prompt": full_text,
            "chars": current_chars,
            "scene": current_scene
        })
        
    return items

def build_motion_prompt_template(sequence_content: str) -> str:
    items = parse_sequence_content(sequence_content)
    if not items:
        return MOTION_PROMPT_TEMPLATE
    grid_map = {}
    for item in items:
        grid = item.get("grid")
        panel = item.get("panel")
        try:
            grid_i = int(grid)
            panel_i = int(panel)
        except Exception:
            continue
        grid_map.setdefault(grid_i, set()).add(panel_i)
    if not grid_map:
        return MOTION_PROMPT_TEMPLATE
    lines = []
    lines.append("---")
    lines.append("name: motion-prompt-template")
    lines.append("description: Motion Prompt 动态提示词模板。基于 Sequence Board 生成。")
    lines.append("---")
    lines.append("")
    lines.append("# Motion Prompt 模板")
    lines.append("")
    lines.append("[任务指令]")
    lines.append("    读取 sequence-board-prompt.md，为每个 Beat Anchor 生成一组动态提示词：")
    lines.append("    - 1 个关键帧动态提示词（对应九宫格该格）")
    lines.append("    - 展开分镜对应的动态提示词")
    lines.append("")
    for grid in sorted(grid_map.keys()):
        lines.append("---")
        lines.append("")
        lines.append(f"## 格{grid}：[节拍名称]")
        lines.append("")
        lines.append("### 关键帧")
        lines.append(f"{grid}-0: [Motion Prompt]")
        lines.append("")
        lines.append("### 展开")
        for panel in sorted(grid_map[grid]):
            lines.append(f"{grid}-{panel}: [Motion Prompt]")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

def extract_voiceover_lines(content: str) -> str:
    lines = content.strip().splitlines()
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if table_lines:
        rows = []
        for line in table_lines:
            if "---" in line:
                continue
            parts = [p.strip() for p in line.strip().split("|")]
            if len(parts) < 6:
                continue
            voice = parts[5] if len(parts) > 5 else ""
            if voice:
                rows.append(voice)
        if rows:
            return "\n\n".join(rows).strip()
    kept = []
    for line in lines:
        if line.strip().startswith("#"):
            continue
        if line.strip().startswith("|"):
            continue
        if line.strip().startswith("```"):
            continue
        kept.append(line)
    result = "\n".join(kept).strip()
    return result or content.strip()

def normalize_voiceover_lines(content: str, items: List[Dict]) -> str:
    segments = [seg for seg in re.split(r"\n\s*\n", content.strip()) if seg.strip()]
    out = []
    for i, seg in enumerate(segments):
        s = seg.strip()
        if s.startswith("独白：") or s.startswith("独白:"):
            speaker = ""
            if i < len(items):
                raw = items[i].get("chars") or ""
                parts = re.split(r"[，,、\s]+", raw)
                for p in parts:
                    p = p.strip()
                    if p:
                        speaker = p
                        break
            if speaker:
                s = re.sub(r"^独白[:：]\s*", f"{speaker}：", s)
            else:
                s = re.sub(r"^独白[:：]\s*", "旁白：", s)
        out.append(s)
    return "\n\n".join(out)

def update_storyboard_table_file(project_dir: Path, sequence_content: str, script_file: Optional[str] = None):
    """Update storyboard table (per-episode if script_file provided) with parsed prompts."""
    table_path = get_storyboard_table_path(project_dir, script_file=script_file)
    print(f"Updating {table_path.name}...")
    char_path = project_dir / "character-overview.md"
    scene_path = project_dir / "scene-overview.md"
    
    chars = extract_table_names(char_path)
    scenes = extract_table_names(scene_path)
    
    parsed_items = parse_sequence_content(sequence_content)
    
    if not parsed_items:
        print("Warning: No prompts parsed from sequence content.")
        return

    # Prepare new rows
    new_rows = []
    
    # Check if table exists to determine starting ID
    start_id = 1
    existing_content = ""
    
    if table_path.exists():
        existing_content = table_path.read_text(encoding="utf-8")
        # Try to find last ID
        lines = existing_content.strip().splitlines()
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("|") and "---" not in stripped and "编号" not in stripped:
                try:
                    parts = stripped.split("|")
                    if len(parts) > 1 and parts[1].strip().isdigit():
                        start_id = int(parts[1].strip()) + 1
                        break
                except:
                    pass
    else:
        # Create header if not exists
        header = "| 编号 | 出场人物 | 场景 | 分镜提示词 | 视频提示词 |\n| --- | --- | --- | --- | --- |\n"
        title = "# 分镜表\n\n"
        # Include episode hint in title if per-episode
        if script_file:
            base = Path(script_file).stem
            title = f"# 分镜表（{base}）\n\n"
        existing_content = title + header
        write_file(table_path, existing_content)

    for item in parsed_items:
        prompt = item['prompt']
        
        # Use extracted fields if available
        char_str = item.get('chars', '')
        scene_str = item.get('scene', '')
        
        # If empty, fallback to matching
        if not char_str:
            prompt_lower = prompt.lower()
            found_chars = []
            for c in chars:
                if c.lower() in prompt_lower:
                    found_chars.append(c)
            char_str = ", ".join(found_chars) if found_chars else ""
            
        if not scene_str:
            prompt_lower = prompt.lower()
            found_scenes = []
            for s in scenes:
                if s.lower() in prompt_lower:
                    found_scenes.append(s)
            scene_str = ", ".join(found_scenes) if found_scenes else ""
        
        # Clean prompt for table (remove newlines, escape pipes)
        clean_prompt = prompt.replace("\n", " ").replace("|", "\|")
        
        row = f"| {start_id} | {char_str} | {scene_str} | {clean_prompt} | |"
        new_rows.append(row)
        start_id += 1
        
    # Append
    if new_rows:
        # Use a lock if possible, but write_file handles locking if we use it.
        # Here we just append.
        try:
            with open(table_path, "a", encoding="utf-8") as f:
                if existing_content and not existing_content.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(new_rows) + "\n")
            print(f"Successfully added {len(new_rows)} rows to {table_path.name}")
        except Exception as e:
            print(f"Error appending to storyboard table {table_path.name}: {e}")

def update_overviews(project_dir: Path, data: Dict[str, Any]) -> None:
    """Update character and scene overviews with data extracted from storyboard prompts."""
    char_path = project_dir / "character-overview.md"
    scene_path = project_dir / "scene-overview.md"
    
    def update_table(path: Path, title: str, items: List[Dict[str, str]], headers: List[str]):
        header_row = "| " + " | ".join(headers) + " |"
        sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
        
        # Ensure file exists and read content
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                content = ""
        else:
            content = ""
        
        # Normalize trailing newline
        if not content.endswith("\n") and content:
            content += "\n"
        
        lines = content.splitlines() if content else []
        
        # Detect if a header line exists
        header_line_idx = -1
        for i, line in enumerate(lines):
            strip = line.strip()
            if strip.startswith("|"):
                # Consider it a header if it contains first two headers
                if all(h in strip for h in headers[:2]):
                    header_line_idx = i
                    break
        
        if header_line_idx == -1:
            # No valid header found; prepend title + header
            prefix = f"# {title}\n\n{header_row}\n{sep_row}\n"
            content = prefix + content
            lines = content.splitlines()
            header_line_idx = lines.index(header_row)
        
        # Ensure the last column exists (生图提示词)
        if headers[-1] not in lines[header_line_idx]:
            lines[header_line_idx] = lines[header_line_idx].rstrip("| \t") + f" | {headers[-1]} |"
            # Update separator line accordingly
            if header_line_idx + 1 < len(lines) and lines[header_line_idx + 1].strip().startswith("|"):
                sep = lines[header_line_idx + 1].rstrip("| \t")
                # Count columns and pad to match header columns
                current_cols = sep.count("---")
                needed_cols = len(headers)
                if current_cols < needed_cols:
                    extra = " | " + " | ".join(["---"] * (needed_cols - current_cols)) + " |"
                    sep = sep + extra
                else:
                    sep = sep + " | --- |"
                lines[header_line_idx + 1] = sep
            content = "\n".join(lines) + "\n"

        existing_names = set()
        for line in content.splitlines():
            if line.strip().startswith("|") and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) > 2:
                    # | name | desc | ... -> ['', 'name', 'desc', ..., '']
                    name = parts[1]
                    if name and name != headers[0] and "---" not in name:
                        existing_names.add(name)
        
        new_rows = []
        for item in items:
            name = item.get("name", "").strip()
            desc = item.get("description", "").strip()
            prompt = item.get("visual_prompt", "").strip()
            
            if name and name not in existing_names:
                desc = desc.replace("\n", " ").replace("|", "\|")
                prompt = prompt.replace("\n", " ").replace("|", "\|")
                new_rows.append(f"| {name} | {desc} | {prompt} |")
                existing_names.add(name)
        
        if new_rows:
            if not content.endswith("\n"):
                content += "\n"
            content += "\n".join(new_rows) + "\n"
            write_file(path, content)
            print(f"Updated overview: {path.name} (Added {len(new_rows)} items)")

    # Characters
    chars = [{"name": c.get("name"), "description": c.get("description"), "visual_prompt": c.get("visual_prompt")} for c in data.get("characters", [])]
    if chars:
        update_table(char_path, "角色概览", chars, ["角色名", "描述", "生图提示词"])
    
    # Scenes
    scenes = [{"name": c.get("name"), "description": c.get("description"), "visual_prompt": c.get("visual_prompt")} for c in data.get("scenes", [])]
    if scenes:
        update_table(scene_path, "场景概览", scenes, ["场景名", "描述", "生图提示词"])

def parse_motion_content(content: str) -> Dict[str, str]:
    """Parse motion prompts markdown content. Returns dict keyed by 'grid-panel' (e.g. '1-1')."""
    prompts = {}
    # Regex for line: 1-1: prompt text
    # Also handles 1-1： prompt text (Chinese colon)
    # Assumes lines are like "1-1: ..."
    pattern = re.compile(r'^\s*(\d+)-(\d+)\s*[:：]\s*(.*)')
    
    lines = content.splitlines()
    for line in lines:
        m = pattern.match(line)
        if m:
            grid, panel, text = m.groups()
            key = f"{grid}-{panel}"
            prompts[key] = text.strip()
    return prompts

def update_storyboard_table_with_motion(project_dir: Path, sequence_content: str, motion_content: str, script_file: Optional[str] = None):
    """Update storyboard table (per-episode if script_file provided) with motion prompts matching sequence prompts."""
    table_path = get_storyboard_table_path(project_dir, script_file=script_file)
    print(f"Updating {table_path.name} with motion prompts...")
    if not table_path.exists():
        print(f"Warning: {table_path.name} not found. Skipping update.")
        return

    # Parse inputs
    sequence_items = parse_sequence_content(sequence_content) # List of {grid, panel, prompt}
    motion_items = parse_motion_content(motion_content) # Dict { '1-1': 'prompt' }
    
    if not sequence_items:
        print("Warning: No sequence prompts parsed.")
        return

    # Create a map from Sequence Prompt Text -> Motion Prompt Text
    # We use the Grid-Panel relationship to link them.
    # Sequence Item (Grid G, Panel P) <-> Motion Item (G-P)
    
    prompt_map = {} # Cleaned Sequence Prompt -> Cleaned Motion Prompt
    
    for item in sequence_items:
        grid = item['grid']
        panel = item['panel']
        seq_prompt = item['prompt']
        
        motion_key = f"{grid}-{panel}"
        if motion_key in motion_items:
            motion_prompt = motion_items[motion_key]
            
            # Prepare keys for table matching
            # The table stores cleaned sequence prompts
            clean_seq = seq_prompt.replace("\n", " ").replace("|", "\|").strip()
            clean_motion = motion_prompt.replace("\n", " ").replace("|", "\|").strip()
            
            prompt_map[clean_seq] = clean_motion
            
    if not prompt_map:
        print("Warning: No matching motion prompts found for sequence items.")
        return

    # Update Table
    try:
        content = table_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        new_lines = []
        updated_count = 0
        
        for line in lines:
            stripped = line.strip()
            # Check if it's a table row
            if stripped.startswith("|") and "---" not in stripped and "编号" not in stripped:
                parts = stripped.split("|")
                # Parts: [empty, ID, Chars, Scenes, SeqPrompt, MotionPrompt, empty]
                # Index: 0      1   2      3       4          5             6
                # Note: Markdown tables often have leading/trailing pipes.
                # Let's handle splitting carefully.
                
                # Re-split carefully to preserve structure
                # We assume standard formatting: | col1 | col2 | ... |
                
                if len(parts) >= 6:
                    # parts[4] is Sequence Prompt
                    current_seq_cell = parts[4].strip()
                    # We need to match this against our keys.
                    # Exact match might be tricky due to spacing.
                    # Let's try exact match of stripped content.
                    
                    if current_seq_cell in prompt_map:
                        motion_text = prompt_map[current_seq_cell]
                        # Update parts[5] (Video Prompt)
                        parts[5] = f" {motion_text} "
                        updated_count += 1
                        line = "|".join(parts)
            
            new_lines.append(line)
            
        if updated_count > 0:
            write_file(table_path, "\n".join(new_lines))
            print(f"Successfully updated {updated_count} rows in {table_path.name}")
        else:
            print(f"No rows updated in {table_path.name} (no prompt matches found).")
            
    except Exception as e:
        print(f"Error updating storyboard table with motion prompts: {e}")

def ensure_dirs(script_dir, output_dir):
    script_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

def get_script_content(script_dir, script_file: Optional[str] = None) -> Optional[str]:
    # If a specific script file is provided, use it (absolute or relative to scripts/)
    if script_file:
        sf_path = Path(script_file)
        if not sf_path.is_absolute():
            sf_path = script_dir / script_file
        if not sf_path.exists():
            print(f"Error: Script file not found: {sf_path}")
            return None
        print(f"Using script file: {sf_path.name}")
        try:
            return sf_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading script file: {e}")
            return None
    # Fallback: first .md in scripts/
    files = sorted(list(script_dir.glob("*.md")))
    if not files:
        print(f"Error: No .md files found in {script_dir}")
        return None

def parse_episode_from_script_file(script_file: Optional[str]) -> Optional[str]:
    if not script_file:
        return None
    base = Path(script_file).stem
    m = re.search(r"Episode[-_]?(\d+)", base, re.IGNORECASE)
    if not m:
        return None
    return str(int(m.group(1)))
    print(f"Using script file: {files[0].name}")
    try:
        return files[0].read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading script file: {e}")
        return None

def write_file(path: Path, content: str):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Infer project lock
        lock_path = None
        for parent in path.resolve().parents:
            if (parent / "storyboard_output").exists() or (parent / "scripts").exists():
                 lock_path = parent / ".project_lock"
                 break
        
        if lock_path:
            lock = filelock.FileLock(str(lock_path), timeout=60)
            with lock:
                path.write_text(content, encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
            
        print(f"Generated: {path}")
    except Exception as e:
        print(f"Error writing to {path}: {e}")

def read_output_file(path: Path) -> Optional[str]:
    if not path.exists():
        print(f"Error: File not found: {path}")
        return None
    return path.read_text(encoding="utf-8")

def get_system_prompt(role: str) -> str:
    # Embedded system prompts for simplicity
    if role == "storyboard-artist":
        return "You are an expert AI Storyboard Artist. Your goal is to visualize scripts into clear, cinematic, and consistent storyboard prompts."
    elif role == "director":
        return "You are a Visionary Film Director. Your goal is to ensure the storyboard aligns with the narrative, visual style, and emotional tone."
    elif role == "animator":
        return "You are a Technical Animator. Your goal is to translate static storyboards into dynamic motion prompts for AI video generation."
    return "You are a helpful assistant."

# --- Commands ---

def cmd_init(args):
    project_dir, script_dir, output_dir = get_dirs(args)
    print(f"Initializing project structure in {project_dir}...")
    ensure_dirs(script_dir, output_dir)
    
    example_script = script_dir / "example_script.md"
    if not example_script.exists():
        example_script.write_text("# Example Script\n\n[Scene: A dark alleyway. Rain pours down.]\n\nDETECTIVE SMITH (V.O.): It was a night like any other...", encoding="utf-8")
        print(f"Created {example_script.name}")
    
    print("Initialization complete.")

def cmd_status(args):
    project_dir, script_dir, output_dir = get_dirs(args)
    print(f"--- Project Status ({project_dir}) ---")
    scripts = sorted(list(script_dir.glob("*.md")))
    if scripts:
        print(f"Scripts: {[p.name for p in scripts]}")
    else:
        print("Scripts: [MISSING]")
    outputs = sorted(list(output_dir.glob("*.md")))
    if outputs:
        print(f"Outputs: {[p.name for p in outputs]}")
    else:
        print("Outputs: [MISSING]")

def cmd_breakdown(args):
    print("Generating Beat Breakdown...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    grid_count, panels_per_grid = normalize_sequence_counts(
        getattr(args, "sequence_grids", None),
        getattr(args, "sequence_panels", None)
    )
    
    script_content = get_script_content(script_dir, script_file=script_file)
    if not script_content:
        print("Error: No script found in scripts/ directory.")
        return

    prompt = f"""
Task: Generate a Beat Breakdown for the provided script.

[Input Script]
{script_content}

[Methodology]
{STORYBOARD_PLAYBOOK}

[Template]
{BEAT_BREAKDOWN_TEMPLATE}

Instructions:
1. Analyze the script to identify key narrative beats.
2. Target storyboard count is {grid_count * panels_per_grid} shots ({grid_count} grids × {panels_per_grid} panels). If the target count is low, merge adjacent beats into larger narrative segments so the full story arc is covered.
3. Select exactly {grid_count} anchor beats for the Beat Board, covering beginning, development, climax, and resolution.
4. If grid_count < 9, leave unused grid slots as “占位” and mark them as non-anchors.
5. Fill out the Beat Breakdown Template.
6. 输出内容必须为中文。
7. Output ONLY the filled markdown content.
"""
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": get_system_prompt("storyboard-artist")},
        {"role": "user", "content": prompt}
    ])
    
    write_file(files['breakdown'], response)

def cmd_beatboard(args):
    print("Generating Beat Board Prompts...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    grid_count, panels_per_grid = normalize_sequence_counts(
        getattr(args, "sequence_grids", None),
        getattr(args, "sequence_panels", None)
    )
    
    breakdown_content = read_output_file(files['breakdown'])
    if not breakdown_content and not script_file:
        return

    if breakdown_content:
        prompt = f"""
Task: Generate Beat Board Prompts based on the Beat Breakdown.

[Input Breakdown]
{breakdown_content}

[Methodology]
{STORYBOARD_PLAYBOOK}

[Image Prompt Guide]
{GEMINI_IMAGE_PROMPT_GUIDE}

[Template]
{BEAT_BOARD_TEMPLATE}

Instructions:
1. Read the Beat Breakdown and focus on the selected anchor beats.
2. The target storyboard count is {grid_count * panels_per_grid} shots. If grid_count < 9, compress the full story into the first {grid_count} panels by merging adjacent beats; remaining panels must be placeholders with no new plot.
3. Generate a 3x3 Beat Board prompt description following the template.
4. Ensure character and visual consistency across all panels.
5. 输出内容必须为中文。
6. Output ONLY the filled markdown content.
"""
    elif script_file:
        script_content = get_script_content(script_dir, script_file=script_file)
        if not script_content:
            return
        prompt = f"""
Task: Generate Beat Board Prompts directly from the provided script.

[Input Script]
{script_content}

[Methodology]
{STORYBOARD_PLAYBOOK}

[Image Prompt Guide]
{GEMINI_IMAGE_PROMPT_GUIDE}

[Template]
{BEAT_BOARD_TEMPLATE}

Instructions:
1. Analyze the script and select exactly {grid_count} anchor beats that cover the full story arc.
2. The target storyboard count is {grid_count * panels_per_grid} shots. If grid_count < 9, compress the full story into the first {grid_count} panels by merging adjacent beats; remaining panels must be placeholders with no new plot.
3. Generate a 3x3 Beat Board prompt description following the template.
4. Ensure character and visual consistency across all panels.
5. 输出内容必须为中文。
6. Output ONLY the filled markdown content.
"""
    else:
        return
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": get_system_prompt("storyboard-artist")},
        {"role": "user", "content": prompt}
    ])
    
    write_file(files['beat_board'], response)

def cmd_sequence(args):
    print("Generating Sequence Board Prompts...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    grid_count, panels_per_grid = normalize_sequence_counts(
        getattr(args, "sequence_grids", None),
        getattr(args, "sequence_panels", None)
    )
    sequence_template = build_sequence_board_template(grid_count, panels_per_grid)
    
    beat_board_content = read_output_file(files['beat_board'])
    if not beat_board_content and not script_file:
        return

    if beat_board_content:
        prompt_template = """
Task: Generate Sequence Board Prompts based on the Beat Board.

[Input Beat Board]
__INPUT_CONTENT__

[Methodology]
__METHODOLOGY__

[Image Prompt Guide]
__IMAGE_PROMPT_GUIDE__

[Template]
__TEMPLATE__

Instructions:
1. For the first {grid_count} Beat Board panels, expand each into a {panels_per_grid}-panel sequence (Sequence Board).
2. If grid_count < 9, merge adjacent beats from the Beat Board so that the {grid_count} grids still cover the full story arc from beginning to resolution.
3. Maintain visual consistency with the source panel.
4. Describe the action/motion progression within the {panels_per_grid} panels.
5. 输出内容必须为中文。
6. Output the filled Markdown content FIRST.
7. Only output panels for 格1-格{grid_count}.

[Extra Requirement]
AFTER the Markdown content, output a JSON block containing the characters and scenes used in the storyboard.
Format:
```json
{
  "characters": [
    {"name": "Name", "description": "Brief description", "visual_prompt": "Visual prompt in Chinese"}
  ],
  "scenes": [
    {"name": "Name", "description": "Brief description", "visual_prompt": "Visual prompt in Chinese"}
  ]
}
```
要求：JSON 内 name、description、visual_prompt 均使用中文。
"""
        prompt = prompt_template.replace("{grid_count}", str(grid_count)) \
                                .replace("{panels_per_grid}", str(panels_per_grid)) \
                                .replace("__INPUT_CONTENT__", beat_board_content) \
                                .replace("__METHODOLOGY__", STORYBOARD_PLAYBOOK) \
                                .replace("__IMAGE_PROMPT_GUIDE__", GEMINI_IMAGE_PROMPT_GUIDE) \
                                .replace("__TEMPLATE__", sequence_template)
    elif script_file:
        script_content = get_script_content(script_dir, script_file=script_file)
        if not script_content:
            return
        prompt_template = """
Task: Generate Sequence Board Prompts directly from the provided script.

[Input Script]
__INPUT_CONTENT__

[Methodology]
__METHODOLOGY__

[Image Prompt Guide]
__IMAGE_PROMPT_GUIDE__

[Template]
__TEMPLATE__

Instructions:
1. Identify {grid_count} anchor beats and for each, expand it into a {panels_per_grid}-panel sequence (Sequence Board).
2. If grid_count < 9, merge adjacent story beats so that the {grid_count} grids still cover the full story arc from beginning to resolution.
3. Ensure visual consistency across sequences as if sourced from unified Beat Board.
4. Describe the action/motion progression within the {panels_per_grid} panels.
5. 输出内容必须为中文。
6. Output the filled Markdown content FIRST.
7. Only output panels for 格1-格{grid_count}.

[Extra Requirement]
AFTER the Markdown content, output a JSON block containing the characters and scenes used in the storyboard.
Format:
```json
{
  "characters": [
    {"name": "Name", "description": "Brief description", "visual_prompt": "Visual prompt in Chinese"}
  ],
  "scenes": [
    {"name": "Name", "description": "Brief description", "visual_prompt": "Visual prompt in Chinese"}
  ]
}
```
要求：JSON 内 name、description、visual_prompt 均使用中文。
"""
        prompt = prompt_template.replace("{grid_count}", str(grid_count)) \
                                .replace("{panels_per_grid}", str(panels_per_grid)) \
                                .replace("__INPUT_CONTENT__", script_content) \
                                .replace("__METHODOLOGY__", STORYBOARD_PLAYBOOK) \
                                .replace("__IMAGE_PROMPT_GUIDE__", GEMINI_IMAGE_PROMPT_GUIDE) \
                                .replace("__TEMPLATE__", sequence_template)
    else:
        return
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": get_system_prompt("storyboard-artist")},
        {"role": "user", "content": prompt}
    ])
    
    # Extract and process JSON
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            data = json.loads(json_str)
            # update_overviews(project_dir, data) # Disabled in favor of strict extraction via cmd_extract
            
            # Remove JSON block but check if it leaves content empty
            cleaned_response = response.replace(json_match.group(0), "").strip()
            if cleaned_response:
                response = cleaned_response
            else:
                print("Warning: Removing JSON block would result in empty content. Keeping original response (likely missing markdown).")
    except Exception as e:
        print(f"Warning: Failed to extract character/scene JSON: {e}")
    
    if not response:
        print("Error: Generated sequence board content is empty.")

    write_file(files['sequence_board'], response)
    
    # Auto-update storyboard table (per-episode)
    try:
        update_storyboard_table_file(project_dir, response, script_file=script_file)
    except Exception as e:
        print(f"Error updating storyboard table: {e}")

def cmd_motion(args):
    print("Generating Motion Prompts...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    
    sequence_content = read_output_file(files['sequence_board'])
    if not sequence_content and not script_file:
        return

    if sequence_content:
        motion_template = build_motion_prompt_template(sequence_content)
        prompt_template = """
Task: Generate Motion Prompts based on the Sequence Board.

[Input Sequence Board]
__INPUT_CONTENT__

[Methodology]
__METHODOLOGY__

[Template]
__TEMPLATE__

Instructions:
1. Extract the key visual elements and actions from the Sequence Board.
2. Generate motion prompts for video generation tools (Runway/Kling/Pika).
3. Follow the Motion Prompt Methodology for camera movement and action description.
4. 输出内容必须为中文。
5. Output ONLY the filled markdown content.
"""
        prompt = prompt_template.replace("__INPUT_CONTENT__", sequence_content) \
                                .replace("__METHODOLOGY__", MOTION_METHODOLOGY) \
                                .replace("__TEMPLATE__", motion_template)
    elif script_file:
        script_content = get_script_content(script_dir, script_file=script_file)
        if not script_content:
            return
        prompt_template = """
Task: Generate Motion Prompts directly from the provided script.

[Input Script]
__INPUT_CONTENT__

[Methodology]
__METHODOLOGY__

[Template]
__TEMPLATE__

Instructions:
1. Identify key visual elements and actions from the script aligned to 9 anchor beats.
2. Generate motion prompts for video generation tools (Runway/Kling/Pika).
3. Follow the Motion Prompt Methodology for camera movement and action description.
4. 输出内容必须为中文。
5. Output ONLY the filled markdown content.
"""
        prompt = prompt_template.replace("__INPUT_CONTENT__", script_content) \
                                .replace("__METHODOLOGY__", MOTION_METHODOLOGY) \
                                .replace("__TEMPLATE__", MOTION_PROMPT_TEMPLATE)
    else:
        return
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": get_system_prompt("animator")},
        {"role": "user", "content": prompt}
    ])
    
    write_file(files['motion_prompt'], response)

    # Auto-update storyboard table with motion prompts (per-episode)
    if sequence_content:
        try:
            update_storyboard_table_with_motion(project_dir, sequence_content, response, script_file=script_file)
        except Exception as e:
            print(f"Error updating storyboard table with motion prompts: {e}")

def cmd_voiceover(args):
    print("Generating Voiceover Table...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    
    sequence_content = read_output_file(files['sequence_board'])
    if not sequence_content and not script_file:
        return
    if not sequence_content:
        return
    
    script_content = get_script_content(script_dir, script_file=script_file)
    if not script_content:
        return
    
    items = parse_sequence_content(sequence_content)
    if not items:
        print("Error: No sequence items parsed.")
        return
    
    episode = parse_episode_from_script_file(script_file)
    episode_text = f"第{episode}集" if episode else "本集"
    
    panel_lines = []
    for idx, item in enumerate(items, 1):
        grid = str(item.get("grid", "")).strip()
        panel = str(item.get("panel", "")).strip()
        panel_id = f"{grid}-{panel}".strip("-")
        chars = item.get("chars") or "未填写"
        scene = item.get("scene") or "未填写"
        prompt = item.get("prompt", "")
        panel_lines.append(f"{idx}. 画面编号: {panel_id} | 出场人物: {chars} | 场景: {scene} | 画面提示词: {prompt}")
    panel_list = "\n".join(panel_lines)
    
    prompt = f"""
Task: Generate voiceover lines for {episode_text} based on the script and sequence board panels.

[Input Script]
{script_content}

[Sequence Panels]
{panel_list}

Instructions:
1. 配音顺序必须与面板列表顺序一致。
2. 配音内容默认采用“角色名：”形式，只有全知视角才用“旁白：”。
3. 禁止使用“独白：”前缀。
4. 禁止使用拟音与群像。
5. 配音内容必须以“角色名：”或“旁白：”开头。
6. 角色名应来自脚本或画面出场人物。
7. 配音应有画面感与情绪推进，字数可比对白更完整。
8. 每个画面只输出配音内容本身，不要编号、不加表头、不加说明。
9. 多条配音之间用一个空行分隔。
10. 输出格式示例：
{VOICEOVER_TABLE_TEMPLATE}
"""
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": get_system_prompt("storyboard-artist")},
        {"role": "user", "content": prompt}
    ])

    cleaned_response = extract_voiceover_lines(response)
    normalized_response = normalize_voiceover_lines(cleaned_response, items)
    write_file(files['voiceover_table'], normalized_response)

def cmd_extract(args):
    print("Extracting Character and Scene Overviews from Sequence Board...")
    project_dir, script_dir, output_dir = get_dirs(args)
    script_file = getattr(args, 'script_file', None)
    files = get_file_paths(output_dir, script_file=script_file)
    
    sequence_content = read_output_file(files['sequence_board'])
    if not sequence_content:
        print(f"Error: No sequence board content found for {script_file or 'default'}")
        return

    # Regex extraction for strict name compliance
    # Match "出场人物：Name" or "出场人物: Name"
    char_matches = re.findall(r"出场人物[：:]\s*(.*?)(?:\n|$)", sequence_content)
    # Match "场景：Name" or "场景: Name"
    scene_matches = re.findall(r"场景[：:]\s*(.*?)(?:\n|$)", sequence_content)

    # Deduplicate and split by comma
    final_chars = set()
    for c in char_matches:
        # Split by Chinese comma, English comma, or Dunhao (、)
        parts = re.split(r'[，,、]', c)
        for p in parts:
            p = p.strip()
            if p and p.lower() != "无" and p.lower() != "none":
                final_chars.add(p)
    
    final_scenes = set()
    for s in scene_matches:
        parts = re.split(r'[，,、]', s)
        for p in parts:
            p = p.strip()
            if p:
                final_scenes.add(p)
                
    final_chars_list = sorted(list(final_chars))
    final_scenes_list = sorted(list(final_scenes))

    print(f"Found characters: {final_chars_list}")
    print(f"Found scenes: {final_scenes_list}")

    if not final_chars_list and not final_scenes_list:
        print("No characters or scenes found via regex to extract.")
        return
        
    prompt_template = """
Task: Generate Descriptions and Visual Prompts for the following specific Characters and Scenes based on the content.

[Target Characters]
__TARGET_CHARACTERS__

[Target Scenes]
__TARGET_SCENES__

[Input Sequence Board]
__INPUT_CONTENT__

Instructions:
1. For each character in the [Target Characters] list:
   - Generate a "description" (summary of appearance/role based on context).
   - Generate a "visual_prompt" (keywords for image generation, comma-separated).

2. For each scene in the [Target Scenes] list:
   - Generate a "description" (summary of environment based on context).
   - Generate a "visual_prompt" (keywords for image generation).

3. 输出内容全部使用中文（description 与 visual_prompt 也必须为中文）。
4. Output the result in JSON format using the names as KEYS.

Format:
```json
{
  "characters": {
    "Name1": {"description": "...", "visual_prompt": "..."},
    "Name2": {"description": "...", "visual_prompt": "..."}
  },
  "scenes": {
    "Scene1": {"description": "...", "visual_prompt": "..."},
    "Scene2": {"description": "...", "visual_prompt": "..."}
  }
}
```
"""
    
    prompt = prompt_template.replace("__TARGET_CHARACTERS__", json.dumps(final_chars_list, ensure_ascii=False)) \
                            .replace("__TARGET_SCENES__", json.dumps(final_scenes_list, ensure_ascii=False)) \
                            .replace("__INPUT_CONTENT__", sequence_content)
    
    llm = LLM(config=LLMConfig(args))
    response = llm.chat([
        {"role": "system", "content": "You are a data extraction assistant. Output only JSON."},
        {"role": "user", "content": prompt}
    ])
    
    data = {"characters": [], "scenes": []}
    
    # Handle Dummy Mode or Error
    if response.startswith("[DUMMY OUTPUT]") or response.startswith("[ERROR]"):
        print("LLM in Dummy Mode or Error state. Using extracted names with placeholder descriptions.")
        for name in final_chars_list:
            data["characters"].append({
                "name": name,
                "description": "待补充描述 (AI未连接)",
                "visual_prompt": "portrait, cinematic lighting"
            })
        for name in final_scenes_list:
            data["scenes"].append({
                "name": name,
                "description": "待补充描述 (AI未连接)",
                "visual_prompt": "cinematic environment, 8k"
            })
    else:
        try:
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                raw_data = json.loads(json_str)
                
                # Strict Name Mapping
                raw_chars = raw_data.get("characters", {})
                for name in final_chars_list:
                    # Try exact match
                    info = raw_chars.get(name)
                    if not info:
                        # Try case-insensitive match
                        for k, v in raw_chars.items():
                            if k.lower() == name.lower():
                                info = v
                                break
                    
                    info = info or {}
                    data["characters"].append({
                        "name": name,
                        "description": info.get("description", "AI未生成描述"),
                        "visual_prompt": info.get("visual_prompt", "")
                    })
                    
                raw_scenes = raw_data.get("scenes", {})
                for name in final_scenes_list:
                    info = raw_scenes.get(name)
                    if not info:
                        for k, v in raw_scenes.items():
                            if k.lower() == name.lower():
                                info = v
                                break
                                
                    info = info or {}
                    data["scenes"].append({
                        "name": name,
                        "description": info.get("description", "AI未生成描述"),
                        "visual_prompt": info.get("visual_prompt", "")
                    })
                    
                print("Successfully mapped extracted names to AI descriptions.")
            else:
                # Fallback to raw JSON parsing
                try:
                    # If LLM ignored the format and returned a list, we can't map strictly by key, 
                    # but we can try to use it if it looks like the old format.
                    # However, to be safe and follow user instruction "don't change names", 
                    # we should probably default to placeholders if format is wrong.
                    print("Warning: Could not find JSON block in LLM response. Using placeholders.")
                    for name in final_chars_list:
                        data["characters"].append({"name": name, "description": "解析失败", "visual_prompt": ""})
                    for name in final_scenes_list:
                        data["scenes"].append({"name": name, "description": "解析失败", "visual_prompt": ""})
                except:
                    print("Error: JSON parsing failed.")
        except Exception as e:
            print(f"Error processing extraction: {e}")
            return

    update_overviews(project_dir, data)

def cmd_review(args):
    print("Review functionality is not yet fully implemented in standalone mode.")
    print("In a full implementation, this would check consistency between outputs.")

def cmd_auto(args):
    print("Starting One-Click Storyboard Generation...")
    
    # 1. Breakdown
    print("\n[1/5] Generating Beat Breakdown...")
    cmd_breakdown(args)
    
    # 2. Beat Board
    print("\n[2/5] Generating Beat Board Prompts...")
    cmd_beatboard(args)
    
    # 3. Sequence Board
    print("\n[3/5] Generating Sequence Board Prompts...")
    cmd_sequence(args)

    # 3.5 Extract Overviews (Strict Mode)
    print("\n[3.5/5] Extracting Character/Scene Overviews...")
    try:
        cmd_extract(args)
    except Exception as e:
        print(f"Warning: Overview extraction failed: {e}")
    
    # 4. Motion Prompts
    print("\n[4/5] Generating Motion Prompts...")
    cmd_motion(args)

    # 5. Voiceover Table
    print("\n[5/5] Generating Voiceover Table...")
    cmd_voiceover(args)
    
    print("\nAll steps completed successfully!")

def main():
    # Global API Arguments parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--api-key", help="API Key (overrides env API_KEY)", default=argparse.SUPPRESS)
    parent_parser.add_argument("--api-base", help="API Base URL (overrides env API_BASE)", default=argparse.SUPPRESS)
    parent_parser.add_argument("--model", help="Model Name (overrides env MODEL_NAME)", default=argparse.SUPPRESS)
    parent_parser.add_argument("--api-style", choices=["openai", "anthropic"], help="API Style (overrides env API_STYLE)", default=argparse.SUPPRESS)
    parent_parser.add_argument("--project-dir", help="Project Directory", default=None)
    parent_parser.add_argument("--sequence-grids", type=int, help="Sequence grid count (1-9)", default=None)
    parent_parser.add_argument("--sequence-panels", type=int, help="Panels per sequence grid (2-6)", default=None)

    parser = argparse.ArgumentParser(description="AI Storyboard Workflow Standalone", parents=[parent_parser])
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("init", help="Initialize project structure")
    subparsers.add_parser("status", help="Show project status")
    
    parser_breakdown = subparsers.add_parser("breakdown", help="Generate Beat Breakdown")
    parser_breakdown.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")

    parser_beatboard = subparsers.add_parser("beatboard", help="Generate Beat Board Prompts")
    parser_beatboard.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")
    parser_sequence = subparsers.add_parser("sequence", help="Generate Sequence Board Prompts")
    parser_sequence.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")
    parser_motion = subparsers.add_parser("motion", help="Generate Motion Prompts")
    parser_motion.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")
    
    parser_extract = subparsers.add_parser("extract", help="Extract Character and Scene Overviews")
    parser_extract.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")

    parser_voiceover = subparsers.add_parser("voiceover", help="Generate Voiceover Table")
    parser_voiceover.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")
    parser_dubbing = subparsers.add_parser("dubbing", help="Generate Voiceover Table")
    parser_dubbing.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")
    
    parser_auto = subparsers.add_parser("auto", help="Run full storyboard workflow sequentially")
    parser_auto.add_argument("--script-file", help="Specify script file (absolute or under scripts/)")

    subparsers.add_parser("review", help="Review outputs")
    
    args = parser.parse_args()
    
    if args.command == "init":
        cmd_init(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "breakdown":
        cmd_breakdown(args)
    elif args.command == "beatboard":
        cmd_beatboard(args)
    elif args.command == "sequence":
        cmd_sequence(args)
    elif args.command == "motion":
        cmd_motion(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command in ["voiceover", "dubbing"]:
        cmd_voiceover(args)
    elif args.command == "auto":
        cmd_auto(args)
    elif args.command == "review":
        cmd_review(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
