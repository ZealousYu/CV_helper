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


settings = Settings()
