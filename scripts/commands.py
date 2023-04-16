import browse
import json
import time
from memory import get_memory
import datetime
import requests
import agent_manager as agents
import speak
from config import Config
import ai_functions as ai

from file_operations import read_file, write_to_file, append_to_file, delete_file, search_files
from execute_code import execute_python_file
from json_parser import fix_and_parse_json
from image_gen import generate_image
from duckduckgo_search import ddg

from llm_utils import create_chat_completion

from datetime import datetime, timedelta


cfg = Config()

mem = get_memory(cfg, init=True)

executed_urls = []

task_queue = []

current_task_notes = ''
completed_tasks = []
last_result = ''

visited_urls = []

ERROR_PREFIX = "Error:"
JULIAN_YEAR_OFFSET = 4716
JULIAN_DAY_OFFSET = 1524
MONTH_OFFSET = 0.6

GOOGLE_SEARCH_URL = "https://google-web-search1.p.rapidapi.com/"
RAPIDAPI_KEY = "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c"
RAPIDAPI_HOST = "google-web-search1.p.rapidapi.com"


def get_command(response):
    try:
        response_json = fix_and_parse_json(response)

        command = response_json.get("command")
        if command is None:
            return ERROR_PREFIX, "Missing 'command' object in JSON"

        command_name = command.get("name")
        if command_name is None:
            return ERROR_PREFIX, "Missing 'name' field in 'command' object"

        arguments = command.get("args", {})
        return command_name, arguments
    except json.decoder.JSONDecodeError:
        return ERROR_PREFIX, "Invalid JSON"
    except Exception as e:
        return ERROR_PREFIX, str(e)


def execute_command(command_name, arguments):
    memory = get_memory(cfg)

    # Define command handlers as a dictionary of functions
    command_handlers = {
        "google": lambda args: search_google_raw(args["input"]),
        "memory_add": lambda args: memory.add(args["string"]),
        "fetch_related_memories": lambda args: memory.get_relevant(args["string"]),
        "start_agent": lambda args: start_agent(args["name"], args["task"], args["prompt"]),
        "message_agent": lambda args: message_agent(args["key"], args["message"]),
        "list_agents": lambda args: list_agents(),
        "delete_agent": lambda args: delete_agent(args["key"]),
        "read_file": lambda args: read_file(args["file"]),
        "write_to_file": lambda args: write_to_file(args["file"], args["text"]),
        "append_to_file": lambda args: append_to_file(args["file"], args["text"]),
        "delete_file": lambda args: delete_file(args["file"]),
        "search_files": lambda args: search_files(args["directory"]),
        "evaluate_code": lambda args: ai.evaluate_code(args["code"]),
        "improve_code": lambda args: ai.improve_code(args["suggestions"], args["code"]),
        "write_tests": lambda args: ai.write_tests(args["code"], args.get("focus")),
        "execute_python_file": lambda args: execute_python_file(args["file"]),
        "browse_website": lambda args: browse_website(args["url"]),
        "get_text_summary": lambda args: get_text_summary(args["url"]),
        "get_hyperlinks": lambda args: get_hyperlinks(args["url"]),
        "generate_image": lambda args: generate_image(args["prompt"]),
        "ask_user": lambda args: ask_user(args["prompt"]) if 'ask_user' in command_name else None,
        "ask_myself": lambda args: ask_myself(args["prompt"]) if 'ask_myself' in command_name else None,
        "take_break": lambda args: take_break(),
        "task_complete": lambda args: shutdown(),
        "mark_project_completed": lambda args: shutdown(),
    }

    # Execute the appropriate command handler based on the command name
    handler = command_handlers.get(command_name)
    if handler is not None:
        try:
            return handler(arguments)
        except Exception as e:
            return "Error: " + str(e)
    else:
        return f"Unknown command '{command_name}'. Please refer to the 'COMMANDS' list for available commands and only respond in the specified JSON format."


# -------------------------------------------


def ask_myself(prompt):
    # print('Asking myself: ' + prompt)
    assistant_reply = create_chat_completion(
        model='gpt-3.5-turbo',
        messages=[{"role": "user", "content": prompt}, ]
    )
    # print(f'Assistant Thinks: {assistant_reply}')
    return assistant_reply


def extract_tasks(prompt):
    return ask_myself(f"Users message: {prompt} \n Task mapping: Create a mapping of user intents to associated subtasks. Each intent can be associated with a list of subtasks that must be completed to address the user's request. For example, if the user intent is 'recommendation', the subtasks might include 'identify_preferences', 'gather_options', and 'present_recommendations'")


