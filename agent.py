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
        self.memory = {}

    # TODO: later need to scale up at project and task level, not just one global memory for the agent. Now, if there are multiple projects, the brain handling is in scequence, not in parallel.
    def process(self):
        """Drain this agent's process queue, run through brain, push to response queue."""
        while True:
            event = globalVar.slack_msg_process_queue[self.name].get()
            try:
                text = event.get("text", "")
                user = event.get("user", "")
                project = "project-test-1"  # TODO

                project_context = globalVar.project_context.get(project)

                # TODO: need to optimise this part to save tokens, e.g.: use a small model to summarise each time
                reply = self.brain.run(
                    user_input=f"{text}; project context: project one pager: {project_context.one_pager}; current agent project memory: {self.memory.get(project, [])}",
                )
                if project not in self.memory:
                    self.memory[project] = []
                self.memory[project].append(event)
                if reply and reply.strip().lower() != "no":
                    globalVar.slack_msg_response_queue[self.name].put(
                        {
                            "project": project,
                            "text": f"Hi <@{user}>! {reply}",
                            "thread_ts": event.get("ts"),
                        }
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
