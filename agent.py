import threading
import yaml
from pathlib import Path

from llm import LLMCenter
from skill import Skill, SkillCenter
from brain import AgentBrain
from config import globalVar


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
            llm=self.llm,
            skills=self.skills,
            config_path=config_path,
        )
        self.memory = {}                     # raw event history per project
        self.summarised_project_memory = {}  # cheap-model condensed bullets per project

    # TODO: later need to scale up at project and task level, not just one global memory for the agent. Now, if there are multiple projects, the brain handling is in sequence, not in parallel.
    def process(self):
        """Drain this agent's process queue, run through brain, push to response queue."""
        while True:
            event = globalVar.slack_msg_process_queue[self.name].get()
            try:
                text = event.get("text", "")
                user = event.get("user", "")
                project = "project-test-1"  # TODO

                project_context = globalVar.project_context.get(project)

                # step 1 — good model: classify + run skill, plain string reply
                # prefer summarised memory if available, fall back to raw history
                memory_for_context = self.summarised_project_memory.get(
                    project, self.memory.get(project, [])
                )
                reply = self.brain.run(
                    user_input=(
                        f"{text}; project context: project one pager: {project_context.one_pager}; "
                        f"current agent project memory: {memory_for_context}"
                    ),
                )

                # step 2 — post reply to Slack
                if reply and reply.strip().lower() != "no":
                    globalVar.slack_msg_response_queue[self.name].put(
                        {
                            "project": project,
                            "text": f"Hi <@{user}>! {reply}",
                            "thread_ts": event.get("ts"),
                        }
                    )

                # step 3 — append raw event to memory log
                if project not in self.memory:
                    self.memory[project] = []
                self.memory[project].append(event)

                # step 4 — cheap model: condense into summarised memory bullets
                self.summarised_project_memory[project] = self.brain.summarise_for_memory(
                    user_message=text,
                    agent_reply=reply or "",
                    existing_memory=self.summarised_project_memory.get(project, []),
                    project=project,
                )

            except Exception as e:
                print(f"[{self.name}] Error processing message: {e}")
            finally:
                globalVar.slack_msg_process_queue[self.name].task_done()

    def run(self):
        self.process()


if __name__ == "__main__":
    agent = Agent(config_path="agent/researcher.yaml")
    answer = agent.brain.run(
        "What are circuit breaker logic used in other market making exchange?"
    )
    print(answer)