"""Public interface for resolving C0–C5 mutant selections.

Each returned value is a declarative Configuration from ``mutants.config``;
the API/engine adapter may pass the selected object as its ``config`` value.
No run outcomes are stored here.
"""

from typing import Final

from .config import CONFIGS_BY_ID, Configuration


CONFIG_IDS: Final[tuple[str, ...]] = ("C0", "C1", "C2", "C3", "C4", "C5")


def get_configurations() -> dict[str, Configuration]:
    """Return a fresh ID-to-configuration mapping in stable C0–C5 order."""
    return {configuration_id: CONFIGS_BY_ID[configuration_id] for configuration_id in CONFIG_IDS}
