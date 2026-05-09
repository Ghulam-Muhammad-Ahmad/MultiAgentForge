from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://agentdb:agentpass@localhost:5432/agentdb"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    workspace_base_path: str = "/workspaces"

    class Config:
        env_file = ".env"


settings = Settings()
