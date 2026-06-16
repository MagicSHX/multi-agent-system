import json
import threading
from config import globalVar


from slackBotIo import Agent as SlackAgent
from agent import Agent as BrainAgent
from project import ProjectCenter


if __name__ == "__main__":
    # for project in ["project-test-1"]:
    for project in ["gamified-trading-cards"]:
        globalVar.project_context[project] = ProjectCenter(project)

    with open("slack-bot-config.json") as f:
        config = json.load(f)

    for a in config["agents"]:
        SlackAgent(a["name"], a["bot_token"], a["app_token"], a["keywords"]).start()
        BrainAgent(f"agents/{a['name']}.yaml").start()

    threading.Event().wait()
