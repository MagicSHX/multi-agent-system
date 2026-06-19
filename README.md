# multi-agent-system


# workflow: slack <> LLM agent
    Slack event → SlackAgent._process → slack_msg_process_queue ─┐
                                                                 ▼
                            BrainAgent.process → brain.run() → slack_msg_response_queue ─┐
                                                                                         ▼  
                                                                SlackAgent.slack_msg_send → say() → Slack