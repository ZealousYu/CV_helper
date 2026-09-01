# 简历面试助手 — 交互 Demo

## 推荐打开方式（已接后端）

先启动后端，再浏览器访问：

```bash
cd CV_Helper/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

打开：**http://127.0.0.1:8000/**  

侧边栏应显示 `API · mock`（或接 Key 后为 `openai`）。经历 / 面试树 / 知识汇总均读写 SQLite，**刷新页面不丢**。

也可直接打开本目录 `standalone.html`（会请求 `http://127.0.0.1:8000`）；若提示未连接，先确认 uvicorn 已启动。

## 建议体验路径

1. **① 经历库** — 手动添加/编辑（写入后端）
2. **③ 模拟面试** — 开始提问 → 作答 → 深挖 → 标记 → 加入知识汇总
3. **刷新浏览器** — 确认追问树与知识条目还在
4. **④ 笔记本 / ⑤ 知识汇总** — 看归档结果

## 说明

- `src/` React 版仍为早期结构；当前以 `standalone.html` + 后端为准。
- 接真实大模型：见 `../docs/接真实大模型.md`。
