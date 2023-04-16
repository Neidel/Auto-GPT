import json
import random
import commands as cmd
from memory import get_memory
import data
import chat
from colorama import Fore, Style
from spinner import Spinner
import time
import speak
from enum import Enum, auto
import sys
from config import Config
from json_parser import fix_and_parse_json
from ai_config import AIConfig
import traceback
import yaml
import argparse


def print_to_console(
        title,
        title_color,
        content,
        speak_text=False,
        min_typing_speed=0.05,
        max_typing_speed=0.01):
    global cfg
    if speak_text and cfg.speak_mode:
        speak.say_text(f"{title}. {content}")
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
            # type faster after each word
            min_typing_speed = min_typing_speed * 0.95
            max_typing_speed = max_typing_speed * 0.95
    print()


def print_assistant_thoughts(assistant_reply):
    global ai_name
    global cfg
    try:
        # Parse and print Assistant response
        assistant_reply_json = fix_and_parse_json(assistant_reply)

        # Check if assistant_reply_json is a string and attempt to parse it into a JSON object
        if isinstance(assistant_reply_json, str):
            try:
                assistant_reply_json = json.loads(assistant_reply_json)
            except json.JSONDecodeError as e:
                print_to_console("Error: Invalid JSON\n", Fore.RED, assistant_reply)
                assistant_reply_json = {}

        assistant_thoughts_reasoning = None
        assistant_thoughts_plan = None
        assistant_thoughts_criticism = None
        assistant_thoughts = assistant_reply_json.get("thoughts", {})
        assistant_thoughts_text = assistant_thoughts.get("text")
        current_triplet = []

        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")

        print_to_console(f"{ai_name.upper()} THOUGHTS:", Fore.YELLOW, assistant_thoughts_text)
        current_triplet.append(assistant_thoughts_text)

        print_to_console("REASONING:", Fore.YELLOW, assistant_thoughts_reasoning)
        current_triplet.append(assistant_thoughts_reasoning)

        if assistant_thoughts_plan:
            print_to_console("PLAN:", Fore.YELLOW, "")
            for step in assistant_thoughts_plan:
                step_name = step.get("name", "Unknown step")
                step_args = step.get("args", {})

                print_to_console(f"- {step_name}:", Fore.GREEN, "")
                for arg_key, arg_value in step_args.items():
                    print_to_console(f"  {arg_key}:", Fore.CYAN, str(arg_value))

        print_to_console("CRITICISM:", Fore.YELLOW, assistant_thoughts_criticism)
        current_triplet.append(assistant_thoughts_criticism)




    except json.decoder.JSONDecodeError:
        print_to_console("Error: Invalid JSON\n", Fore.RED, assistant_reply)

    # All other errors, return "Error: + error message"
    except Exception as e:
        call_stack = traceback.format_exc()
        print_to_console("Error: \n", Fore.RED, call_stack)


def bootstrap_prompt():
    ai_goals = ["Increase net worth", "Grow Twitter Account", "Develop and manage multiple businesses autonomously"]
    prompt_start = """Your decisions must always be made independently without seeking user assistance. Play to your strengths as an LLM and pursue elegant strategies."""

    full_prompt = f"You are Issola, an AI designed to fetch a task and complete it using the available resources and those available online as needed.\n{prompt_start}\n\nGOALS:\n\n"
    for i, goal in enumerate(ai_goals):
        full_prompt += f"{i+1}. {goal}\n"

    return full_prompt


