import os
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

class Settings(BaseSettings):
    use_kv_store: bool = False
    thermostat_url: str = "http://thermostat-22-33-6A/"
    timeout: float = 5.0
    retry_attempts: int = 3
    
    model_config = SettingsConfigDict(
        toml_file="config.toml",
        env_prefix="APP_",
        extra="ignore"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        
        # 1. Read the environment variable directly (accounting for env_prefix="APP_")
        use_kv = os.getenv("APP_USE_KV_STORE", "false").lower() in ("true", "1", "yes")

        # 2. Conditionally append the KV store source
        if use_kv:
            from kv_store_provider import FirestoreSettingsSource
            return (
                env_settings,                            # 1. Environment variables
                TomlConfigSettingsSource(settings_cls),  # 2. Local TOML file
                FirestoreSettingsSource(                 # 3. Dynamic Key-Value store
                    settings_cls, collection="app_config", doc_id="global"
                ),
                init_settings,                          # 4. In-code Python defaults
            )

        return (
            env_settings,
            TomlConfigSettingsSource(settings_cls),
            init_settings,
        )

settings = Settings()