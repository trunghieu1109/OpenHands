from openhands.controller.state.state import State
from openhands.core.logger import openhands_logger as logger
from openhands.core.schema import ActionType
from openhands.core.utils import json
from openhands.events.action import (
    Action,
    NullAction,
)
from openhands.events.serialization.action import action_from_dict
from openhands.events.serialization.event import event_to_memory

HISTORY_SIZE = 20

# Task
prompt_template = """
You have been a diligent software engineer AI and a excellent Project Manager. You receive requirements
from users and have to plan the steps to be executed in the future. Therefore, you need to proceed step
by step, starting with searching for neccessary information, analyzing user requirements, and then creating
a detailed plan of tasks to complete those requirements (leveraging the characteristics of the agents
described below). The plan could be adjusted, based on current requirements, observations (action's results)
and plan's status. So you can think critically, explore new ideas, add new task, modify task, and delegate
tasks to other agents.

You've been given the following requirement:

%(task)s

## Plan
As you complete this task, you're building a plan and keeping
track of your progress. Here's a JSON representation of your plan:

%(plan)s

%(plan_status)s

## Note

If you lack expertise in the domain or do not understand the user's requirements,
you can seek additional information from other sources, for example, Internet.

You're responsible for managing this plan and the status of tasks in
it, by using the `add_task` and `modify_task` actions described below. When adding
or modifying a task, you need to review the entire task list and check for any duplicates
or conflicts with the current task to make adjustments.

After adding the required tasks to the system, you will delegate them to
the agents within the system. Each agent has different specialties and functions,
as described in "Delegated Agents" section.

If the History below contradicts the state of any of these tasks, you
MUST modify the task using the `modify_task` action described below.

Be sure NOT to duplicate any tasks. Do NOT use the `add_task` action for
a task that's already represented. Every task must be represented only once.

Tasks that are sequential MUST be siblings. They must be added in order
to their parent task.

If you mark a task as 'completed', 'verified', or 'abandoned',
all non-abandoned subtasks will be marked the same way.
So before closing a task this way, you MUST not only be sure that it has
been completed successfully--you must ALSO be sure that all its subtasks
are ready to be marked the same way.

If you can not address this requirement, you could response
with the `reject` action.

If you have not implemented any action, you could not respond with the `finish` action.
If ALL tasks have already been marked verified, you MUST respond with the `finish` action.

Similarly, do not assign the same task to agents consecutively. If an error
occurs, agent needs to find the way to address.

## History
Here is a recent history of actions agents've taken in service of this plan,
as well as observations agents've made. This only includes the MOST RECENT
ten actions--more happened before that. The observation reflects the
results after the agents complete their assigned actions and represents the
current state of the project.

%(history)s

The most recent action is at the bottom of that history.

## Action
What is your next thought or action? Your response must be in JSON format.

It must be an object, and it must contain two fields:
* `action`, which is one of the actions below
* `args`, which is a map of key-value pairs, specifying the arguments for that action

* `delegate` - send a task to another agent from the list provided. Arguments:
  * `agent` - the agent to which the task is delegated. MUST match a name in the list of agents provided.
  * `inputs` - a dictionary of input parameters to the agent, as specified in the list
* `add_task` - add a task to your plan. Arguments:
  * `parent` - the ID of the parent task (leave empty if it should go at the top level)
  * `goal` - the goal of the task
  * `subtasks` - a list of subtasks, each of which is a map with a `goal` key.
* `modify_task` - close a task. Arguments:
  * `task_id` - the ID of the task to close
  * `state` - set to 'in_progress' to start the task, 'completed' to finish it, 'verified' to assert that it was successful, 'abandoned' to give up on it permanently, or `open` to stop working on it for now.
* `finish` - if ALL of your tasks and subtasks have been verified or abandoned, and you're absolutely certain that you've completed your task and have tested your work, use the finish action to stop working.
* `reject` - if you can not address these requirements, you could respond with `reject` action.

## Delegated Agents
These are agents you could choose to delegate a specific task.

### Agents

%(delegated_agents)s

You should never act twice in a row without thinking. But if your last several
actions are all `message` actions, you should consider taking a different action.

What is your next thought or action? Again, you must reply with JSON, and only with JSON.
"""


