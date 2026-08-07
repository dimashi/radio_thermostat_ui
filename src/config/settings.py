from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


# Settings Declaration 
class Settings(BaseSettings):
    # Default values defined directly in Python
    use_kv_store: bool = False
    thermostat_ip: str = "http://127.0.0.1:8080"
    timeout: float = 5.0
    retry_attempts: int = 3
    
    # Enable optional local TOML or .env file support
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
        # Precedence Hierarchy (Highest priority wins):

        if cls.use_kv_store:
            from kv_store_provider import FirestoreSettingsSource
            return (
                env_settings,            # 1. Environment variables (Cloud Run)
                TomlConfigSettingsSource(settings_cls), # 2. Local TOML file
                FirestoreSettingsSource( # 3. Dynamic Key-Value store (Firestore)
                    settings_cls, collection="app_config", doc_id="global"
                ),
                init_settings,          # 4. In-code Python defaults
            )
        else:
            return (
                env_settings,            # 1. Environment variables (Cloud Run)
                TomlConfigSettingsSource(settings_cls), # 2. Local TOML file
                init_settings,          # 4. In-code Python defaults
            )

# Instantiation automatically negotiates all layers!
settings = Settings()