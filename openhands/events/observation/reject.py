from dataclasses import dataclass

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class UserRejectObservation(Observation):
    """This data class represents the result of a rejected action."""

    observation: str = ObservationType.USER_REJECTED
    src_id: str = 'default-es'
    esid: str = 'default-es'

    @property
    def message(self) -> str:
        return self.content
