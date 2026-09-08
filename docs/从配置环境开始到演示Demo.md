**从配置环境开始到演示 Demo**

给一台**从没装过本项目**的电脑用：装好依赖 → 拉代码 → 启动 → 浏览器打开。  
本地和云端用的是同一套界面（`demo/standalone.html`）。

仓库：https://github.com/ZealousYu/CV_helper

---

## 0. 先装这两个（只需一次）

| 工具 | 用途 | 怎么装 |
|------|------|--------|
| **Git** | 下载代码 | Mac：终端执行 `xcode-select --install`，或装 [Git](https://git-scm.com/)；Windows：安装 [Git for Windows](https://git-scm.com/download/win) |
| **Python 3.10+** | 跑后端 | Mac：`brew install python` 或 [python.org](https://www.python.org/downloads/)；Windows：官网安装时勾选 **Add python.exe to PATH** |

装完在终端里确认：

```bash
git --version
python3 --version
```

Windows 若没有 `python3`，用：

```bat
python --version
```

---

## 1. 下载项目

**任意目录**都可以，例如用户主目录或桌面。不要假设一定有 `cursorProject` 文件夹。

```bash
git clone https://github.com/ZealousYu/CV_helper.git
cd CV_helper/backend
```

---

## 2. 创建虚拟环境并安装依赖

### Mac / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Windows（命令提示符 CMD）

```bat
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

提示符前面出现 `(.venv)` 就说明环境激活成功。

---

## 3. （可选）配置真实大模型

默认 `.env` 里是 `LLM_PROVIDER=mock`：**不配 Key 也能演示**全流程，只是 AI 回答是模拟的。

若要用 DeepSeek / OpenAI 等，用记事本或 VS Code 打开 `backend/.env`，改成例如：

```env
LLM_PROVIDER=openai
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

保存即可。**不要把 `.env` 提交到 Git。**  
更细的说明见：`docs/接真实大模型.md`。

---

## 4. 启动服务

确认当前目录是 `CV_helper/backend`，且已激活 `.venv`：

```bash
uvicorn app.main:app --reload --port 8000
```

看到类似输出即成功：

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

**这个窗口不要关**；关掉服务就停了。

---

## 5. 打开演示页面

浏览器访问：

**http://127.0.0.1:8000/**

会自动进入前端（`/ui/standalone.html`）。

建议演示路径：

1. 注册一个账号并登录  
2. **经历库**：手动加一条经历，或上传简历  
3. **模拟面试**：开始提问 → 作答 → 追问  
4. 看 **笔记本 / 知识汇总**  

终端里若出现 `favicon.ico` 的 `404`，可忽略，不影响演示。

---

## 6. 下次在同一台电脑再演示

不必重新 `clone`，只要：

```bash
cd CV_helper/backend          # 改成你当时放仓库的真实路径
source .venv/bin/activate     # Windows: .\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

若很久没更新，先：

```bash
cd CV_helper
git pull
cd backend
source .venv/bin/activate
pip install -r requirements.txt   # 有新依赖时才需要
uvicorn app.main:app --reload --port 8000
```

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `cd CV_Helper/backend` 失败 | 路径不对。先 `cd` 到你执行 `git clone` 的目录，再进 `CV_helper/backend`（GitHub 仓库名是 `CV_helper`） |
| `uvicorn` 不是内部或外部命令 | 没激活 venv，或没用 `python -m uvicorn ...` |
| 页面打不开 | 确认终端里服务还在跑；地址是 `127.0.0.1:8000` 不是云域名 |
| AI 很假 / 解析很粗 | 仍是 `mock`；按第 3 步填 Key 并重启 uvicorn |
| 端口被占用 | 换端口：`uvicorn app.main:app --reload --port 8001`，浏览器也改开 `8001` |