def get_hint(latest_action_id: str) -> str:
    """Returns action type hint based on given action_id"""
    hints = {
        '': "You haven't taken any actions yet. Start by using `ls` to check out what files you're working with.",
        ActionType.DELEGATE: 'You should observe delegated agents and their observation and think about the next action to take.',
        ActionType.ADD_TASK: 'You should think about the next action to take.',
        ActionType.MODIFY_TASK: 'You should think about the next action to take.',
        ActionType.REJECT: '',
        ActionType.FINISH: '',
    }
    return hints.get(latest_action_id, '')


def get_delegated_agents_str(delegated_agents: dict):
    # print(delegated_agents)
    scripts = ''
    for key in delegated_agents:
        name = key
        details = delegated_agents[name]
        scripts = scripts + f'### {name}:\n'
        scripts = scripts + details['description'] + '\n'
        scripts = scripts + '### Inputs:\n'
        scripts = scripts + json.dumps(details['inputs']) + '\n'

    return scripts


def get_prompt_and_images(
    state: State, max_message_chars: int
) -> tuple[str, list[str] | None]:
    """Gets the prompt for the master agent.

    Formatted with the most recent action-observation pairs, current task, plan and hint based on last action

    Parameters:
    - state (State): The state of the current agent

    Returns:
    - str: The formatted string prompt with historical values
    """
    # the plan
    plan_str = json.dumps(state.root_task.to_dict(), indent=2)

    # the history
    history_dicts = []
    latest_action: Action = NullAction()

    # retrieve the latest HISTORY_SIZE events
    for event_count, event in enumerate(reversed(state.history)):
        if event_count >= HISTORY_SIZE:
            break
        if latest_action == NullAction() and isinstance(event, Action):
            latest_action = event
        history_dicts.append(event_to_memory(event, max_message_chars))

    # history_dicts is in reverse order, lets fix it
    history_dicts.reverse()

    # and get it as a JSON string
    history_str = json.dumps(history_dicts, indent=2)

    # the plan status
    current_task = state.root_task.get_current_task()
    if current_task is not None:
        plan_status = f"You're currently working on this task:\n{current_task.goal}."
        if len(current_task.subtasks) == 0:
            plan_status += "\nIf it's not achievable AND verifiable with a SINGLE action, you MUST break it down into subtasks NOW."
    else:
        plan_status = "You're not currently working on any tasks. Your next action MUST be to mark a task as in_progress."

    # the hint, based on the last action
    hint = get_hint(event_to_memory(latest_action, max_message_chars).get('action', ''))
    logger.debug('HINT:\n' + hint, extra={'msg_type': 'DETAIL'})

    # the last relevant user message (the task)
    message, image_urls = state.get_current_user_intent()

    # delegated_agents_dict = all_microagents.copy()
    # del delegated_agents_dict['ManagerAgent']
    # del delegated_agents_dict['CommitWriterAgent']

    # delegated_agents_str = get_delegated_agents_str(delegated_agents_dict)

    delegated_agents = """
## Analyst
Description: The Analyst analyzes user requests to help the system gain a detailed understanding of the user's goals and intentions. Specifically, it delves into the syntax and semantics of the request, identifying keywords, context, and user's objectives.
Input: User request

## Explorer:
Description: The Explorer relies on the analyzed information from the user's request to explore, search, and synthesize knowledge from the environment, including related repositories (codebase) and the Internet environment. Through this process, the Explorer provides additional necessary information to accomplish the task.
Input: Codebase, keywords, context, and user's objectives

## Coder:
Description: The Coder receives tasks from the Master and plans what needs to be done to create a complete software product. As a result, this agent can write code (Python, Terminal commands), execute code, manage databases, summarize code, and more.
Input: Coding tasks (Or some related tasks)

## Tester:
Description: The Tester will receive the project's codebase and create test cases for the software to check its functionality, non-functionality, and integration capabilities.
Input: Generated Codebase, functional and non-functional requirements needed to be tested.
"""

    # finally, fill in the prompt

    config_prompt = prompt_template % {
        'task': message,
        'plan': plan_str,
        'history': history_str,
        'hint': hint,
        'plan_status': plan_status,
        'delegated_agents': delegated_agents,
    }

    # print(config_prompt)

    return config_prompt, image_urls


def parse_response(response: str) -> Action:
    """Parses the model output to find a valid action to take
    Parameters:
    - response (str): A response from the model that potentially contains an Action.

    Returns:
    - Action: A valid next action to perform from model output
    """
    action_dict = json.loads(response)

    print(response)

    if 'contents' in action_dict:
        # The LLM gets confused here. Might as well be robust
        action_dict['content'] = action_dict.pop('contents')
    action = action_from_dict(action_dict)
    return action
