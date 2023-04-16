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
from bs4 import BeautifulSoup
from file_operations import read_file, write_to_file, append_to_file, delete_file, search_files
from execute_code import execute_python_file
from json_parser import fix_and_parse_json
from image_gen import generate_image
from duckduckgo_search import ddg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from llm_utils import create_chat_completion
from tqdm import tqdm
import ast
from datetime import datetime, timedelta


cfg = Config()

executed_urls = []

task_queue = []

current_task_notes = ''
completed_tasks = []
last_result = ''

visited_urls = []


class CollectionManager:
    def __init__(self, file_name="dewdrop.txt"):
        self.file_name = file_name
        self.collection = self.load_dict_from_file()
        self.seen_articles = self.load_known_articles()

    def load_known_articles(self):
        try:
            with open("articles.txt", "r") as file:
                # add articles to seen_articles
                self.seen_articles = json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    def check_for_article(self, url):
        if url not in self.seen_articles:
            self.seen_articles.append(url)
            with open("articles.txt", "w") as file:
                json.dump(self.seen_articles, file, indent=4)
            return False
        return True

    def load_dict_from_file(self):
        try:
            with open(self.file_name, "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def add_value_to_key(self, key, value):
        if key not in self.collection:
            self.collection[key] = [value]  # Creates a list with the value if the key does not exist
        else:
            if value not in self.collection[key]:
                self.collection[key].append(value)
        self.save_dict_to_file()

    def remove_value_from_key(self, key, value):
        if key in self.collection and value in self.collection[key]:
            self.collection[key].remove(value)
            if not self.collection[key]:  # Removes the key if its value list is empty
                self.collection.pop(key, None)
            self.save_dict_to_file()

    def get_key_value(self, key):
        return self.collection.get(key, "Key not found")

    def save_dict_to_file(self):
        with open(self.file_name, "w") as file:
            json.dump(self.collection, file, indent=4)

    def add_item_to(self, item, target):
        if target not in self.collection:
            self.collection[target] = {}
        self.collection[target][item] = 1
        self.save_dict_to_file()

    def remove_item_from(self, item, target):
        self.collection[target].pop(item, None)
        self.save_dict_to_file()

    def change_item(self, item, new_item):
        if item in self.collection:
            self.collection[new_item] = self.collection.pop(item)
            self.save_dict_to_file()

    def remove_item(self, item):
        self.collection.pop(item, None)
        self.save_dict_to_file()

    def find_item(self, item):
        return item in self.collection.keys()

    def count_items(self, item=None):
        return len(self.collection) if item is None else self.collection.get(item, 0)


cm = CollectionManager()


def is_valid_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def get_command(response):
    try:
        response_json = fix_and_parse_json(response)
        
        if "command" not in response_json:
            return "Error:" , "Missing 'command' object in JSON"
        
        command = response_json["command"]

        if "name" not in command:
            return "Error:", "Missing 'name' field in 'command' object"
        
        command_name = command["name"]

        # Use an empty dictionary if 'args' field is not present in 'command' object
        arguments = command.get("args", {})

        if not arguments:
            arguments = {}

        return command_name, arguments
    except json.decoder.JSONDecodeError:
        return "Error:", "Invalid JSON"
    # All other errors, return "Error: + error message"
    except Exception as e:
        return "Error:", str(e)


def resolve_redirect_url(url):
    try:
        r = requests.get(url, allow_redirects=True, timeout=60)
        time.sleep(3)
        return r.url
    except:
        return ''


def find_news():
    print("Finding news...")
    try:
        response = requests.get(f"https://news.google.com/topics/CAAqBwgKMLzugQswhJT-Ag?hl=en-US&gl=US&ceid=US%3Aen", allow_redirects=True, timeout=60)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('article')

        for article in articles:
            try:
                article_url = resolve_redirect_url(article.find('a')['href'].replace('./', 'https://news.google.com/'))
                if article_url not in cm.seen_articles:
                    print(f'Article URL: {article_url}')
                    cm.seen_articles.append(article_url)
                    return article_url
            except Exception as e:
                print(f"[{datetime.datetime.now()}]Error: {e}")

    except Exception as e:
        print(f"[{datetime.datetime.now()}]Error: {e}")


def execute_command(command_name, arguments):
    memory = get_memory(cfg)

    try:
        if command_name == "google":
            return search_google_raw(arguments["input"])

        elif command_name == "memory_add":
            return memory.add(arguments["string"])
        elif command_name == "fetch_related_memories":
            return memory.get_relevant(arguments["string"])
        elif command_name == "start_agent":
            return start_agent(
                arguments["name"],
                arguments["task"],
                arguments["prompt"])
        elif command_name == "message_agent":
            return message_agent(arguments["key"], arguments["message"])
        elif command_name == "list_agents":
            return list_agents()
        elif command_name == "delete_agent":
            return delete_agent(arguments["key"])
        elif command_name == "get_text_summary":
            return get_text_summary(arguments["url"])
        elif command_name == "get_hyperlinks":
            return get_hyperlinks(arguments["url"])
        elif command_name == "read_file":
            return read_file(arguments["file"])
        elif command_name == "write_to_file":
            return write_to_file(arguments["file"], arguments["text"])
        elif command_name == "append_to_file":
            return append_to_file(arguments["file"], arguments["text"])
        elif command_name == "delete_file":
            return delete_file(arguments["file"])
        elif command_name == "search_files":
            return search_files(arguments["directory"])
        elif command_name == "browse_website":
            return browse_website(arguments["url"])
        elif command_name == "evaluate_code":
            return ai.evaluate_code(arguments["code"])
        elif command_name == "improve_code":
            return ai.improve_code(arguments["suggestions"], arguments["code"])
        elif command_name == "write_tests":
            return ai.write_tests(arguments["code"], arguments.get("focus"))
        elif command_name == "execute_python_file":  # Add this command
            return execute_python_file(arguments["file"])
        elif command_name == "generate_image":
            return generate_image(arguments["prompt"])

        elif 'ask_user' in command_name:
            return ask_user(arguments["prompt"])

        elif 'ask_myself' in command_name:
            return ask_myself(arguments["prompt"])

        elif command_name == "find_news":
            return find_news()

        elif command_name == "take_break":
            return take_break()

        elif command_name == "check_source_article":
            return check_source_article()

        elif command_name == "get_next_research_targets":
            if cfg.google_api_key and (cfg.google_api_key.strip() if cfg.google_api_key else None):
                return scrub_google_results(get_next_search_query(search_generator))
            else:
                return scrub_google_results(google_search(get_next_search_query(search_generator)))

        elif command_name == "add_item_to":
            return cm.add_item_to(arguments["item"], arguments["target"])
        elif command_name == "remove_item_from":
            return cm.remove_item_from(arguments["item"], arguments["target"])
        elif command_name == "change_item":
            return cm.change_item(arguments["target"], arguments["item"])
        elif command_name == "remove_item":
            return cm.remove_item(arguments["target"])
        elif command_name == "find_item":
            return cm.find_item(arguments["target"])
        elif command_name == "add_value_to_key":
            return cm.add_value_to_key(arguments["target"], arguments["value"])
        elif command_name == "remove_value_from_key":
            return cm.remove_value_from_key(arguments["target"], arguments["value"])
        elif command_name == "get_key_value":
            return cm.get_key_value(arguments["target"])

        elif command_name == "app_reviews":
            return app_review_blog_writer(arguments["app_name"])

        elif command_name == "task_complete":
            shutdown()
        else:
            return f"Unknown command '{command_name}'. Please refer to the 'COMMANDS' list for availabe commands and only respond in the specified JSON format."
    # All errors, return "Error: + error message"
    except Exception as e:
        return "Error: " + str(e)


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


def app_reviews(app_name='com.fliff.fapp', sample_size=400):
    import http.client

    conn = http.client.HTTPSConnection("store-apps.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c",
        'X-RapidAPI-Host': "store-apps.p.rapidapi.com"
    }

    conn.request("GET", f"/app-reviews?app_id={app_name}&limit={sample_size}&region=us&language=en", headers=headers)

    res = conn.getresponse()
    data = res.read()

    return json.loads(data.decode("utf-8"))['data']['reviews']


def process_app_reviews(app_name):
    reviews = app_reviews(app_name)
    time.sleep(10)
    aggregated_review_block = ''
    total_reviews = 0
    current_aggregate_pros = ''
    current_aggregate_cons = ''
    for review in tqdm(reviews):
        total_reviews += 1
        if total_reviews > 10:
            # print(f'Threshold reached: {total_reviews}. Submitting...')
            total_reviews = 0
            prompt = f'Please evaluate the provided app reviews and compile a list of positive feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_pros}\n\nUpdated bulleted positive feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the pro is> (Reported 3 Times)"}, ]
            )
            print('\n\nPositive\n' + assistant_reply + '\n\n')
            current_aggregate_pros = f'{assistant_reply}'

            # print(f'Threshold reached: {total_reviews}. Submitting...')
            prompt = f'Please evaluate the provided app reviews and compile a list of negative feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_cons}\n\nUpdated bulleted negative feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the con is> (Reported 3 Times)"}, ]
            )
            print('\n\nNegative\n' + assistant_reply + '\n\n')
            current_aggregate_cons = f'{assistant_reply}'

            aggregated_review_block = ''

        aggregated_review_block += '\n' + review["review_text"] + f'({review["author_name"]})' + '\n'

    return current_aggregate_pros, current_aggregate_cons