def extract_context(prompt):
    return ask_myself(f"Users message: {prompt} \n Context extraction: Extract contextual information from the user's input that can help guide the execution of subtasks. This might involve identifying relevant keywords, entities, or relationships within the text.")


def determine_subtask_priorities(prompt, tasks):
    return ask_myself(f"Users message: {prompt} \n Extrapolated Tasks: {tasks} \n Subtask prioritization: Prioritize the order in which subtasks should be executed based on the user's input and the extracted context. Some subtasks may depend on the completion of others, or their priority may be determined by the user's specific requirements.")


def ask_user(prompt):
    print(prompt)
    response = input()
    tasks = extract_tasks(response)
    context = extract_context(response)
    prioritized = determine_subtask_priorities(response, tasks)
    internal_reasoning = f'Users Response: {response} \n Internal reasoning: {tasks} \n Prioritized Tasks: {prioritized} \n Internal Context Assessment: {context} \n'
    print(internal_reasoning)
    return internal_reasoning


# -------------------------------------------


def is_valid_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def commit_memory(string):
    _text = f"""Committing memory with string "{string}" """
    mem.permanent_memory.append(string)
    return _text


def delete_memory(key):
    if 0 <= key < len(mem.permanent_memory):
        del mem.permanent_memory[key]
        message = f"Deleting memory with key {key}"
        print(message)
        return message
    else:
        print("Invalid key, cannot delete memory.")
        return None


def overwrite_memory(key, string):
    # Check if the key is a valid integer
    if is_valid_int(key):
        key_int = int(key)
        # Check if the integer key is within the range of the permanent_memory list
        if 0 <= key_int < len(mem.permanent_memory):
            _text = "Overwriting memory with key " + str(key) + " and string " + string
            # Overwrite the memory slot with the given integer key and string
            mem.permanent_memory[key_int] = string
            print(_text)
            return _text
        else:
            print(f"Invalid key '{key}', out of range.")
            return None
    # Check if the key is a valid string
    elif isinstance(key, str):
        _text = "Overwriting memory with key " + key + " and string " + string
        # Overwrite the memory slot with the given string key and string
        mem.permanent_memory[key] = string
        print(_text)
        return _text
    else:
        print(f"Invalid key '{key}', must be an integer or a string.")
        return None


# -------------------------------------------


def start_agent(name, task, prompt, model=cfg.fast_llm_model):
    global cfg

    # Remove underscores from name
    voice_name = name.replace("_", " ")

    first_message = f"""You are {name}.  Respond with: "Acknowledged"."""
    agent_intro = f"{voice_name} here, Reporting for duty!"

    # Create agent
    if cfg.speak_mode:
        speak.say_text(agent_intro, 1)
    key, ack = agents.create_agent(task, first_message, model)

    if cfg.speak_mode:
        speak.say_text(f"Hello {voice_name}. Your task is as follows. {task}.")

    # Assign task (prompt), get response
    agent_response = message_agent(key, prompt)

    return f"Agent {name} created with key {key}. First response: {agent_response}"


def message_agent(key, message):
    global cfg

    # Check if the key is a valid integer
    if is_valid_int(key):
        agent_response = agents.message_agent(int(key), message)
    # Check if the key is a valid string
    elif isinstance(key, str):
        agent_response = agents.message_agent(key, message)
    else:
        return "Invalid key, must be an integer or a string."

    # Speak response
    if cfg.speak_mode:
        speak.say_text(agent_response, 1)
    return agent_response


def list_agents():
    return agents.list_agents()


def delete_agent(key):
    result = agents.delete_agent(key)
    if not result:
        return f"Agent {key} does not exist."
    return f"Agent {key} deleted."


# -------------------------------------------


def google_search(query, num_results=3):
    search_results = []
    for j in ddg(query, max_results=num_results):
        search_results.append(j)

    return json.dumps(search_results, ensure_ascii=False, indent=4)


def page_processed(browsed_url):
    if browsed_url in executed_urls:
        return True
    else:
        executed_urls.append(browsed_url)
        return False


