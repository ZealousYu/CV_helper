# 简历面试助手（CV Helper）

围绕**简历经历**做结构化模拟面试：可生长的**追问树**、自动归档成笔记本 / 知识汇总，并支持真实面经转写复盘。

> 核心不是「多一个 ChatGPT 窗口」，而是「练完变成带索引的面试资料」。

## `demo/` 是什么？

**不是「只给本地玩玩、不上云」的废弃原型。**  
`demo/standalone.html` 就是当前正式前端：本地和云主机都跑同一份，后端把它挂在 `/ui`。  
名字里的 Demo 只表示「单页联调界面」，不是第二套产品。

| 场景 | 怎么用 |
|------|--------|
| 本机开发 / 虚拟机挂了 | `uvicorn` → 打开 http://127.0.0.1:8000/ |
| 阿里云 / Docker / Railway | 同一仓库部署，浏览器打开公网地址（同样进 `/ui/standalone.html`） |

云上挂了也不丢代码：以 GitHub 为准即可恢复本机。

## 快速开始（本机）

```bash
git clone https://github.com/ZealousYu/CV_helper.git
cd CV_helper/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows CMD: .\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 填 LLM_API_KEY 等；勿把 .env 提交到 Git
uvicorn app.main:app --reload --port 8000
```

浏览器打开：http://127.0.0.1:8000/ （跳到 `/ui/standalone.html`）

接真实大模型说明：`docs/接真实大模型.md`  
过程跟踪（面试可讲）：`docs/项目搭建过程跟踪.md`  
**公网部署**：`docs/部署上线.md`（Docker / Render / Railway / 阿里云，建议设 `ACCESS_PASSWORD`）

### 云主机挂了之后

1. 本机重新 `git clone`（或已有目录里 `git pull`）  
2. 用你自己的 Key 重建 `backend/.env`（密钥从不进仓库）  
3. 按上面启动即可；SQLite 数据若只在云上，需要事先备份 `cv_helper.db`，否则只有代码没有云上账号数据

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

- 支持**用户名密码注册/登录**，数据按账号隔离；首位注册者（或 `.env` 里的 `ADMIN_*`）为管理员，可在「我的」查看用户摘要
- 公网建议设 `ACCESS_PASSWORD`，并修改 `JWT_SECRET`
- **不要提交** `backend/.env`（已在 `.gitignore`）