# create an action log to keep track of the actions performed for the current task
def construct_prompt():
    prompt_start = """Your decisions must always be made independently without seeking user assistance. Play to your strengths as an LLM and pursue elegant strategies."""
    directives_block = """
    
    YOUR TASK:
    %s
    
    CURRENT TASK NOTES:
    %s
    
    CONSTRAINTS:
    
    1. Exclusively use the commands listed in double quotes e.g. "command name"
    2. Function autonomously and without user guidance or assistance.
    
    COMMANDS:
    
    1. Google Search: "google", args: "input": "<search>"
    2. Browse Website: "browse_website", args: "url": "<url>", "desired_information": "<desired_information>"
    3. Write to file: "write_to_file", args: "file": "<file>", "text": "<text>"
    5. Mark this task as complete: "complete_task", args""
    6. Add Mission Critical Notes Regarding the Current Task: "add_mission_critical_notes", args: "notes": "<notes>"
    
    RESOURCES:
    
    1. Internet access.
    
    PERFORMANCE EVALUATION:
    
    1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities. 
    2. Constructively self-criticize your big-picture behavior constantly.
    3. Reflect on past decisions and strategies to refine your approach.
    4. Every command has a cost, so be smart and efficient. Aim to complete tasks in the least number of steps.
    
    You should only respond in JSON format as described below in the Python json.loads compatible format:
    
    RESPONSE FORMAT EXAMPLE:
    Reminder: Dont forget to make the commands dictionary a list of dictionaries.
    {
        "thoughts": {
            "text": "To research current laws governing online betting in Maryland, I will need to browse the website of the Maryland State Lottery and Gaming Control Agency. I can search for any potential changes or updates on their site as well as on news sites.",
            "reasoning": "Since the task involves legal research, browsing the official website of the governing agency allows for the most credible and up-to-date information. Additionally, news sites may provide insight into proposed changes that have not yet been enacted.",
            "plan": "browse_website, write_to_file",
            "criticism": "I may need to review multiple sources to ensure accuracy and completeness of information."
        },
        "commands": [
            {
                "name": "browse_website",
                "args": {
                    "url": "https://www.mdlottery.com/about-us/state-agency/",
                    "desired_information": "online betting laws maryland"
                }
            },
            {
                "name": "write_to_file",
                "args": {
                    "file": "maryland_betting_laws.txt",
                    "text": "Summary of Maryland online betting laws:\nAccording to the Maryland State Lottery and Gaming Control Agency, online sports betting is not currently legal in Maryland. However, legislation has been introduced that would allow for online sports betting in the state. The bill would allow for up to 30 online sports betting licenses and would include provisions for responsible gambling protections. The bill has not yet been enacted as of April 2023.\n"
                }
            },
            {
                "name": "complete_task",
                "args": {}
            }
        ]
    }
    """ % (cmd.current_task_report(), cmd.current_task_notes_report())
    full_prompt = f"You are Issola, an AI designed to fetch a task and complete it using the available resources and those available online as needed.\n{prompt_start}\n\nDIRECTIVES:\n\n{directives_block}"

    return full_prompt


def prompt_user():
    ai_name = ""
    # Construct the prompt
    print_to_console(
        "Welcome to Auto-GPT! ",
        Fore.GREEN,
        "Enter the name of your AI and its role below. Entering nothing will load defaults.",
        speak_text=True)

    # Get AI Name from User
    print_to_console(
        "Name your AI: ",
        Fore.GREEN,
        "For example, 'Entrepreneur-GPT'")
    ai_name = input("AI Name: ")
    if ai_name == "":
        ai_name = "Entrepreneur-GPT"

    print_to_console(
        f"{ai_name} here!",
        Fore.LIGHTBLUE_EX,
        "I am at your service.",
        speak_text=True)

    # Get AI Role from User
    print_to_console(
        "Describe your AI's role: ",
        Fore.GREEN,
        "For example, 'an AI designed to autonomously develop and run businesses with the sole goal of increasing your net worth.'")
    ai_role = input(f"{ai_name} is: ")
    if ai_role == "":
        ai_role = "an AI designed to autonomously develop and run businesses with the sole goal of increasing your net worth."

    # Enter up to 5 goals for the AI
    print_to_console(
        "Enter up to 5 goals for your AI: ",
        Fore.GREEN,
        "For example: \nIncrease net worth, Grow Twitter Account, Develop and manage multiple businesses autonomously'")
    print("Enter nothing to load defaults, enter nothing when finished.", flush=True)
    ai_goals = []
    for i in range(5):
        ai_goal = input(f"{Fore.LIGHTBLUE_EX}Goal{Style.RESET_ALL} {i+1}: ")
        if ai_goal == "":
            break
        ai_goals.append(ai_goal)
    if len(ai_goals) == 0:
        ai_goals = ["Increase net worth", "Grow Twitter Account",
                    "Develop and manage multiple businesses autonomously"]

    config = AIConfig(ai_name, ai_role, ai_goals)
    return config

