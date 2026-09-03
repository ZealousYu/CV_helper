#!/usr/bin/env bash
# 在阿里云轻量 / ECS（Ubuntu）上一键部署 CV Helper
# 用法：
#   1) 把整个项目上传到服务器，或 git clone 你的仓库
#   2) cd 到含 Dockerfile 的目录
#   3) bash scripts/deploy-aliyun.sh
set -euo pipefail

APP_NAME="${APP_NAME:-cv-helper}"
IMAGE_NAME="${IMAGE_NAME:-cv-helper:latest}"
HOST_PORT="${HOST_PORT:-80}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
DATA_DIR="${DATA_DIR:-/var/lib/cv-helper}"
ENV_FILE="${ENV_FILE:-.env.production}"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f Dockerfile ]]; then
  echo "当前目录没有 Dockerfile，请在 CV_Helper 仓库根目录执行。"
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  # 生成随机 JWT，避免用开发默认值上公网
  JWT_RAND="$(openssl rand -hex 24 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 32)"
  cat > "$ENV_FILE" <<EOF
# 全站门锁（强烈建议设置；留空=不启用）
ACCESS_PASSWORD=请改成你的访问密码

# 登录 JWT（务必保留随机值，勿用开发默认）
JWT_SECRET=${JWT_RAND}
JWT_EXPIRE_DAYS=30

# 预置管理员（可选；不填则首位注册用户为管理员）
ADMIN_USERNAME=
ADMIN_PASSWORD=

DATABASE_URL=sqlite:////data/cv_helper.db
LLM_PROVIDER=mock
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
CORS_ORIGINS=*
TTS_PROVIDER=auto
DOUBAO_TTS_API_KEY=
EOF
  echo "已生成 $ENV_FILE ，请先编辑里面的 ACCESS_PASSWORD（以及可选的模型 Key / 管理员），再重新运行本脚本。"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "未检测到 Docker，正在安装…"
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
  echo "Docker 已安装。若提示 permission denied，请重新 SSH 登录后再跑一次本脚本。"
fi

sudo mkdir -p "$DATA_DIR"
sudo chown -R "$USER":"$USER" "$DATA_DIR" 2>/dev/null || true

echo "构建镜像…"
sudo docker build -t "$IMAGE_NAME" .

echo "停止旧容器（如有）…"
sudo docker rm -f "$APP_NAME" 2>/dev/null || true

echo "启动…"
sudo docker run -d \
  --name "$APP_NAME" \
  --restart unless-stopped \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  --env-file "$ENV_FILE" \
  -e DATABASE_URL=sqlite:////data/cv_helper.db \
  -e PORT="$CONTAINER_PORT" \
  -v "${DATA_DIR}:/data" \
  "$IMAGE_NAME"

echo
echo "部署完成。"
echo "本机健康检查： curl -s http://127.0.0.1:${HOST_PORT}/api/health"
echo "公网访问： http://你的服务器公网IP/  （安全组需放行 ${HOST_PORT}）"
echo "以后更新代码后，在本目录再次执行： bash scripts/deploy-aliyun.sh"
