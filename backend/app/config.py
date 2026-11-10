from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import RunMode

PositiveInt = Annotated[int, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='forbid', allow_inf_nan=False)

    app_mode: RunMode = RunMode.fixture
    database_path: Path = Path('./data/private/tinchac.sqlite3')
    private_dir: Path = Path('./data/private')
    corpus_dir: Path = Path('./data/corpus')
    frontend_dist: Path | None = None
    app_timezone: Literal['Asia/Ho_Chi_Minh'] = 'Asia/Ho_Chi_Minh'
    gemini_api_key: SecretStr = Field(default=SecretStr(''), repr=False)
    llm_model: str = Field(default='gemini-3.5-flash-lite', min_length=1)
    llm_temperature: NonNegative = 0
    llm_timeout_seconds: PositiveInt = 30
    llm_max_retries: Annotated[int, Field(ge=0, le=1)] = 1
    llm_input_price_per_million_usd: NonNegative = 0.30
    llm_output_price_per_million_usd: NonNegative = 2.50
    usd_vnd_planning_rate: Annotated[float, Field(gt=0)] = 27000
    llm_budget_usd: NonNegative = 3
    llm_billing_mode: Literal['configured_rates', 'free_tier'] = 'configured_rates'
    # Enable HTTP charges only after account preflight and budget approval.
    llm_live_enabled: bool = False
    max_concurrent_jobs: PositiveInt = 2
    max_upload_bytes: PositiveInt = 5242880
    max_image_pixels: PositiveInt = 12000000
    max_input_chars: Annotated[int, Field(ge=20, le=6000)] = 6000
    resource_ttl_hours: PositiveInt = 24
    ocr_languages: str = Field(default='vie+eng', min_length=1)
    ocr_timeout_seconds: PositiveInt = 20
    allow_public_access: bool = False
