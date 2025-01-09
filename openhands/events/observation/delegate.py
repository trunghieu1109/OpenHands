from dataclasses import dataclass, field

from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation


@dataclass
class AgentDelegateObservation(Observation):
    """This data class represents the result from delegating to another agent.

    Attributes:
        content (str): The content of the observation.
        outputs (dict): The outputs of the delegated agent.
        observation (str): The type of observation.
    """

    outputs: dict = field(default_factory=dict)
    observation: str = ObservationType.DELEGATE
    src_id: str = 'default-es'
    esid: str = 'default-es'

    @property
    def message(self) -> str:
        return ''
