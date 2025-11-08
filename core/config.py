from pathlib import Path
from pydantic import BaseModel
from typing import Optional

class AppConfig(BaseModel):
    """Global application configuration."""
    dictionary_path: Path = Path("./core/dictionaries/E_develop/dictionary")
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    timeout: int = 10  # RADIUS timeout in seconds
    retries: int = 3
    max_parallel_sessions: int = 10
    
    @classmethod
    def from_env(cls):
        """Load from environment variables."""
        import os
        return cls(
            dictionary_path=Path(os.getenv("RADIUS_DICT_PATH", cls.__fields__['dictionary_path'].default)),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=Path(os.getenv("LOG_FILE")) if os.getenv("LOG_FILE") else None,
            timeout=int(os.getenv("RADIUS_TIMEOUT", "10")),
            retries=int(os.getenv("RADIUS_RETRIES", "3")),
            max_parallel_sessions=int(os.getenv("MAX_PARALLEL_SESSIONS", "10"))
        )
