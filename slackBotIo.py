import json
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import queue
import traceback
from datetime import datetime

from config import globalVar
import certifi
import os

os.environ["SSL_CERT_FILE"] = certifi.where()

class SlackBot(threading.Thread):
    def __init__(self, name, bot_token, app_token, keywords):
        super().__init__(daemon=True)
        self.name = name
        self.keywords = keywords
        self.app = App(token=bot_token)
        self.app_token = app_token

        self.projects = []
        self._say_fns = {}  # project -> say fn
        self._seen_ts = set()  # dedupe events delivered via >1 listener

        globalVar.slack_msg_process_queue[self.name] = queue.Queue()
        globalVar.slack_msg_response_queue[self.name] = queue.Queue()

        self.bot_user_id = self._get_bot_user_id()

        print(f"[{self.name}] Bot User ID: {self.bot_user_id}")
        self._load_mappings()
        self.testing_projects = ["gamified-trading-cards-1"]  # TODO: remove this hardcoded testing project list


    def _get_bot_user_id(self):
        response = self.app.client.auth_test()
        print(f"[{self.name}] auth_test response: {response}")
        return response["user_id"]

    def _load_mappings(self):
        try:
            self.slack_user_id_name_mapping = {}
            self.slack_channel_id_name_mapping = {}

            for page in self.app.client.users_list():
                for member in page["members"]:
                    id = member.get("id")
                    real_name = member.get("real_name")
                    if real_name:
                        self.slack_user_id_name_mapping[id] = real_name

            for page in self.app.client.conversations_list(
                types="public_channel,private_channel"
            ):
                for ch in page["channels"]:
                    self.slack_channel_id_name_mapping[ch["id"]] = ch["name"]

            print(
                f"[{self.name}] Loaded {len(self.slack_user_id_name_mapping)} users, {len(self.slack_channel_id_name_mapping)} channels"
            )
        except Exception as e:
            print(f"[{self.name}] Failed to load mappings: {traceback.format_exc()}")
            self.slack_user_id_name_mapping = {}
            self.slack_channel_id_name_mapping = {}

    # def initate_new_project(self, project):
    #     if project not in self.projects:
    #         self.projects.append(project)

    def _process(self, event, say):
        slack_user_id_sender = event.get("user", "")
        # never react to our own posts — Slack echoes the bot's own messages back
        # as events; without this the agent processes itself and loops/re-thinks.
        if slack_user_id_sender == self.bot_user_id:
            return

        # dedupe: a single message can arrive via both app_mention and message
        ts = event.get("ts")
        if ts:
            if ts in self._seen_ts:
                return
            self._seen_ts.add(ts)
            if len(self._seen_ts) > 2000:
                self._seen_ts.clear()
        slack_channel_id = event.get("channel", "")
        slack_channel_name = self.slack_channel_id_name_mapping[slack_channel_id]
        project = slack_channel_name

        if project not in self.testing_projects:
            return  # TODO: remove this hardcoded testing project filter
        
        # TODO: handle missing mapping, maybe reload mappings
        if project not in self.projects:
            self.projects.append(project)

        self._say_fns[project] = say

        slack_user_name_sender = self.slack_user_id_name_mapping[slack_user_id_sender]
        event["slack_user_name_sender_name"] = slack_user_name_sender
        event["slack_channel_name"] = slack_channel_name

        # was this bot directly addressed? robust to the app_mention/message
        # dedupe race — the message event won't have type "app_mention", but its
        # text still contains our mention token.
        event["is_mention"] = (
            event.get("type") == "app_mention"
            or f"<@{self.bot_user_id}>" in event.get("text", "")
        )

        globalVar.slack_msg_process_queue[self.name].put(event)

    def slack_msg_receive(self):
        @self.app.event("app_mention")
        def handle_mention(event, say):
            print(f"[{self.name}] received event: {event}")
            self._process(event, say)

        @self.app.event("message")
        def handle(event, say):

            # record every channel message ONCE into shared global memory.
            # all agent bots receive the same event, so dedupe across bots by ts.
            ts = event.get("ts")
            if ts and ts not in globalVar.global_memory_seen_ts:
                globalVar.global_memory_seen_ts.add(ts)
                slack_channel_id = event.get("channel", "")
                slack_channel_name = self.slack_channel_id_name_mapping.get(slack_channel_id)
                if slack_channel_name:
                    formatted_msg = f"message by: {event.get('user')}: {event.get('text')}"
                    globalVar.global_memory.setdefault(slack_channel_name, []).append(formatted_msg)
                    # snapshot current global memory to a timestamped log file
                    ts_label = datetime.now().strftime("%H%M%S_%d%m%y")
                    os.makedirs("logs", exist_ok=True)
                    log_path = f"logs/current_global-memory_{ts_label}.log"
                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(
                            globalVar.global_memory[slack_channel_name],
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )


            # humans reach agents via plain messages; agents reach each other via
            # @mentions (handled by app_mention above). Ignore bot and system
            # (edit/delete/join) messages on this path so an agent never reacts
            # to its own or another bot's posts here.
            if event.get("bot_id") or event.get("subtype"):
                return
            self._process(event, say)

    def slack_msg_send(self):
        while True:
            response = globalVar.slack_msg_response_queue[self.name].get()

            project = response.get("project")
            say = self._say_fns.get(project)
            if not say:
                print(f"[{self.name}] No say() fn for project {project}")
                continue

            text = response.get("text")
            thread_ts = response.get("thread_ts")

            if thread_ts:
                say(text=text, thread_ts=thread_ts)
            else:
                say(text=text)

    def match(self, text):
        return any(kw in text.lower() for kw in self.keywords)

    def run(self):
        self.slack_msg_receive()
        threading.Thread(target=self.slack_msg_send, daemon=True).start()
        SocketModeHandler(self.app, self.app_token).start()


if __name__ == "__main__":
    with open("slack-bot-config.json") as f:
        config_slack_bot = json.load(f)

    slackBots = [
        SlackBot(a["name"], a["bot_token"], a["app_token"], a["keywords"])
        for a in config_slack_bot["agents"][:1]
    ]

    threading.Event().wait()
