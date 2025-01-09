from dataclasses import dataclass

from openhands.events.event import Event


@dataclass
class Observation(Event):
    content: str = ''
    src_id: str = 'default-es'
    esid: str = 'default-es'
