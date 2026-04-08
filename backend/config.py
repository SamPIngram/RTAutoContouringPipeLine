import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OrthancConfig:
    url: str = "http://orthanc:8042"
    username: str = "orthanc"
    password: str = "orthanc"
    aet: str = "RTPIPELINE"


@dataclass
class GpuConfig:
    visible_devices: str = ""
    max_concurrent_inference: int = 2


@dataclass
class ProKnowConfig:
    base_url: str = ""
    credentials_file: str = ""


@dataclass
class Settings:
    data_dir: str = "/data"
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./rtautocontouring.db"
    redis_url: str = "redis://redis:6379/0"
    orthanc: OrthancConfig = field(default_factory=OrthancConfig)
    gpu: GpuConfig = field(default_factory=GpuConfig)
    proknow: ProKnowConfig = field(default_factory=ProKnowConfig)


def load_settings(config_path: str | Path = "config.toml") -> Settings:
    path = Path(config_path)
    if not path.exists():
        return Settings()

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    system = raw.get("system", {})
    db = raw.get("database", {})
    redis = raw.get("redis", {})
    orthanc_raw = raw.get("orthanc", {})
    gpu_raw = raw.get("gpu", {})
    proknow_raw = raw.get("proknow", {})

    return Settings(
        data_dir=system.get("data_dir", "/data"),
        log_level=system.get("log_level", "INFO"),
        database_url=db.get("url", "sqlite+aiosqlite:///./rtautocontouring.db"),
        redis_url=redis.get("url", "redis://redis:6379/0"),
        orthanc=OrthancConfig(
            url=orthanc_raw.get("url", "http://orthanc:8042"),
            username=orthanc_raw.get("username", "orthanc"),
            password=orthanc_raw.get("password", "orthanc"),
            aet=orthanc_raw.get("aet", "RTPIPELINE"),
        ),
        gpu=GpuConfig(
            visible_devices=gpu_raw.get("visible_devices", ""),
            max_concurrent_inference=gpu_raw.get("max_concurrent_inference", 2),
        ),
        proknow=ProKnowConfig(
            base_url=proknow_raw.get("base_url", ""),
            credentials_file=proknow_raw.get("credentials_file", ""),
        ),
    )
