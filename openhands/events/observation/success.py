from dataclasses import dataclass

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class SuccessObservation(Observation):
    """This data class represents the result of a successful action."""

    observation: str = ObservationType.SUCCESS
    src_id: str = 'default-es'
    esid: str = 'default-es'

    @property
    def message(self) -> str:
        return self.content