def parse_arguments():
    global cfg
    cfg.set_continuous_mode(False)
    cfg.set_speak_mode(False)
    
    parser = argparse.ArgumentParser(description='Process arguments.')
    parser.add_argument('--continuous', action='store_true', help='Enable Continuous Mode')
    parser.add_argument('--speak', action='store_true', help='Enable Speak Mode')
    parser.add_argument('--debug', action='store_true', help='Enable Debug Mode')
    parser.add_argument('--gpt3only', action='store_true', help='Enable GPT3.5 Only Mode')
    args = parser.parse_args()

    if args.continuous:
        cfg.set_continuous_mode(True)

    if args.speak:
        print_to_console("Speak Mode: ", Fore.GREEN, "ENABLED")
        cfg.set_speak_mode(True)

    if args.gpt3only:
        print_to_console("GPT3.5 Only Mode: ", Fore.GREEN, "ENABLED")
        cfg.set_smart_llm_model(cfg.fast_llm_model)

    if args.debug:
        print_to_console("Debug Mode: ", Fore.GREEN, "ENABLED")
        cfg.set_debug_mode(True)


cfg = Config()
parse_arguments()
ai_name = ""

# print(prompt)
# Initialize variables
full_message_history = []
result = None
next_action_count = 0
# Make a constant:
user_input = "Determine which next command to use, and respond using the format specified:"

# Initialize memory and make sure it is empty.
# this is particularly important for indexing and referencing pinecone memory
memory = get_memory(cfg, init=True)
print('Using memory of type: ' + memory.__class__.__name__)


def remember(assistant_reply, result):
    memory_to_add = f"Assistant Reply: {assistant_reply} " \
                    f"\nResult: {result} "

    memory.add(memory_to_add)


def print_to_console(prefix, color, text):
    print(color + prefix + text + Fore.RESET)


def display_plan(assistant_thoughts_plan):
    if assistant_thoughts_plan:
        print_to_console("PLAN:", Fore.YELLOW, "")
        for step in assistant_thoughts_plan:
            step_name = step.get("name", "Unknown step")
            step_args = step.get("args", {})

            print_to_console(f"- {step_name}:", Fore.GREEN, "")
            for arg_key, arg_value in step_args.items():
                print_to_console(f"  {arg_key}:", Fore.CYAN, str(arg_value))



def print_assistant_thoughts(assistant_reply):
    try:
        assistant_reply_dict = fix_and_parse_json(assistant_reply)
        assistant_thoughts_plan = assistant_reply_dict.get("plan", None)
        display_plan(assistant_thoughts_plan)
    except json.decoder.JSONDecodeError as e:
        print_to_console("Error: \n", Fore.RED, str(e))



# Interaction Loop
while True:
    prompt = construct_prompt()

    # Send message to AI, get response
    with Spinner("Thinking... "):
        assistant_reply = chat.chat_with_ai(
            prompt,
            user_input,
            full_message_history)

    # Print Assistant thoughts
    print(f"Response: {assistant_reply}")
    print_assistant_thoughts(assistant_reply)

    # Get commands and arguments
    try:
        commands = cmd.get_commands(assistant_reply)
    except Exception as e:
        print_to_console("Error: \n", Fore.RED, str(e))

    for command in commands:
        command_name = command["name"]
        arguments = command["args"]
        # Print command
        print_to_console(
            "NEXT ACTION: ",
            Fore.CYAN,
            f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}")

        # Execute command
        if command_name.lower().startswith("error"):
            result = f"Command {command_name} threw the following error: " + arguments
        else:
            result = f"Command {command_name} returned: {cmd.execute_command(command_name, arguments)}"
            if next_action_count > 0:
                next_action_count -= 1

        # Check if there's a result from the command append it to the message
        # history
        if result is not None:
            full_message_history.append(chat.create_chat_message("system", result))
            print_to_console("SYSTEM: ", Fore.YELLOW, result)
        else:
            full_message_history.append(
                chat.create_chat_message(
                    "system", "Unable to execute command"))
            print_to_console("SYSTEM: ", Fore.YELLOW, "Unable to execute command")

