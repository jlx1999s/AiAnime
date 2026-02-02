
import re

def find_last_batch(plot_breakdown: str):
    matches = list(re.finditer(r"^###\s*第(\d+)批（第(\d+)-(\d+)章）\s*$", plot_breakdown, re.M))
    if not matches:
        return None
    m = matches[-1]
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

content = """# 剧情拆解

**小说名称**：《我的小说》
**小说类型**：历史，奇幻

---

## 剧情列表

# 剧情拆解

**小说名称**：《箱子里的大明》（根据内容推断，原名《我有一个大明造景箱》或类似）
**小说类型**：玄幻/都市/种田/幕后流

---

## 剧情列表

# 剧情拆解

**小说名称**：《<小说名>》（注：根据原文推测为《箱子里的大明》或类似题材，此处保留占位符或填入《箱子里的大明》）
**小说类型**：<玄幻/历史/种田>

---

## 剧情列表

### 第1批（第1-6章）

【剧情1】...

### 第1批（第1-6章）

【剧情17】...

### 第2批（第7-12章）

【剧情33】...
"""

print(find_last_batch(content))
