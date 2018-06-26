# oncall_schedule_assistant

Work in progress. Currently will details, who is currently on call and when you/someone is next on call.

You must first create a Bot user in Slack. This bot will then listen for RTM messages from that user and act acordingly.

You must export the following env vars for authentication to Slack and PagerDuty: SLACK_BOT_TOKEN, PD_BOT_TOKEN

Associated keys must have correct perms to read from Slack channels and PagerDuty schedules.

Example Usage:
(call using slack Bot username)
@oc_assistant who is on call now?
@oc_assistant who is next on call?
@oc_assistant when am i next on call?

Next step is to allow on call engineers to swap shifts via using the oc_assistant, by sending a shift swap approval to the shift owner. Upon approval by that engineer oc_assistant will swap the shifts.
