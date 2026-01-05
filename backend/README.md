# MochiAni Backend

这是一个基于 FastAPI 的后端服务，为前端提供 API 支持。

## 目录结构

- `main.py`: 后端入口，包含 API 路由定义。
- `models.py`: 数据模型 (Pydantic models)，与前端数据结构对应。
- `requirements.txt`: Python 依赖包列表。
- `Dockerfile`: Docker 构建文件。

## 如何运行

### 方式一：直接运行 (推荐)

您的环境已安装 Python 3.11。

1.  **安装依赖** (如果尚未安装):
    ```bash
    py -m pip install -r requirements.txt
    ```

2.  **启动服务器**:
    ```bash
    py main.py
    ```
    或者使用 uvicorn:
    ```bash
    py -m uvicorn main:app --reload
    ```

### 方式二：使用 Docker

如果您安装了 Docker Desktop，可以直接运行：

```bash
docker-compose up --build
```

服务器将在 `http://localhost:8000` 启动。

## 验证

服务器启动后，访问 `http://localhost:8000/docs` 查看自动生成的 API 文档。

## 前端集成

前端 `index.html` 目前使用 Mock 数据。要接入此后端：

1.  确保后端已启动。
2.  修改 `index.html` 第 132 行：`const USE_MOCK = false;`。
