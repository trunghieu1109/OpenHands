from openhands.controller.state.task import Task
from openhands.events import EventStream

GROUP_HISTORY_DEFAULT_LENGTH = 20


class AgentGroup:
    sid: str
    gid: str
    manager_id: str
    group_tasks: dict[str, Task]
    event_stream: EventStream
    members: dict[str, str]
    status: str

    def __init__(
        self,
        sid: str,
        gid: str,
        manager_id: str,
        init_group_task: Task | None,
        event_stream: EventStream,
    ):
        self.sid = sid
        # self._step_lock = asyncio.Lock()
        self.gid = gid
        self.manager_id = manager_id
        self.event_stream = event_stream

        # TODO: Get initial task from manager
        self.group_tasks = {}
        if init_group_task:
            self.group_tasks[self.manager_id] = init_group_task

        self.members = {}

        self.status = 'processing'  # ready, processing, stuck

    def add_member(self, member_id: str):
        self.members[member_id] = 'active'

    def remove_member(self, member_id: str):
        self.members[member_id] = 'inactive'
        del self.members[member_id]

    def get_group_history(self, length: int = GROUP_HISTORY_DEFAULT_LENGTH):
        start_idx = max(self.event_stream._cur_id - length - 1, 0)
        return self.event_stream.get_events(start_idx)
