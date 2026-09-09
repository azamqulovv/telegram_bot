import json
import os

import config

CHANNELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")


def _normalize_channel(value: str) -> str:
    value = value.strip()
    if value.startswith("https://t.me/"):
        value = "@" + value.removeprefix("https://t.me/").strip("/")
    elif value.startswith("t.me/"):
        value = "@" + value.removeprefix("t.me/").strip("/")
    if not value.startswith("@"):
        value = "@" + value
    return value


def get_channels() -> list[str]:
    default_channel = _normalize_channel(config.CHANNEL_ID)
    try:
        with open(CHANNELS_FILE, "r", encoding="utf-8") as channel_file:
            channels = json.load(channel_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return [default_channel]

    if not isinstance(channels, list):
        return [default_channel]
    result = []
    for channel in channels:
        if isinstance(channel, str) and channel.strip():
            normalized = _normalize_channel(channel)
            if normalized not in result:
                result.append(normalized)
    return result or [default_channel]


def save_channels(channels: list[str]) -> None:
    unique_channels = []
    for channel in channels:
        normalized = _normalize_channel(channel)
        if normalized not in unique_channels:
            unique_channels.append(normalized)
    temporary_file = f"{CHANNELS_FILE}.tmp"
    with open(temporary_file, "w", encoding="utf-8") as channel_file:
        json.dump(unique_channels, channel_file, ensure_ascii=False, indent=2)
    os.replace(temporary_file, CHANNELS_FILE)


def add_channel(channel: str) -> str:
    normalized = _normalize_channel(channel)
    channels = get_channels()
    if normalized not in channels:
        channels.append(normalized)
        save_channels(channels)
    return normalized


def remove_channel(channel: str) -> bool:
    """Admin qo'shgan kanalni o'chiradi; asosiy .env kanali saqlanadi."""
    normalized = _normalize_channel(channel)
    default_channel = _normalize_channel(config.CHANNEL_ID)
    if normalized == default_channel:
        return False

    current = get_channels()
    if normalized not in current:
        return False
    current.remove(normalized)
    save_channels(current)
    return True
