# ABOUTME: Configuration loading and validation for notion-backup.
# ABOUTME: Parses config.yaml into validated dataclasses.

from dataclasses import dataclass, field
from pathlib import Path
import os
import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


@dataclass
class WorkspaceConfig:
    """Configuration for a single Notion workspace."""
    name: str
    token_env: str

    def get_token(self) -> str:
        """Retrieve the Notion token from environment variable."""
        token = os.environ.get(self.token_env)
        if not token:
            raise ConfigError(f"Environment variable '{self.token_env}' not set for workspace '{self.name}'")
        return token


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    discord_webhook_url: str | None = None
    notify_on: str = "error"  # "always" or "error"

    def __post_init__(self):
        if self.notify_on not in ("always", "error"):
            raise ConfigError(f"notify_on must be 'always' or 'error', got '{self.notify_on}'")


@dataclass
class Config:
    """Main configuration for notion-backup."""
    schedule: str
    retention_count: int
    workspaces: list[WorkspaceConfig]
    notifications: NotificationConfig = field(default_factory=NotificationConfig)

    def __post_init__(self):
        if self.retention_count < 1:
            raise ConfigError(f"retention_count must be at least 1, got {self.retention_count}")
        if not self.workspaces:
            raise ConfigError("At least one workspace must be configured")


def load_config(path: Path) -> Config:
    """Load and validate configuration from a YAML file."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(path) as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")

    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a YAML mapping")

    # Validate required fields
    required = ["schedule", "retention_count", "workspaces"]
    for key in required:
        if key not in raw:
            raise ConfigError(f"Missing required config field: {key}")

    # Parse workspaces
    workspaces = []
    for i, ws in enumerate(raw["workspaces"]):
        if not isinstance(ws, dict):
            raise ConfigError(f"Workspace {i} must be a mapping")
        if "name" not in ws:
            raise ConfigError(f"Workspace {i} missing 'name'")
        if "token_env" not in ws:
            raise ConfigError(f"Workspace '{ws.get('name', i)}' missing 'token_env'")
        workspaces.append(WorkspaceConfig(name=ws["name"], token_env=ws["token_env"]))

    # Parse notifications
    notif_raw = raw.get("notifications", {})
    notifications = NotificationConfig(
        discord_webhook_url=notif_raw.get("discord_webhook_url"),
        notify_on=notif_raw.get("notify_on", "error"),
    )

    return Config(
        schedule=raw["schedule"],
        retention_count=raw["retention_count"],
        workspaces=workspaces,
        notifications=notifications,
    )
