import json
import random
import time
import traceback
from typing import Any, Tuple, Union, List, Dict

import commands as cmd
from chat import create_chat_message, chat_with_ai
from colorama import Fore, Style
from config import Config
from json_parser import fix_and_parse_json
from memory import get_memory
from spinner import Spinner



user_input = "Determine which next command to use, and respond using the format specified above:"


def print_to_console(title: str, title_color: str, content: Union[str, list], min_typing_speed: float = 0.05, max_typing_speed: float = 0.01) -> None:
    """Print content to the console with a colored title and simulate typing."""
    print(title_color + title + " " + Style.RESET_ALL, end="")
    if content:
        if isinstance(content, list):
            content = " ".join(content)
        words = content.split()
        for i, word in enumerate(words):
            print(word, end="", flush=True)
            if i < len(words) - 1:
                print(" ", end="", flush=True)
            typing_speed = random.uniform(min_typing_speed, max_typing_speed)
            time.sleep(typing_speed)
            min_typing_speed *= 0.95
            max_typing_speed *= 0.95
    print()


def parse_assistant_reply(assistant_reply: str) -> Tuple[str, Any]:
    """
    Parse the assistant's reply and extract the thoughts and command.

    assistant_reply (str): The assistants reply
    :return: A tuple with the assistant's thoughts and command as JSON objects
    """
    assistant_reply_json = fix_and_parse_json(assistant_reply)

    if isinstance(assistant_reply_json, str):
        try:
            assistant_reply_json = json.loads(assistant_reply_json)
        except json.JSONDecodeError as e:
            print_to_console(f"Error: Invalid JSON - {e}\n", Fore.RED, assistant_reply)
            assistant_reply_json = {}

    assistant_thoughts = assistant_reply_json.get("thoughts", {})
    command = assistant_reply_json.get("command", {})

    return assistant_thoughts, command


def execute_command(command_name: str, arguments: Any) -> str:
    """
    Execute the given command and return the result as a string.

    command_name (str): The name of the command
    arguments (any): The arguments for the command
    :return: The result of the command execution as a string
    """
    if command_name.lower().startswith("error"):
        result = f"Command {command_name} threw the following error: " + arguments
    elif command_name == "human_feedback":
        result = f"Human feedback: {user_input}"
    else:
        result = f"Command {command_name} returned: {cmd.execute_command(command_name, arguments)}"

    return result


def print_assistant_thoughts(assistant_reply: str, ai_name: str):
    try:
        # Parse and print Assistant response
        assistant_reply_json = fix_and_parse_json(assistant_reply)

        # Extract relevant information from the JSON response
        assistant_thoughts = assistant_reply_json.get("thoughts", {})
        assistant_thoughts_text = assistant_thoughts.get("text")
        # assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
        # assistant_thoughts_plan = assistant_thoughts.get("plan")
        # assistant_thoughts_criticism = assistant_thoughts.get("criticism")

        # Print extracted information
        print_to_console(f"\n{ai_name.upper()} THOUGHTS:", Fore.YELLOW, assistant_thoughts_text)
        # print_to_console("REASONING:", Fore.YELLOW, assistant_thoughts_reasoning)
        # print_plan(assistant_thoughts_plan)
        # print_to_console("CRITICISM:", Fore.YELLOW, assistant_thoughts_criticism)

    except json.decoder.JSONDecodeError:
        print_to_console("Error: Invalid JSON\n", Fore.RED, assistant_reply)

    # All other errors, return "Error: + error message"
    except Exception as e:
        call_stack = traceback.format_exc()
        print_to_console(f"Error: {e}\n", Fore.RED, call_stack)


def print_plan(assistant_thoughts_plan: Union[str, List[str], Dict[str, Any]]):
    if assistant_thoughts_plan:
        print_to_console("PLAN:", Fore.YELLOW, "")
        # If it's a list, join it into a string
        if isinstance(assistant_thoughts_plan, list):
            assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
        elif isinstance(assistant_thoughts_plan, dict):
            assistant_thoughts_plan = str(assistant_thoughts_plan)

        # Split the input_string using the newline character and dashes
        lines = assistant_thoughts_plan.split('\n')
        for line in lines:
            line = line.lstrip("- ")
            print_to_console("- ", Fore.GREEN, line.strip())


