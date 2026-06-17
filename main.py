import json
import threading
from config import globalVar


from slackBotIo import SlackBot
from agent import Agent
from project import ProjectCenter


if __name__ == "__main__":
    for project in ["project-test-1", "gamified-trading-cards"]:
        globalVar.project_context[project] = ProjectCenter(project)

    with open("slack-bot-config.json") as f:
        config = json.load(f)

    for a in config["agents"]:
        SlackBot(a["name"], a["bot_token"], a["app_token"], a["keywords"]).start()
        Agent(f"agents/{a['name']}.yaml").start()

    threading.Event().wait()