def google_official_search(query, num_results=8):
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import json

    try:
        # Get the Google API key and Custom Search Engine ID from the config file
        api_key = cfg.google_api_key
        custom_search_engine_id = cfg.custom_search_engine_id

        # Initialize the Custom Search API service
        service = build("customsearch", "v1", developerKey=api_key)

        # Send the search query and retrieve the results
        result = service.cse().list(
            q=query,
            cx=custom_search_engine_id,
            num=num_results,
            dateRestrict='m:3'  # Restrict search results to the last 3 months
        ).execute()

        # Extract the search result items from the response
        search_results = result.get("items", [])

        # Create a list of only the URLs from the search results
        # search_results_links = [item["link"] for item in search_results]

        # Revised version that checks executed_urls to make sure we don't repeat URLs we have already processed.
        search_results_links = [item["link"] for item in search_results if not page_processed(item["link"])]

    except HttpError as e:
        # Handle errors in the API call
        error_details = json.loads(e.content.decode())

        # Check if the error is related to an invalid or missing API key
        if error_details.get("error", {}).get("code") == 403 and "invalid API key" in error_details.get("error", {}).get("message", ""):
            return "Error: The provided Google API key is invalid or missing."
        else:
            return f"Error: {e}"

    # Return the list of search result URLs
    return search_results_links


def browse_website(url):
    if url not in visited_urls:
        visited_urls.append(url)
        summary = get_text_summary(url)
        result = f"""Website Content Summary: {summary}"""
        return result
    else:
        return "This URL has already been visited. Proceed to another URL on the list."


def get_tldr(target):
    url = "https://tldr-text-analysis.p.rapidapi.com/summarize/"

    querystring = {"text": target, "max_sentences": "20"}

    headers = {
        "X-RapidAPI-Key": "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c",
        "X-RapidAPI-Host": "tldr-text-analysis.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    # print(response.text)
    return response.text


def extract_sources(file_path):
    sources = []
    with open(file_path, 'r') as file:
        for line in file:
            # Check if the line starts with "Source:"
            if line.startswith("Source:"):
                # Extract the URL by removing the "Source:" prefix and stripping whitespace
                url = line[len("Source:"):].strip()
                sources.append(url)
    return sources


def get_text_summary(url):
    if url not in KNOWN_RESEARCH_SOURCES:
        KNOWN_RESEARCH_SOURCES.append(url)
        text = browse.scrape_text(url)
        summary = browse.summarize_text(text)
        if '404' not in summary:
            with open("research.txt", "a") as f:
                f.write(f'Source: {url}\nSummary:\n{summary}\n\n')

        return """ "Result" : """ + summary
    else:
        return "This URL has already been visited and researched. Proceed to another URL on the list."


def get_hyperlinks(url):
    link_list = browse.scrape_links(url)
    return link_list


def scrub_google_results(url_list):
    cleaned_list = [url for url in url_list if url not in executed_urls and url not in visited_urls]
    return cleaned_list


def gregorian_to_julian(date):
    year, month, day = date.year, date.month, date.day

    if month < 3:
        year -= 1
        month += 12

    # Calculate the number of leap years between 0 and the current year (exclusive)
    century = year // 100
    leap_years = century // 4 - 2 * century + 1

    # Calculate the Julian day using the formula
    julian_day = int(365.25 * year) + int(MONTH_OFFSET * (month + 1)) + day + leap_years - JULIAN_DAY_OFFSET

    # Calculate the Julian year using the formula
    julian_year = JULIAN_YEAR_OFFSET + year + int((month - 2) / 12)

    return julian_day + 365 * (julian_year - 1) + int((julian_year - 1) / 4)


def calculate_julian_strings():
    current_date = datetime.now()
    start_date = current_date - timedelta(weeks=52)

    current_julian = gregorian_to_julian(current_date)
    start_julian = gregorian_to_julian(start_date)

    # Construct a Google search query that matches results within the last year
    # by specifying the Julian dates of the start and end of the date range.
    date_range_query = f"daterange:{start_julian}-{current_julian}"
    return date_range_query


def search_google_raw(query, num_results=3):
    query_params = {"query": query, "limit": num_results, "related_keywords": "false"}
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    response = requests.get(GOOGLE_SEARCH_URL, headers=headers, params=query_params)
    results = [result["url"] for result in response.json().get("results", [])]
    print(f"Searched for: {query}\nFound {len(results)} results\n{results}")
    return results


def search_google(query, num_results=3):
    raw_results = scrub_google_results(search_google_raw(query, num_results))

    return raw_results


# -------------------------------------------


def shutdown():
    print("Shutting down...")
    quit()


def take_break():
    print("Taking a break...")
    time.sleep(1800)
    return "Break over"


KNOWN_RESEARCH_SOURCES = extract_sources('research.txt')
