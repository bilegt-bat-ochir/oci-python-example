from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ScaleTags:
    namespace: str = "osc_exacc"
    scale_down_time: str = "scale_down_time"
    scale_up_time: str = "scale_up_time"
    scale_down_ocpus: str = "scale_down_ocpus"
    scale_up_ocpus: str = "scale_up_ocpus"


@dataclass
class ScaleDecision:
    cluster_id: str
    display_name: str
    region: str
    compartment_path: str
    lifecycle_state: str
    current_ocpus: int
    desired_ocpus: Optional[int]
    direction: str
    outcome: str
    reason: str

    @property
    def should_submit(self) -> bool:
        return self.outcome == "submit"


def current_utc_hour_marker() -> str:
    return datetime.now(timezone.utc).strftime("%H:00_UTC")


def _defined_tag_value(
    defined_tags: Dict[str, Dict[str, Any]], tags: ScaleTags, key: str
) -> Any:
    namespace_values = defined_tags.get(tags.namespace, {})
    return namespace_values.get(key)


def decide_scale_action(
    *,
    cluster_id: str,
    display_name: str,
    region: str,
    compartment_path: str,
    lifecycle_state: str,
    cpus_enabled: int,
    defined_tags: Dict[str, Dict[str, Any]],
    time_marker: str,
    tags: ScaleTags,
    confirm: bool,
    verbose: bool = False,
) -> Optional[ScaleDecision]:
    state = (lifecycle_state or "").upper()
    if state != "AVAILABLE":
        return ScaleDecision(
            cluster_id=cluster_id,
            display_name=display_name,
            region=region,
            compartment_path=compartment_path,
            lifecycle_state=state,
            current_ocpus=cpus_enabled,
            desired_ocpus=None,
            direction="none",
            outcome="ignored",
            reason="cluster is not AVAILABLE",
        )

    down_time = _defined_tag_value(defined_tags, tags, tags.scale_down_time)
    up_time = _defined_tag_value(defined_tags, tags, tags.scale_up_time)
    down_ocpus = _defined_tag_value(defined_tags, tags, tags.scale_down_ocpus)
    up_ocpus = _defined_tag_value(defined_tags, tags, tags.scale_up_ocpus)

    required_values = [down_time, up_time, down_ocpus, up_ocpus]
    if any(value in (None, "") for value in required_values):
        if not verbose:
            return None
        return ScaleDecision(
            cluster_id=cluster_id,
            display_name=display_name,
            region=region,
            compartment_path=compartment_path,
            lifecycle_state=state,
            current_ocpus=cpus_enabled,
            desired_ocpus=None,
            direction="none",
            outcome="ignored",
            reason="one or more scaling tags are missing",
        )

    if down_time == time_marker:
        direction = "down"
        desired_value = down_ocpus
    elif up_time == time_marker:
        direction = "up"
        desired_value = up_ocpus
    else:
        return None

    try:
        desired_ocpus = int(desired_value)
    except (TypeError, ValueError):
        return ScaleDecision(
            cluster_id=cluster_id,
            display_name=display_name,
            region=region,
            compartment_path=compartment_path,
            lifecycle_state=state,
            current_ocpus=cpus_enabled,
            desired_ocpus=None,
            direction=direction,
            outcome="ignored",
            reason=f"{direction} OCPU tag value is not an integer",
        )

    if cpus_enabled == desired_ocpus:
        return ScaleDecision(
            cluster_id=cluster_id,
            display_name=display_name,
            region=region,
            compartment_path=compartment_path,
            lifecycle_state=state,
            current_ocpus=cpus_enabled,
            desired_ocpus=desired_ocpus,
            direction=direction,
            outcome="noop",
            reason=f"already at {desired_ocpus} OCPUs",
        )

    outcome = "submit" if confirm else "dry-run"
    reason = (
        f"scale {direction} from {cpus_enabled} to {desired_ocpus} OCPUs"
        if confirm
        else f"would scale {direction} from {cpus_enabled} to {desired_ocpus} OCPUs"
    )
    return ScaleDecision(
        cluster_id=cluster_id,
        display_name=display_name,
        region=region,
        compartment_path=compartment_path,
        lifecycle_state=state,
        current_ocpus=cpus_enabled,
        desired_ocpus=desired_ocpus,
        direction=direction,
        outcome=outcome,
        reason=reason,
    )
