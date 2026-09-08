# 简历面试助手 — 后端

## 启动

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 可选：填入 LLM_API_KEY
uvicorn app.main:app --reload --port 8000
```

- **前端 Demo（推荐）**：http://127.0.0.1:8000/  → 自动跳到 `/ui/standalone.html`
- API 文档：http://127.0.0.1:8000/docs  
- 健康检查：http://127.0.0.1:8000/api/health  

未配置 `LLM_API_KEY` 时自动使用 **MockLLM**。接真模型见 [接真实大模型](../docs/接真实大模型.md)。

## 目录

```
app/
  main.py          # 入口、CORS、挂载 /ui
  config.py        # 环境变量
  database.py      # SQLite
  models.py        # ORM
  schemas.py       # 请求/响应
  routers/         # experiences / interview / knowledge
  services/llm.py  # Mock / OpenAI 兼容
```