def aggregate_pros_and_cons(app_name):
    pros_list, cons_list = process_app_reviews(app_name)

    prompt = f'Please write a blog themed summary of the pros:\n{pros_list}'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, {"role": "system", "content": 'In your summary, ignore any issues that only have a single reporter.'}, ]
    )
    final_pros = f'{assistant_reply}'
    prompt = f'Please write a blog themed summary of the cons:\n{cons_list}'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, {"role": "system", "content": 'In your summary, ignore any issues that only have a single reporter.'}, ]
    )
    final_cons = f'{assistant_reply}'

    return final_pros, final_cons, pros_list, cons_list


def app_review_blog_writer(app_name='com.fliff.fapp'):
    pros, cons, pros_list, cons_list = aggregate_pros_and_cons(app_name)

    print(f'Final Pros Summary:\n{pros}')
    print(f'Final Cons Summary:\n{cons}\n\n')

    prompt = f'Please write a blog based on the provided pros and cons:\nPros:\n{pros}\nCons:\n{cons}\n'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, ]
    )
    return pros_list + '\n\n' + cons_list + '\n\n' + assistant_reply


def take_break():
    print("Taking a break...")
    time.sleep(1800)
    return "Break over"


def get_datetime():
    return "Current date and time: " + \
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def google_search(query, num_results=3):
    search_results = []
    for j in ddg(query, max_results=num_results):
        search_results.append(j)

    return json.dumps(search_results, ensure_ascii=False, indent=4)


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


