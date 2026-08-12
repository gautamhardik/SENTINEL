"""
FeatureRegistry managing active feature builder groups.
"""
from typing import List

from fraud_detection.feature_engineering.builders import (
    BaseFeatureBuilder,
    BehavioralBuilder,
    RiskBuilder,
    RollingBuilder,
    TemporalBuilder,
    VelocityBuilder,
)


class FeatureRegistry:
    """Registry maintaining active feature builder groups."""

    def __init__(self, builders: List[BaseFeatureBuilder] = None):
        if builders is not None:
            self.builders = list(builders)
        else:
            self.builders = [
                TemporalBuilder(),
                VelocityBuilder(),
                BehavioralBuilder(),
                RiskBuilder(),
                RollingBuilder()
            ]

    def register(self, builder: BaseFeatureBuilder) -> None:
        """Registers a new feature builder group."""
        self.builders.append(builder)

    def get_builders(self) -> List[BaseFeatureBuilder]:
        """Returns active list of feature builders."""
        return list(self.builders)
