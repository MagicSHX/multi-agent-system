import os
import certifi
import json
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import queue

os.environ["SSL_CERT_FILE"] = certifi.where()


from config import globalVar


class Agent(threading.Thread):
    def __init__(self, name, bot_token, app_token, keywords):
        super().__init__(daemon=True)
        self.name = name
        self.keywords = keywords
        self.app = App(token=bot_token)
        self.app_token = app_token

        self.projects = []
        self._say_fns = {}  # project -> say fn

        # own identity (filled in _load_mappings) — used to ignore our own posts
        self.bot_user_id = None
        self.bot_id = None
        self._seen_ts = set()  # dedupe events delivered via >1 listener

        globalVar.slack_msg_process_queue[self.name] = queue.Queue()
        globalVar.slack_msg_response_queue[self.name] = queue.Queue()

        self._load_mappings()

    def _load_mappings(self):
        try:
            self.user_email = {}
            for page in self.app.client.users_list():
                for member in page["members"]:
                    profile = member.get("profile", {})
                    email = profile.get("email")
                    if email:
                        self.user_email[member["id"]] = email

            self.channel_name = {}
            for page in self.app.client.conversations_list(
                types="public_channel,private_channel"
            ):
                for ch in page["channels"]:
                    self.channel_name[ch["id"]] = ch["name"]

            auth = self.app.client.auth_test()
            self.bot_user_id = auth.get("user_id")
            self.bot_id = auth.get("bot_id")

            print(
                f"[{self.name}] Loaded {len(self.user_email)} users, {len(self.channel_name)} channels "
                f"(bot_user_id={self.bot_user_id})"
            )
        except Exception as e:
            print(f"[{self.name}] Failed to load mappings: {e}")
            self.user_email = {}
            self.channel_name = {}

    def initate_new_project(self, project):
        if project not in self.projects:
            self.projects.append(project)

    def _process(self, event, say):
        # ignore our own posts (by user id or bot id) so the agent never
        # reacts to itself and loops. NOTE: messages from *other* agents are
        # still processed — only self is dropped.
        if event.get("user") == self.bot_user_id or (
            self.bot_id and event.get("bot_id") == self.bot_id
        ):
            return
        # ignore edits/deletes/joins and other non-message system events
        if event.get("subtype") in {
            "message_changed", "message_deleted", "channel_join", "channel_leave",
        }:
            return
        # dedupe: a human @mention fires both app_mention and message listeners
        ts = event.get("ts")
        if ts:
            if ts in self._seen_ts:
                return
            self._seen_ts.add(ts)
            if len(self._seen_ts) > 2000:
                self._seen_ts.clear()

        print(f"\n\n######\n{event}\n######\n\n")
        # project = "project-test-1"  # TODO
        project = "gamified-trading-cards"  # TODO

        if project not in self.projects:
            self.initate_new_project(project)

        self._say_fns[project] = say

        user_id = event.get("user", "")
        channel_id = event.get("channel", "")
        event["user_email"] = self.user_email.get(user_id, "")
        event["channel_name"] = self.channel_name.get(channel_id, "")

        globalVar.slack_msg_process_queue[self.name].put(event)

    def slack_msg_receive(self):
        @self.app.event("app_mention")
        def handle_mention(event, say):
            print(f"[{self.name}] mentioned:", event)
            self._process(event, say)

        @self.app.event("message")
        def handle(event, say):
            # only the lead listens to every channel message; self/dedupe/system
            # filtering is handled inside _process()
            if self.name in ["project_lead"]:
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
    with open("agents.json") as f:
        config = json.load(f)

    agents = [
        Agent(a["name"], a["bot_token"], a["app_token"], a["keywords"])
        for a in config["agents"]
    ]

    threading.Event().wait()
