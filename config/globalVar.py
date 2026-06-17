slack_msg_process_queue = {}
slack_msg_response_queue = {}

project_context = {}
global_memory = {}
global_memory_seen_ts = set()   # ts of messages already recorded (shared across all bots)

llm_cost_tracker = {}