def construct_prompt(ai_name: str, project: str, constraints: str, commands: str, resources: str, evaluation: str) -> str:
    prompt_start = f"""Your decisions must always be made independently without seeking user assistance. Play to your strengths as an LLM and pursue elegant strategies."""
    directives_block = f"""
    CURRENT PROJECT:
    {project}

    CONSTRAINTS:
    {constraints}

    COMMANDS:
    {commands}

    RESOURCES:
    {resources}

    PERFORMANCE EVALUATION:
    {evaluation}

    You should only respond in JSON format as described below in the Python json.loads compatible format:

    RESPONSE FORMAT:
    {{
        "thoughts":
        {{
            "text": "thought",
            "reasoning": "reasoning",
            "plan": "- short bulleted\\n- list that conveys\\n- long-term plan",
            "criticism": "constructive self-criticism"
        }},
        "command": {{
            "name": "command name",
            "args":{{
                "arg name": "value"
            }}
        }}
    }}
    """
    full_prompt = f"You are {ai_name}, an AI designed to work on the CURRENT PROJECT using the available resources and those available online as needed.\n{prompt_start}\n\nDIRECTIVES:\n\n{directives_block}"
    return full_prompt


def main() -> None:
    cfg = Config()
    cfg.set_continuous_mode(True)

    # Research Backlog
    # Gather information on responsible gaming resources, initiatives, and support groups available in Maryland.
    # Develop a list of frequently asked questions (FAQs) specific to Maryland sports betting and online gambling.
    # Determine the legal status of real-money online casinos in Maryland and any related regulations.
    project = "Determine the most popular sports events to bet on in Maryland in 2023"

    constraints = """
    1. Exclusively use the commands listed in double quotes e.g. "command name"
    2. Function autonomously and without user guidance or assistance."""

    commands = """
    1. Fetch Next Research URL: "fetch_next_research_url", args: ""
    2. Browse Website: "browse_website", args: "url"
    3. No More Research URLs Remain: "mark_project_completed", args: ""
    """

    resources = "1. Internet access."

    evaluation = """
    1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities.
    2. Constructively self-criticize your big-picture behavior constantly.
    3. Reflect on past decisions and strategies to refine your approach.
    4. Every command has a cost, so be smart and efficient. Aim to complete tasks in the least number of steps."""

    ai_name = "Ana"

    prompt = construct_prompt(ai_name, project, constraints, commands, resources, evaluation)

    full_message_history = []
    next_action_count = 0

    memory = get_memory(cfg, init=True)
    print('Using memory of type: ' + memory.__class__.__name__)

    while True:
        with Spinner("Thinking... "):
            assistant_reply = chat_with_ai(
                prompt,
                user_input,
                full_message_history,
                memory,
                cfg.fast_token_limit, cfg.debug)

        assistant_thoughts, command = parse_assistant_reply(assistant_reply)
        print_assistant_thoughts(assistant_thoughts, ai_name)

        command_name = ''
        arguments = ''
        try:
            command_name, arguments = cmd.get_command(assistant_reply)
        except Exception as e:
            print_to_console("Error: \n", Fore.RED, str(e))

        print_to_console("NEXT ACTION: ", Fore.CYAN, f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}")

        result = execute_command(command_name, arguments)
        if next_action_count > 0:
            next_action_count -= 1

        memory_to_add = f"Assistant Reply: {assistant_reply} \nResult: {result} \nHuman Feedback: {user_input} "
        memory.add(memory_to_add)

        if result is not None:
            full_message_history.append(create_chat_message("system", result))
            print_to_console("SYSTEM: ", Fore.YELLOW, result)
        else:
            full_message_history.append(create_chat_message("system", "Unable to execute command"))
            print_to_console("SYSTEM: ", Fore.YELLOW, "Unable to execute command")


if __name__ == '__main__':
    main()
