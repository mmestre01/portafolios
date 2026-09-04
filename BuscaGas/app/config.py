from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ors_api_key: str = ""
    ors_base_url: str = "https://api.heigit.org"
    miteco_stations_url: str = (
        "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
        "PreciosCarburantes/EstacionesTerrestres/"
    )
    stations_cache_ttl: int = Field(600, ge=1)
    matrix_batch_size: int = Field(40, ge=1, le=100)
    max_matrix_candidates: int = Field(200, ge=1, le=1000)
    max_results: int = Field(20, ge=1, le=100)
    http_timeout_seconds: float = Field(20, gt=0)
    root_path: str = "/BuscaGas"


@lru_cache
def get_settings() -> Settings:
    return Settings()
