
import requests
import datetime

from datetime import datetime, timedelta

visited_urls = []
executed_urls = []


def execute_command(command_name, arguments):

    try:
        if command_name == "get_next_research_targets":
            return scrub_google_results(get_next_search_query(search_generator))

        else:
            return f"Unknown command '{command_name}'. Please refer to the 'COMMANDS' list for availabe commands and only respond in the specified JSON format."
    # All errors, return "Error: + error message"
    except Exception as e:
        return "Error: " + str(e)


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
