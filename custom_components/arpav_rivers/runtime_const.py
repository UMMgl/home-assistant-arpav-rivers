from __future__ import annotations

from datetime import timedelta

DOMAIN = "arpav_rivers"
PLATFORMS = ["sensor"]
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=10)
DEFAULT_REQUEST_TIMEOUT = 15
DEFAULT_PROFILE = "bacchiglione"

PROFILES: dict[str, tuple[str, ...]] = {
    "bacchiglione": (
        "0276", "0333", "0303", "0308", "0334", "0595", "0287",
        "0285", "0305", "0404", "0321", "0635", "0302", "0629",
        "0329", "0646",
    ),
    "piave": (
        "0271", "0297", "0309", "0316", "0323", "0327", "0406",
        "0628", "0651", "0652", "0661",
    ),
    "livenza": (
        "0294", "0300", "0306", "0359", "0378", "0400", "0401",
    ),
}
