import threading
import yaml
from pathlib import Path
import re
import traceback

from llm import LLMCenter
from skill import Skill, SkillCenter
from brain import AgentBrain
from config import globalVar
from utils.utils import json_exporter

# Slack user IDs of the agents — mirrors the roster in agents/project_lead.yaml.
# Used to (a) avoid greeting/re-pinging a bot sender and (b) cap each outgoing
# message to one agent mention so only one agent is triggered at a time.
AGENT_SLACK_IDS = {
    "U0B9K560933",  # project_lead
    "U0B9K3QQW57",  # research
    "U0BAD9MHY06",  # architect
    "U0BA90P4MEF",  # marketing
    "U0B9K5ZLMS5",  # developer
    "U0BA90EM1FV",  # tester
}

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]+)?>")


def limit_to_one_agent_mention(text: str) -> str:
    """Keep only the FIRST agent mention; strip any further agent mentions so a
    single Slack message triggers at most one agent. Human mentions are left
    untouched."""
    used = False

    def _repl(m):
        nonlocal used
        if m.group(1) in AGENT_SLACK_IDS:
            if used:
                return ""
            used = True
        return m.group(0)

    return _MENTION_RE.sub(_repl, text)


class Agent(threading.Thread):
    def __init__(self, config_path: str):
        super().__init__(daemon=True)
        config = yaml.safe_load(Path(config_path).read_text())

        self.name = config["name"]
        self.llm = LLMCenter(called_by=self.name)
        self.skills = SkillCenter(
            skills_dir=config.get("skills_dir", "skills"),
            context_dir=config.get("context_dir", "context"),
        )
        self.brain = AgentBrain(
            llm=self.llm, skills=self.skills, config_path=config_path,
        )
        self.memory = {}  # raw event history per project
        self.summarised_project_memory = {}  # cheap-model condensed bullets per project

    # TODO: later need to scale up at project and task level, not just one global memory for the agent. Now, if there are multiple projects, the brain handling is in sequence, not in parallel.
    def process(self):
        """Drain this agent's process queue, run through brain, push to response queue."""
        while True:
            event = globalVar.slack_msg_process_queue[self.name].get()
            try:
                slack_user_name_sender_name = event["slack_user_name_sender_name"]
                reply_required = True
                # if slack_user_name_sender_name == self.name:
                #     reply_required = False
                # self-messages are already dropped in SlackBot._process (by
                # bot_user_id), so no name-based self-check is needed here. Gate
                # only by role: non-lead agents act when @mentioned (app_mention),
                # not on every plain channel message.

                if (event["type"] == "message") and (self.name not in ["lead-agent"]):
                    reply_required = False

                text = event.get("text", "")
                sender_user_id = event.get("user")
                # project = "project-test-1"  # TODO
                project = event["slack_channel_name"]

                project_context = globalVar.project_context.get(project)

                # step 1 — good model: classify + run skill, plain string reply
                # prefer summarised memory if available, fall back to raw history
                # memory_for_context = self.memory.get(
                #     project, []
                # )  # TODO: sometimes, it is in a list, sometimes in str
                memory_for_context = globalVar.global_memory.get(project)
                
                reply = None
                if reply_required == True:
                    resolved_skill = self.brain._classify(text)
                    if resolved_skill.value == "reply_not_required":
                        # if we were directly addressed (e.g. "APPROVED @lead-agent"),
                        # the message DOES need action — don't go silent; reason about
                        # the next step. Only stay silent on undirected chatter.
                        if event.get("is_mention"):
                            resolved_skill = Skill.REASONING
                        else:
                            reply_required = False

                if reply_required:
                    # TODO: make one_pager as by default first memory for the agent in the project
                    reply = self.brain.run(
                        user_input=(
                            # f"slack message received: {text}; sender: {slack_user_name_sender_name}; receiver: {self.name}; project context: project one pager: {project_context.one_pager}; "
                            f"slack message details received: {event}; sender: {slack_user_name_sender_name}; receiver: {self.name}; project context: project one pager: {project_context.one_pager}; "
                            f"full channel project memory: {memory_for_context}"
                        ),
                        skill=resolved_skill,
                    )

                    # step 2 — post reply to Slack
                    if reply and reply.strip() != "":
                        # TODO: if reply has sender_user_id, then remove the hard coded sender_user_id. Actually should let the agent to decide who to reply to.
                        globalVar.slack_msg_response_queue[self.name].put(
                            {
                                "project": project,
                                # "text": f"Hi <@{sender_user_id}>! {reply}",
                                "text": f"{reply}",
                                "thread_ts": event.get("ts"),
                            }
                        )

                # step 3 — append raw event to memory log
                if project not in self.memory:
                    self.memory[project] = []
                self.memory[project].append(event)

                json_exporter(
                    self.memory[project],
                    f"memory/full/{self.name}_{project}_memory.json",
                )

                # # step 4 — cheap model: condense into summarised memory bullets
                # self.summarised_project_memory[
                #     project
                # ] = self.brain.summarise_for_memory(
                #     user_message=text,
                #     agent_reply=reply or "",
                #     existing_memory=self.summarised_project_memory.get(project, []),
                #     project=project,
                # )
                # json_exporter(
                #     self.summarised_project_memory[project],
                #     f"memory/summary/{self.name}_{project}_memory.json",
                # )

            except Exception as e:
                print(
                    f"[{self.name}] Error processing message: {traceback.format_exc()}"
                )
            finally:
                globalVar.slack_msg_process_queue[self.name].task_done()

    def run(self):
        self.process()


if __name__ == "__main__":
    agent = Agent(config_path="agents/research-agent.yaml")
    answer = agent.brain.run(
        "What are circuit breaker logic used in other market making exchange?"
    )
    print(answer)