def check_source_article():
    blob = """
    New York Sweepstakes Casino and Gambling Guide
    
    New York is finally catching up with neighboring states like Pennsylvania and New Jersey but unfortunately won’t have online casino gaming legalized in 2023. Residents can currently bet on horse racing, the state lottery, and sports. In this guide we cover everything residents need to know including New York sweepstakes casino options. 

Online gambling in New York casinos was left out of the 2023 legislative session. However, some lawmakers, including New York Senator Joseph Addabbo, say licensing online casinos is a priority in 2024. If legislation is passed, New York would be one of the few US states to offer online sports betting, casinos, and poker legally. 

For now, players can enjoy their favorite games at online sweepstakes casinos in New York, a great alternative where players can win real money. While there are multiple sweepstakes providers to choose from, it’s important to note that promotional sweepstakes games are heavily regulated in New York. Nonetheless, these operators ensure compliance with state laws by refraining from offering the sale of chips with actual cash value.

Sweepstakes casinos online in New York must also comply with US sweepstakes laws to remain in operation. 
    """
    return blob


def scrub_google_results(url_list):
    cleaned_list = []
    for url in url_list:
        if url in executed_urls:
            continue
        elif url in visited_urls:
            continue
        else:
            cleaned_list.append(url)
    return cleaned_list


def page_processed(browsed_url):
    if browsed_url in executed_urls:
        return True
    else:
        executed_urls.append(browsed_url)
        return False


def browse_website(url):
    if url not in visited_urls:
        visited_urls.append(url)
        # summary = get_text_summary(get_tldr(url), desired_information)
        # result = f"""Website Content Summary: {summary}"""
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


def get_text_summary(url):
    text = browse.scrape_text(url)
    summary = browse.summarize_text(text)

    with open("research.txt", "a") as f:
        f.write(f'Source: {url}\nSummary:\n{summary}\n\n')

    return """ "Result" : """ + summary


def get_hyperlinks(url):
    link_list = browse.scrape_links(url)
    return link_list


def commit_memory(string):
    _text = f"""Committing memory with string "{string}" """
    mem.permanent_memory.append(string)
    return _text


def delete_memory(key):
    if key >= 0 and key < len(mem.permanent_memory):
        _text = "Deleting memory with key " + str(key)
        del mem.permanent_memory[key]
        print(_text)
        return _text
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


def shutdown():
    print("Shutting down...")
    quit()


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


def get_next_search_query(search_generator):
    return next(search_generator, None)


def get_search_queries():
    search_queries = [
        "Maryland online casino gaming legislation",
        "Maryland sweepstakes casino options",
        "Maryland online gambling laws",
        "Promotions at Maryland sweepstakes casinos",
        "Top Maryland sweepstakes casinos",
        "Maryland online sports betting",
        "Maryland online poker laws",
        "Land-based casinos in Maryland",
        "Maryland responsible gaming resources",
        "FAQs about Maryland online gambling"
    ]

    for query in search_queries:
        yield query





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


def gregorian_to_julian(date):
    year, month, day = date.year, date.month, date.day
    if month < 3:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524


def calculate_julian_strings():
    today = datetime.now()
    one_week_ago = today - timedelta(weeks=52)

    today_julian = gregorian_to_julian(today)
    one_week_ago_julian = gregorian_to_julian(one_week_ago)

    return f"daterange:{one_week_ago_julian}-{today_julian}"


def search_google_raw(query, num_results=3):
    url = "https://google-web-search1.p.rapidapi.com/"

    querystring = {"query": query, "limit": num_results, "related_keywords": "false"}

    headers = {
        "X-RapidAPI-Key": "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c",
        "X-RapidAPI-Host": "google-web-search1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    result_list = []
    for url in response.json()["results"]:
        result_list.append(url["url"])

    print(f'Searched for: {query}\nFound {len(result_list)} results\n{result_list}')
    return result_list


def search_google(query, num_results=3):
    raw_results = scrub_google_results(search_google_raw(query, num_results))

    return raw_results


search_generator = get_search_queries()


if __name__ == '__main__':
    app_review_blog_writer()