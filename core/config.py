"""Central configuration for ScrimLab.

Every guild / channel / role / emoji ID can be overridden with an environment
variable (see ``.env.example``).  The defaults are the IDs ScrimLab shipped
with, so an existing deployment keeps working without a ``.env`` file.

Secrets (bot token, top.gg token) are read from the environment and are never
written to disk by this module.
"""

from __future__ import annotations

import os


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a Discord snowflake (integer), got {raw!r}"
        ) from exc


def _csv_ints(name: str, default: str) -> tuple[int, ...]:
    raw = os.getenv(name, default)
    return tuple(int(part) for part in raw.replace(" ", "").split(",") if part)


# --- credentials -----------------------------------------------------------
TOKEN = os.getenv("TOKEN", "")
TOP_GG_TOKEN = os.getenv("TOP_GG_TOKEN", "")

# --- update checker --------------------------------------------------------
GITHUB_USER = os.getenv("GITHUB_USER", "IHLAMUR123")
GITHUB_REPO = os.getenv("GITHUB_REPO", "ScrimLab")

# --- guilds ----------------------------------------------------------------
GUILD_ID = _int("GUILD_ID", 1458071278689845283)
# Where slash commands are synced during development.
# Set DEV_GUILD_ID=0 to sync globally instead.
DEV_GUILD_ID = _int("DEV_GUILD_ID", GUILD_ID)
DEV_USER_IDS = _csv_ints("DEV_USER_IDS", "655498457083150342")

# --- channels --------------------------------------------------------------
BALANCE_LOG_CHANNEL_ID = _int("BALANCE_LOG_CHANNEL_ID", 1454210251887874128)
REPORT_CHANNEL_ID = _int("REPORT_CHANNEL_ID", 1454162669597622303)
SUPPORT_CHANNEL_ID = _int("SUPPORT_CHANNEL_ID", 1453371166147477575)
QUEUE_CHANNEL_ID = _int("QUEUE_CHANNEL_ID", 1454458642622451824)
MATCH_INFO_CHANNEL_ID = _int("MATCH_INFO_CHANNEL_ID", 1456276066967752705)
ERROR_LOG_CHANNEL_ID = _int("ERROR_LOG_CHANNEL_ID", 1452690176760479755)

# --- roles -----------------------------------------------------------------
# WARNING_ROLE_ID ships as 0 (disabled): the original code pointed it at a
# channel ID, so the warning role never resolved. Set it to a real role ID.
WARNING_ROLE_ID = _int("WARNING_ROLE_ID", 0)
NEW_MEMBER_ROLE_ID = _int("NEW_MEMBER_ROLE_ID", 1453407218442702941)
MEMBER_ROLE_ID = _int("MEMBER_ROLE_ID", 1453335299840020511)

# --- testing ---------------------------------------------------------------
TEST_BOT_ID = _int("TEST_BOT_ID", 1452380258933149958)

# --- emojis ----------------------------------------------------------------
def _emoji(name: str, default: str) -> str:
    return os.getenv(name, default)


ROLE_EMOJIS: dict[str, str] = {
    "top": _emoji("EMOJI_TOP", "<:Top:1454081617382477908>"),
    "jungle": _emoji("EMOJI_JUNGLE", "<:Jungle:1454081696327667836>"),
    "mid": _emoji("EMOJI_MID", "<:Mid:1454081643374448836>"),
    "adc": _emoji("EMOJI_ADC", "<:ADC:1454081581445812244>"),
    "support": _emoji("EMOJI_SUPPORT", "<:Support:1454081735087231048>"),
    "flex": _emoji("EMOJI_FLEX", "❓"),
}
FILL_EMOJI = _emoji("EMOJI_FILL", "<:fill:1066868480537800714>")


def sync_guild_ids() -> list[int] | None:
    """Value for ``test_guilds`` / ``guild_ids``: None means global sync."""
    return [DEV_GUILD_ID] if DEV_GUILD_ID else None
