from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 始终读 backend/.env（不依赖启动时的当前工作目录）
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./cv_helper.db"
    llm_provider: str = "mock"  # mock | openai
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    # 面经转写送给模型的最大字符数（中文约等于字数）；入库本身不截断
    llm_transcript_max_chars: int = 20000
    # 简历正文送给模型的最大字符数
    llm_resume_max_chars: int = 16000
    cors_origins: str = "*"
    # 公网部署时建议设置：访问站点需输入此密码（留空则不启用）
    access_password: str = ""
    # 用户登录 JWT（务必在公网环境改成随机长串）
    jwt_secret: str = "cv-helper-dev-secret-change-me"
    jwt_expire_days: int = 30
    # 启动时若填写则预置管理员；遗留无主数据会挂到该账号
    admin_username: str = ""
    admin_password: str = ""
    # 语音合成：browser=浏览器自带 | doubao=火山引擎 | auto=有 Key 用豆包否则浏览器
    tts_provider: str = "auto"
    # 新版控制台：只填 API Key（推荐，对应文档 X-Api-Key）
    doubao_tts_api_key: str = ""
    # 旧版控制台：AppId + Access Token
    doubao_tts_app_id: str = ""
    doubao_tts_access_key: str = ""
    doubao_tts_speaker: str = "zh_female_kefunvsheng_uranus_bigtts"  # 默认女声（原暖阳）
    doubao_tts_resource_id: str = ""  # 空则按音色自动选 seed-tts-2.0 / seed-icl-2.0


settings = Settings()
