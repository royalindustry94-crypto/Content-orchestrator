"""Resolution of the configured pipeline provider.

``PIPELINE_PROVIDER_MODE`` selects the implementation once per process. The
default is ``null``, so a deployment that sets nothing keeps the fail-closed
behaviour it had before this seam existed.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import PipelineProvider
from app.providers.null import NullPipelineProvider
from app.providers.simulation import SimulationPipelineProvider

PROVIDER_MODE_NULL = "null"
PROVIDER_MODE_SIMULATION = "simulation"
SUPPORTED_PROVIDER_MODES = (PROVIDER_MODE_NULL, PROVIDER_MODE_SIMULATION)

_FACTORIES = {
    PROVIDER_MODE_NULL: NullPipelineProvider,
    PROVIDER_MODE_SIMULATION: SimulationPipelineProvider,
}


@lru_cache
def get_pipeline_provider() -> PipelineProvider:
    """Return the provider backing every pipeline stage in this process."""
    mode = get_settings().pipeline_provider_mode
    factory = _FACTORIES.get(mode)
    if factory is None:
        # Settings validation rejects unknown modes at startup; reaching here
        # would mean config was bypassed, and guessing a provider is worse
        # than refusing.
        raise ValueError(f"unsupported PIPELINE_PROVIDER_MODE: {mode!r}")
    return factory()


def provider_status() -> dict[str, object]:
    """Provider facts the UI needs to label stored output honestly."""
    provider = get_pipeline_provider()
    return {
        "mode": get_settings().pipeline_provider_mode,
        "name": provider.name,
        "state_label": provider.state_label,
        "configured": provider.is_configured,
        "simulated": provider.state_label == PROVIDER_MODE_SIMULATION,
        "external_publishing_enabled": False,
        "human_review_required": True,
    }
