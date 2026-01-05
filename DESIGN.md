# AI 漫剧制作 Web 平台设计方案

## 1. 项目概述
本项目旨在开发一个 AI 辅助的漫剧（漫画/动画视频）制作平台。用户可以通过剧本描述，利用 AI 生成分镜图、角色、场景，并最终合成视频片段。

## 2. 核心功能 (基于 UI 分析)

### 2.1 顶部导航栏 (Header)
- **项目信息**: 显示当前项目名称（如“守墓五年...”）。
- **全局设置**:
  - 风格选择 (如：日漫, 韩漫, 写实)。
  - 时代/背景设置。
  - 模型配置 (选择 SD 模型, LoRA 等)。
- **生成记录**: 查看历史生成任务。
- **用户中心**: 头像及设置。

### 2.2 主要工作区 (Main Workspace - 剧本/分镜列表)
核心区域是一个垂直滚动的列表，每一行代表一个分镜(Shot/Scene)。
- **序号**: 分镜顺序。
- **剧本/提示词区域**:
  - **视觉描述**: 详细描述画面内容、镜头角度、光影等 (Prompt)。
  - **台词**: 角色的对白。
  - **音频**: 音效或配音设置。
- **资产槽位 (Assets Slots)**:
  - **出场人物**: 从右侧侧边栏拖拽或选择当前分镜的人物。
  - **场景**: 选择背景图片。
  - **道具**: 关键道具。
- **生成结果**:
  - **分镜图 (Storyboard)**: AI 生成的静态图预览。
  - **视频 (Video)**: 图生视频的结果。
- **操作**: 生成按钮、删除、上下移动。

### 2.3 右侧资源侧边栏 (Asset Sidebar)
- **Tabs**: 角色 (Characters), 场景 (Scenes), 道具 (Props)。
- **角色管理**:
  - **作品中角色**: 当前项目已选用的角色。
  - **全部可选角色**: 角色库。
  - **新建角色**: 上传参考图或通过 AI 生成新角色 (训练 LoRA 或保持一致性)。
- **批量操作**: 批量生成按钮。

## 3. 技术栈 (推荐)

### 前端
- **框架**: React (Vite) + TypeScript
- **UI 库**: Tailwind CSS + Shadcn/UI (用于快速构建现代化界面)
- **状态管理**: Zustand (轻量级，适合管理复杂的剧本状态)
- **拖拽库**: dnd-kit 或 react-beautiful-dnd (用于资产拖拽)

### 后端 (模拟/建议)
- **API**: Python (FastAPI) - 方便对接 AI 模型
- **数据库**: PostgreSQL (存储项目、剧本、关联关系)
- **AI 服务**:
  - 图像生成: Stable Diffusion WebUI API / ComfyUI
  - 视频生成: Stable Video Diffusion (SVD) / Runway API
  - LLM: OpenAI / Claude / Local LLM (用于剧本扩写)

## 4. 数据结构设计 (前端 Types)

```typescript
// 分镜单元
interface Shot {
  id: string;
  order: number;
  script: {
    visualPrompt: string; // 画面描述
    dialogue: string;     // 台词
    audioPrompt?: string; // 音效描述
  };
  assets: {
    characterIds: string[];
    sceneId?: string;
    propIds?: string[];
  };
  generated: {
    imageUrl?: string;    // 分镜图 URL
    videoUrl?: string;    // 视频 URL
    status: 'idle' | 'generating' | 'completed' | 'failed';
  };
}

// 角色
interface Character {
  id: string;
  name: string;
  avatarUrl: string;
  tags: string[]; // 用于生成的一致性 Prompt
}

// 项目
interface Project {
  id: string;
  name: string;
  style: string;
  shots: Shot[];
}
```

## 5. 开发计划
1.  **初始化项目**: Vite + React + TS + Tailwind.
2.  **构建布局**: Header + Sidebar + Main Content 骨架。
3.  **实现分镜列表**: 开发复杂的列表行组件。
4.  **实现资源管理**: 右侧侧边栏及 mock 数据。
5.  **状态管理**: 使用 Zustand 串联数据。
