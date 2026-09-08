# 简历面试助手（CV Helper）

围绕**简历经历**做结构化模拟面试：可生长的追问树、自动归档成笔记本 / 知识汇总，并支持真实面经转写复盘。

> 核心不是「多一个 ChatGPT 窗口」，而是「练完变成带索引的面试资料」。

仓库：https://github.com/ZealousYu/CV_helper
云服务网址：http://8.138.236.113:8000/
---

## 项目背景

求职准备里常见两类工具：一类是泛用聊天框，练完难沉淀；一类是题库刷题，和自己的简历经历脱节。

CV Helper 以**个人经历**为中心：把模拟问答长成一棵可回跳的**追问树**，并把值得保留的内容**归档**到笔记本与知识汇总，让「练」和「复盘」落在同一套资料上。文字追问树偏准备与打磨；语音面试偏正式演练；真实面经转写用于对照弱答。产品方向与竞品取舍见 [竞品对照与融合路线](docs/竞品对照与融合路线.md)、[产品方案](docs/简历面试助手-产品方案.md)。

前端主界面是 `demo/standalone.html`
**本地演示与云端部署采用同一套页面**

---

## 核心功能

| 模块 | 说明 |
|------|------|
| 经历库 | 手填或 PDF / Word 解析导入，作为出题与追问的素材 |
| 文字准备 | 在追问树上打磨答案（深挖 / 换角度 / 发散），可回跳 |
| 语音面试 | 浏览器读题 + 听写（可接豆包 TTS）；答案写入同一棵树 |
| 笔记本 / 知识汇总 | 标记待练习、复习对比、跨经历沉淀知识点 |
| 真实面经 | 粘贴转写 → 抽取问答 → 弱答标红 + 四维评分 |
| 岗位匹配 | JD 对照经历库，看缺口与表述建议 |
| 账号体系 | 注册登录、按用户隔离数据；管理员可查看用户摘要 |

---

## 亮点

- **采用追问树结构，而非一次性对话**：问答可生长、可回跳，刷新后仍在（SQLite 持久化）
- **练习时能即可归档**：笔记本与知识汇总把「练过的」变成可复习资产
- **简历驱动**：出题与追问围绕你的真实经历，而非通用题海
- **文字准备 + 语音演练分工清晰**：先打磨结构，再练临场表达
- **面经复盘带评分维度**：弱答可见，便于对照补洞
- **默认 Mock、可切真模型**：无 API Key 时可用内置 Mock 走通完整演示链路；配置 OpenAI 兼容接口（如 DeepSeek）后，可增强简历解析与问答生成。

---

## 如何快速部署到本地并使用 Demo

### 环境要求

- Git
- Python 3.10+

### 一键流程（Mac / Linux）

```bash
git clone https://github.com/ZealousYu/CV_helper.git
cd CV_helper/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Windows（CMD）

```bat
git clone https://github.com/ZealousYu/CV_helper.git
cd CV_helper\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 打开 Demo

浏览器访问：**http://127.0.0.1:8000/**  
（自动跳到 `/ui/standalone.html`）

建议路径：注册登录 → 经历库添加/导入 → 模拟面试作答与追问 → 查看笔记本 / 知识汇总。

默认 `LLM_PROVIDER=mock`，不配 API Key 也能演示；接真模型见下方文档链接。

更完整的「从装环境到打开 Demo」说明（含常见问题）：[从配置环境开始到演示 Demo](docs/从配置环境开始到演示Demo.md)

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端 | FastAPI、SQLAlchemy、SQLite |
| 鉴权 | JWT、bcrypt；可选整站访问密码 |
| LLM | Provider 抽象（Mock / OpenAI 兼容，如 DeepSeek） |
| 语音 | 浏览器 Web Speech；可选火山引擎豆包 TTS |
| 前端 | 单页 `demo/standalone.html`，与 API 同端口 `/ui` 挂载 |
| 部署 | Docker、阿里云、Railway、Render 等 |

API 与数据模型概览：[MVP-API 与数据模型](docs/MVP-API与数据模型.md)

---

## 注意事项

- **密钥与配置**：`backend/.env` 含 API Key、JWT 等，**不要提交到 Git**（已在 `.gitignore`）。公网务必修改 `JWT_SECRET`，建议设置 `ACCESS_PASSWORD`
- **管理员**：`.env` 中可预置 `ADMIN_USERNAME` / `ADMIN_PASSWORD`；否则首位注册用户可为管理员
- **本地 vs 云端数据**：代码以 GitHub 为准可随时恢复；各环境的 SQLite（如 `cv_helper.db`）与 `.env` **不会自动同步**，云主机数据需自行备份
- **大陆云域名 HTTPS**：阿里云等大陆机用域名走 80/443 通常需 ICP 备案；未备案可用 `http://公网IP:端口/` 访问
- **终端里 favicon 404**：可忽略，不影响使用

---

## 相关文档

| 文档 | 说明 |
|------|------|
| [从配置环境开始到演示 Demo](docs/从配置环境开始到演示Demo.md) | 零基础机器从安装环境到打开 Demo |
| [接真实大模型](docs/接真实大模型.md) | 配置 DeepSeek / OpenAI 兼容接口 |
| [竞品对照与融合路线](docs/竞品对照与融合路线.md) | 产品取舍与迭代路线 |
| [项目搭建过程跟踪](docs/项目搭建过程跟踪.md) | 记录搭建过程中的收获与踩坑点 |
| [产品方案](docs/简历面试助手-产品方案.md) | 早期产品方案 |
| [MVP-API 与数据模型](docs/MVP-API与数据模型.md) | 接口与模型说明 |
| [demo 说明](demo/README.md) | 前端目录说明 |
