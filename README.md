# 简历面试助手（CV Helper）

围绕**简历经历**做结构化模拟面试：可生长的**追问树**、自动归档成笔记本 / 知识汇总，并支持真实面经转写复盘。

> 核心不是「多一个 ChatGPT 窗口」，而是「练完变成带索引的面试资料」。

## 快速开始

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 可选：填 LLM_API_KEY 接真模型
uvicorn app.main:app --reload --port 8000
```

浏览器打开：http://127.0.0.1:8000/ （跳到 `/ui/standalone.html`）

接真实大模型说明：`docs/接真实大模型.md`  
过程跟踪（面试可讲）：`docs/项目搭建过程跟踪.md`  
**公网部署**：`docs/部署上线.md`（Docker / Render / Railway，建议设 `ACCESS_PASSWORD`）

## 当前能力

| 模块 | 说明 |
|------|------|
| 经历库 | 手填 / PDF·Word 解析导入 |
| 文字准备 | 打字打磨追问树（深挖/换角度/发散） |
| **语音面试** | 浏览器朗读 + 听写；答案写入同一追问树 |
| 笔记本 + 知识汇总 | 标记待练习、复习对比、跨经历知识点 |
| 真实面经 | 粘贴转写 → 抽问答 → 弱答标红 + 四维分 |
| 岗位匹配 | JD vs 经历库 |

融合路线见 `docs/竞品对照与融合路线.md`。

默认 `LLM_PROVIDER=mock`；配置 OpenAI 兼容 Key（如 DeepSeek）后切真模型。

## 技术栈

- 后端：FastAPI + SQLite + LLM Provider 抽象（Mock / OpenAI 兼容）
- 前端：单页 Demo（`demo/standalone.html`），同端口 `/ui` 挂载

## 注意

- 当前**无多用户登录**，一份 SQLite 共用，适合个人自测；公网请设 `ACCESS_PASSWORD`
- **不要提交** `backend/.env`（已在 `.gitignore`）
