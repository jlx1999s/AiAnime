
from storyboard_workflow import parse_sequence_content
import json

content = """
## 格1展开——【测试】

1（左上）——【逼仄空间】
出场人物：李道玄
场景：昏暗的出租屋客厅
视角：特写
重点：黑眼圈

2（右上）——【测试2】
出场人物：李道玄
场景：卧室
视角：全景
重点：凌乱
"""

items = parse_sequence_content(content)
print(json.dumps(items, ensure_ascii=False, indent=2))
