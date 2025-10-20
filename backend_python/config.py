from __future__ import annotations
from pathlib import Path
from typing import List, Set
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    APPNAME: str = "image-service"
    ENV: str = Field(default="production")
    DATADIR: Path = Field(default=Path(".data"))
    ALLOWEDHOSTS: List[str] = Field(default_factory=list)
    CORSORIGINS: List[str] = Field(default_factory=list)
    CORSALLOWCREDENTIALS: bool = True
    CORSALLOWMETHODS: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "DELETE", "OPTIONS"]
    )
    CORSALLOWHEADERS: List[str] = Field(
        default_factory=lambda: [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
        ]
    )
    UPLOADMAXFILES: int = 200
    UPLOADMAXUNZIPPEDMB: int = 500
    UPLOADMAXFILEMB: int = 50
    ALLOWEDIMAGEEXTS: Set[str] = Field(
        default_factory=lambda: {".jpg", ".jpeg", ".png", ".webp"}
    )
    MINIMUM_IMAGE_RESOLUTION: int = 32
    MAXIMUM_IMAGE_DIMENSION: int = 10000
    MAXIMUM_IMAGE_PIXELS: int = 50000000

    ASSETSDIRNAME: str = "assets"
    REGISTRYDIRNAME: str = "registry"
    REGISTRYFILENAME: str = "assetsindex.json"
    PARAMSFILENAME: str = "settings.json"
    LOGLEVEL: str = "INFO"
    SECRET_KEY: str = Field(default="CHANGE_THIS_IN_PRODUCTION_USE_ENV_VAR")
    API_KEY_HEADER: str = "X-API-Key"
    REQUIRE_AUTH: bool = Field(default=True)
    VALID_API_KEYS: Set[str] = Field(default_factory=set)

    @field_validator("DATADIR", mode="before")
    @classmethod
    def ensure_datadir(cls, v):
        p = Path(v) if not isinstance(v, Path) else v
        p.mkdir(parents=True, exist_ok=True)
        (p / "tmp").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def DATAPATH(self) -> Path:
        return Path(self.DATADIR).resolve()

    @property
    def ASSETSPATH(self) -> Path:
        p = self.DATAPATH / self.ASSETSDIRNAME
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def REGISTRYPATH(self) -> Path:
        p = self.DATAPATH / self.REGISTRYDIRNAME
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def REGISTRYFILE(self) -> Path:
        return self.REGISTRYPATH / self.REGISTRYFILENAME

    @property
    def PARAMSFILE(self) -> Path:
        return self.DATAPATH / self.PARAMSFILENAME

    @property
    def UPLOAD_MAX_FILES(self) -> int:
        return self.UPLOADMAXFILES

    @property
    def UPLOAD_MAX_UNZIPPED_MB(self) -> int:
        return self.UPLOADMAXUNZIPPEDMB

    @property
    def UPLOAD_MAX_FILE_MB(self) -> int:
        return self.UPLOADMAXFILEMB

    @property
    def ALLOWED_IMAGE_EXTS(self) -> Set[str]:
        return self.ALLOWEDIMAGEEXTS

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if v == "CHANGE_THIS_IN_PRODUCTION_USE_ENV_VAR":
            raise ValueError(
                "SECRET_KEY must be changed from default value. "
                "Set SECRET_KEY environment variable with a secure random string."
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("VALID_API_KEYS")
    @classmethod
    def validate_api_keys(cls, v, info):
        require_auth = info.data.get("REQUIRE_AUTH", True)
        if require_auth and not v:
            raise ValueError(
                "VALID_API_KEYS cannot be empty when REQUIRE_AUTH is True. "
                "Set VALID_API_KEYS environment variable with comma-separated keys."
            )
        return v


settings = Settings()
