import os
import time
import re
import yaml
import logging
from datetime import datetime
from slackclient import SlackClient
from pagerduty import PagerDutySchedule


def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if not (not (event["type"] == "message") or "subtype" in event):
            user_id, message = parse_direct_mention(event["text"])
            if user_id == slack_bot_id:
                return message, event["channel"], event["user"]
    return None, None, None


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

# TODO Clean up this section
def handle_command(command, channel, user_email, pd):
    """
        Executes bot command if the command is known
    """

    default_response = "I'm afraid i don't understand. Try saying hello, or opening a question with when, who or what"

    logging.info('handling command: "{}" from {}'.format(command, user_email))
    response = None

    if command.startswith('when'):
        if 'am i' in command:
            pd_id, pd_user = pd.lookup_user_name(user_email)
            eng_name, start, end = pd.when_is_on_call(pd_user)
            response = "You, <@{}> are next on call from {} until {}".format(user_id, start, end)
        elif 'on call' in command:
            slack_user = re.match('^.*?is\s(.*?)(\snext|\son).*?', command)
            eng_name, start, end = pd.when_is_on_call(slack_user.group(1))
            response = "{} is next on call from {} until {}".format(eng_name, start, end)
        else:
            response = "¯\_(ツ)_/¯"
    elif command.startswith('who'):
        if 'next' in command:
            on_call = pd.next_on_call()
            response = "{}".format(on_call)
        elif 'on call' in command:
            on_call = pd.who_is_on_call_now()
            response = "{} is on call now".format(on_call)
        else:
            response = "¯\_(ツ)_/¯"
    elif command.startswith('what'):
        if 'time is it' in command:
            response = 'It\'s {} to be precise'.format(str(datetime.now().time()))
        else:
            response = "¯\_(ツ)_/¯"
    elif command.startswith('hello'):
        response = 'Hello <@{}>!'.format(user_id)
    elif command.startswith('but'):
        response = "¯\_(ツ)_/¯"
    elif command.startswith('why'):
        response = "¯\_(ツ)_/¯"

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )


if __name__ == "__main__":

    logging.basicConfig(level='INFO', format='%(asctime)s - %(levelname)s - %(message)s')

    # Load the config from YAML
    open_config = open('{}/config.yaml'.format(os.path.dirname(os.path.abspath(__file__))))
    loaded_config = yaml.load(open_config)
    schedule_name = loaded_config['Config']['schedule_name']
    timezone = loaded_config['Config']['timezone']

    # Hardcoded Constant Config
    RTM_READ_DELAY = 1  # 1 second delay between reading from RTM
    MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

    slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
    slack_bot_id = None
    pd_token = os.environ.get('PD_BOT_TOKEN')

    # Setup pd connection
    pd = PagerDutySchedule(pd_token, timezone)
    pd.set_schedule(schedule_name)

    if slack_client.rtm_connect(with_team_state=False):
        logging.info('OCSA initiated and running!')
        slack_bot_id = slack_client.api_call('auth.test')['user_id']
        while True:
            command, channel, user_id = parse_bot_commands(slack_client.rtm_read())
            if command:
                user_email = slack_client.api_call('users.info', user=user_id)['user']['profile']['email']
                handle_command(command, channel, user_email, pd)
            time.sleep(RTM_READ_DELAY)
    else:
        logging.error('Connection failed. Exception traceback printed above.')

