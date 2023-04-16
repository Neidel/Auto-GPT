
import requests
from bs4 import BeautifulSoup

import datetime
import time
import json

from datetime import datetime, timedelta

visited_urls = []
executed_urls = []


def execute_command(command_name, arguments):

    try:
        if command_name == "google":
            return search_google_raw(arguments["input"])

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

        elif command_name == "find_news":
            return find_news()

        else:
            return f"Unknown command '{command_name}'. Please refer to the 'COMMANDS' list for availabe commands and only respond in the specified JSON format."
    # All errors, return "Error: + error message"
    except Exception as e:
        return "Error: " + str(e)

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