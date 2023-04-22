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

from tqdm import tqdm

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
        "browse_website_with_conditions": lambda args: browse_website(args["url"]),
        "get_text_summary": lambda args: get_text_summary(args["url"]),
        "get_hyperlinks": lambda args: get_hyperlinks(args["url"]),
        "generate_image": lambda args: generate_image(args["prompt"]),
        "ask_user": lambda args: ask_user(args["prompt"]) if 'ask_user' in command_name else None,
        "ask_myself": lambda args: ask_myself(args["prompt"]) if 'ask_myself' in command_name else None,
        "take_break": lambda args: take_break(),
        "task_complete": lambda args: shutdown(),
        "mark_project_completed": lambda args: shutdown(),
        "start_a_research_project": lambda args: get_next_research_link(),
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


CURRENT_RESEARCH_OBJECTIVE = ''
CURRENT_RESEARCH_URLS = []
CURRENT_RESEARCH_CONTEXT = ''
GOOGLE_SEARCH_URL = "https://google-web-search1.p.rapidapi.com/"
RAPIDAPI_KEY = "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c"
RAPIDAPI_HOST = "google-web-search1.p.rapidapi.com"


def search_google_raw(query, num_results=3):
    query_params = {"query": query, "limit": num_results, "related_keywords": "false"}
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": RAPIDAPI_HOST}
    response = requests.get(GOOGLE_SEARCH_URL, headers=headers, params=query_params)
    results = [result["url"] for result in response.json().get("results", [])]
    # print(f"Searched for: {query}\nFound {len(results)} results\n{results}")
    return results


def get_text_summary_with_conditions(url, desired_information):
    if url not in KNOWN_RESEARCH_SOURCES:
        KNOWN_RESEARCH_SOURCES.append(url)
        print(f"Processing new research source: {url}")
        text = browse.scrape_text(url)
        summary = browse.summarize_text_with_conditions(text, desired_information)
        if '404' not in summary:
            with open("research.txt", "a") as f:
                f.write(f'Source: {url}\nSummary:\n{summary}\n\n')

        return summary
    else:
        return "This URL has already been visited and researched. Proceed to another URL on the list."


def split_text(text, max_length=8192):
    paragraphs = text.split("\n")
    current_length = 0
    current_chunk = []

    for paragraph in paragraphs:
        if current_length + len(paragraph) + 1 <= max_length:
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 1
        else:
            yield "\n".join(current_chunk)
            current_chunk = [paragraph]
            current_length = len(paragraph) + 1

    if current_chunk:
        yield "\n".join(current_chunk)



def scrape_text(url):
    response = requests.get(url, headers=cfg.user_agent_header)

    # Check if the response contains an HTTP error
    if response.status_code >= 400:
        return "Error: HTTP " + str(response.status_code) + " error"

    soup = BeautifulSoup(response.text, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text



def summarize_text_with_conditions(text, desired_conditions):
    if not text:
        return "Error: No text to summarize"

    text_length = len(text)
    print(f"Text length: {text_length} characters")

    summaries = []
    chunks = list(split_text(text, 4097))

    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i + 1} / {len(chunks)}")
        messages = [create_message(chunk)]

        summary = create_chat_completion(
            model=cfg.fast_llm_model,
            messages=messages,
            max_tokens=1000,
        )
        summaries.append(summary)

    print(f"Summarized {len(chunks)} chunks.")

    combined_summary = "\n".join(summaries)

    final_summary = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": combined_summary}, {"role": "system", "content": f"Constraints: Please provide a detailed summary of facts related to {desired_conditions}]"}],
        max_tokens=2000,
    )

    return final_summary


def browse_website(url, desired_information=None):
    if url not in visited_urls:
        visited_urls.append(url)
        if desired_information is None:
            summary = get_text_summary(url)
            result = f"""Website Content Summary: {summary}"""
            return result
        else:
            result = get_text_summary_with_conditions(url, desired_information)
            return result
    else:
        return "This URL has already been visited. Proceed to another URL on the list."


def set_research_objective(desired_objective):
    global CURRENT_RESEARCH_OBJECTIVE
    CURRENT_RESEARCH_OBJECTIVE = desired_objective


def extract_research_context():
    global CURRENT_RESEARCH_OBJECTIVE
    global CURRENT_RESEARCH_CONTEXT
    message = f"Users research objective: {CURRENT_RESEARCH_OBJECTIVE} \n Context extraction: Using relevant keywords, entities, or relationships within the text, extract contextual information from the user's research objective that can help guide the creation of sub topics to research."
    response = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": message}, ]
    )
    CURRENT_RESEARCH_CONTEXT = response


def generate_research_topics():
    global CURRENT_RESEARCH_OBJECTIVE
    global CURRENT_RESEARCH_CONTEXT
    message = f"Generate a list of research topics related to {CURRENT_RESEARCH_OBJECTIVE}\nContext: {CURRENT_RESEARCH_CONTEXT}\nTopics:"
    result = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": message}]
    )
    research_topics = result.split("\n")
    return research_topics


def execute_research_project(project_name):
    global CURRENT_RESEARCH_OBJECTIVE
    CURRENT_RESEARCH_OBJECTIVE = project_name
    print(f'Generating topic context for {CURRENT_RESEARCH_OBJECTIVE}')
    extract_research_context()
    research_topics = generate_research_topics()
    print(f'Generated research topics: {research_topics}')
    for topic in tqdm(research_topics):
        print(f'Generating research urls for topic: {topic}')
        search_queries = generate_research_queries(topic)
        for query in tqdm(search_queries):
            print(f'Generating research urls for query: {query}')
            results = search_google_raw(query)
            print(f'Generated research urls for query: {query}')
            for result in results:
                if result not in CURRENT_RESEARCH_URLS:
                    print(f'Adding research url: {result}')
                    with open('research_urls.txt', "a") as f:
                        f.write(result + f' ({topic}) ' + "\n")
                    print(f'Digging deeper into research url: {result} . {topic}')
                    relevant_information = browse_website(result, topic)
                    display_string = f'{result}\n{topic}\n{relevant_information}\n\n'
                    print('\n' + display_string)
                    with open('research_summaries.txt', "a") as f:
                        f.write(display_string)


def generate_research_queries(research_topic):
    message = f"Using google optimum google search formatting, generate a comma separated single line text string list of Google search queries related to {research_topic} that will give us the most relevant results:"
    result = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": message}]
    )
    search_queries = result.split(", ")
    return search_queries


def get_next_research_link():
    global CURRENT_RESEARCH_URLS
    if not CURRENT_RESEARCH_URLS:
        return None
    next_url = CURRENT_RESEARCH_URLS.pop(0)
    return next_url





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




# -------------------------------------------


def shutdown():
    print("Shutting down...")
    quit()


def take_break():
    print("Taking a break...")
    time.sleep(1800)
    return "Break over"


KNOWN_RESEARCH_SOURCES = extract_sources('research.txt')


if __name__ == '__main__':
    execute_research_project('Online Gambling in Maryland')
    print('done')