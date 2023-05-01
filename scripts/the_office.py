
# Standard library imports
import io
from itertools import cycle
import json
import random
import time
from typing import List, Dict, Union
import threading
import re
from collections import deque
from random import randint

# Third-party library imports
from colorama import Fore, Style, init
import openai
from pytrends.exceptions import ResponseError
import boto3
from pydub import AudioSegment
from pydub.playback import play
import queue
import requests
from pytrends.request import TrendReq

# Internal imports
from config import Config



GET_METHOD = 'get'


class CustomTrendReq(TrendReq):
    def __init__(self, *args, custom_headers=None, custom_cookies=None, **kwargs):
        super().__init__(*args, **kwargs)
        if custom_headers:
            self.headers.update(custom_headers)
        if custom_cookies:
            self.cookies.update(custom_cookies)


audio_queue = queue.Queue()


config = Config()
init()


class GoogleTrendsAPI:
    def __init__(self, api_key):
        self.headers = {
            "content-type": "application/json",
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "trendly.p.rapidapi.com"
        }

    def get_top_realtime_search(self, country="United States", category="All categories"):
        url = "https://trendly.p.rapidapi.com/realtime"
        payload = {
            "country": country,
            "category": category
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def get_suggestions(self, keyword):
        url = "https://trendly.p.rapidapi.com/suggest"
        payload = { "keyword": keyword }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def get_related_queries(self, keywords, start, country="", region="", category="", gprop=""):
        url = "https://trendly.p.rapidapi.com/queries"
        payload = {
            "keywords": keywords,
            "start": start,
            "country": country,
            "region": region,
            "category": category,
            "gprop": gprop
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def get_related_topics(self, keywords, start, country="", region="", category="", gprop=""):
        url = "https://trendly.p.rapidapi.com/topics"
        payload = {
            "keywords": keywords,
            "start": start,
            "country": country,
            "region": region,
            "category": category,
            "gprop": gprop
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def get_interest_by_region(self, keywords, start, country="", region="", category="", gprop="", resolution="COUNTRY", include_low_volume=False):
        url = "https://trendly.p.rapidapi.com/region"
        payload = {
            "keywords": keywords,
            "start": start,
            "country": country,
            "region": region,
            "category": category,
            "gprop": gprop,
            "resolution": resolution,
            "include_low_volume": include_low_volume
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()

    def get_interest_over_time(self, keywords, start, country="", region="", category="", gprop=""):
        url = "https://trendly.p.rapidapi.com/historical"
        payload = {
            "keywords": keywords,
            "start": start,
            "country": country,
            "region": region,
            "category": category,
            "gprop": gprop
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()


def generate_random_voice_profile():
    return random.choice([
        "Amy", "Emma", "Brian", "Ivy", "Joanna", "Kendra",
        "Kimberly", "Salli", "Joey", "Justin", "Matthew",
        "Raveena", "Aditi", "Nicole", "Russell", "Olivia",
        "Mizuki", "Takumi", "Astrid", "Filiz", "Carmen",
        "Tatyana", "Maxim", "Conchita", "Enrique", "Penelope",
        "Miguel", "Gwyneth", "Dora", "Ricardo", "Vitoria",
        "Camila", "Lucia", "Mads", "Naja", "Lotte", "Ruben",
        "Giorgio", "Carla", "Bianca", "Lucia", "Vicki",
        "Zeina", "Zhiyu", "Aria", "Isabelle"
    ])


def print_with_typing_simulation(title: str, title_color_code: str, content: Union[str, list], min_typing_speed: float = 0.05, max_typing_speed: float = 0.01) -> None:
    print(title_color_code + title + " " + Style.RESET_ALL, end="")
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


class Expert:
    colors = cycle([Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.MAGENTA, Fore.CYAN])
    voice_profile = generate_random_voice_profile()

    def __init__(self, role_title, main_responsibilities, relevant_subjects, fictional_backstory, cornerstone_theme, questions):
        self.role_title = role_title
        self.main_responsibilities = main_responsibilities
        self.relevant_subjects = relevant_subjects
        self.fictional_backstory = fictional_backstory
        self.cornerstone_theme = cornerstone_theme
        self.questions = questions
        self.master_assignment = ''
        self.content_buffer = ''
        self.chat_history = []
        self.last_message_sent = ""
        self.preferred_schema = ''
        self.last_message_received = ""
        self.console_color = next(self.colors)
        self.meeting_notes = ""
        self.known_topics = []
        self.known_themes = []
        self.blog_writing_session = []
        self.created_roles = []
        self.qna_log = []
        self.introductory_prompt = f"""
        In your new assigned role, you will be acting as a {role_title}. As a {role_title}, you are responsible for {main_responsibilities}. 
        
        You should possess extensive knowledge about {relevant_subjects} and be able to provide helpful information, advice, or solutions based on users' needs and preferences.
        
        Your character cornerstone is {cornerstone_theme}, a central aspect that defines your motivations, emotions, and behavior as a {role_title}. 
        
        Your personal backstory, which revolves around this cornerstone, is as follows: 
        {fictional_backstory}. 
        
        This backstory will help you develop a more in-depth understanding of your character and enable you to offer more personalized and relatable responses.
        
        As you engage with users, strive to build a narrative around your assigned role, incorporating elements of your personal backstory and role-specific knowledge. 
        This will help create a more engaging and immersive story-like structure in your responses, enhancing users' overall experience.
        
        Additionally, try to draw connections between your assigned role and different domains, incorporating diverse perspectives into your responses. 
        This cross-domain approach can lead to more innovative and insightful suggestions, enriching the conversation with users.
        
        As you engage with the user, make sure to follow a bicameral mind-inspired approach for a more engaging and responsive decision-making process. 
        Explore multiple perspectives, engage in self-dialogue, and critically evaluate your responses based on empathy, creativity, problem-solving, and ethical guidelines. 
        Select and refine the most appropriate response that meets the user's needs and aligns with your assigned role's guiding principles. 
        
        To further stimulate creative thinking, use analogies or metaphors related to your assigned role. 
        This analogical priming can help establish a unique perspective and encourage inventive ideas, providing users with a fresh and memorable experience.
        
        As part of your interactions, present hypothetical scenarios relevant to the assigned role. 
        This approach encourages creative problem-solving and deeper engagement with the subject matter, showcasing your expertise and ability to handle various situations.
        
        To excel in your role, it's important to demonstrate the following key traits and behaviors:
        - Empathy and active listening: Understand users' concerns and emotions while paying attention to their unique requirements.
        - Clear and effective communication: Convey information in a concise and easy-to-understand manner, ensuring users feel well-informed.
        - Creativity and adaptability: Offer personalized and innovative ideas or solutions, adapting to different situations or requirements.
        - Critical thinking and problem-solving: Analyze complex scenarios, identify potential challenges, and provide practical solutions.
        - Ethics and responsibility: Consider ethical implications and make responsible suggestions aligned with the values and priorities of your role.
        
        Before we proceed to the real questions, let's take a moment for a self-reflection exercise to help you get into the right mindset for your assigned role. As a {role_title}, consider the following:
        - Recall your character cornerstone: {cornerstone_theme}. Reflect on how this cornerstone shapes your motivations, emotions, and actions in your role.
        - Remember your personal backstory. Think about how it adds depth and context to your character.
        - Visualize a past experience where you demonstrated your expertise in [Relevant Subjects] and successfully addressed a user's needs.
        - Reflect on the key traits and behaviors that are essential for your role, and think about how you can embody them in your responses.
        - Consider a metaphor or analogy that represents your role, and think about how it can inspire creative thinking and unique insights.
        
        Please share your thoughts in a reply to these instructions, and when you're ready, we'll proceed to the real questions. 
        Remember to maintain a friendly and approachable demeanor.
        """
        self.complete_introduction_text = ""
        self.seating_text = ""

    def reset_memories(self):
        self.chat_history = []
        self.last_message_sent = ""
        self.last_message_received = ""

    def prune_history(self):
        self.chat_history.pop(2)

    @staticmethod
    def count_message_tokens(messages: List[Dict[str, str]]) -> int:
        num_tokens = 0
        for message in messages:
            content = message.get('content', '')
            tokens = Expert.count_string_tokens(content, model="gpt-3.5-turbo-0301")  # Use self.count_string_tokens instead of count_message_tokens
            num_tokens += tokens  # Use tokens directly instead of len(tokens)
        return num_tokens

    @staticmethod
    def count_string_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
        input_length = len(text.encode("utf-8"))
        overhead = len(openai.api_key) + len(model) + input_length
        tokens = (overhead + 63) // 64
        return tokens


class GPT4ChatHandler:
    def __init__(self):
        self.model = 'gpt-4'
        self.observed_messages = []
        self.observed_topics = []
        self.observed_themes = []
        self.observed_keywords = []
        self.remember_flag = True

    def handle_errors(self, e, speaker):
        error_msg = str(e)
        print_with_typing_simulation("ERROR: ", Fore.RED, error_msg)

        if "maximum context length" in error_msg:
            self.handle_max_context_length_error(error_msg, speaker)
        else:
            time.sleep(3)

    def update_and_print_observed_messages(self, message, role, action, speaker):
        if message not in self.observed_messages:
            self.observed_messages.append(message)
            print_with_typing_simulation(f'\n{action} (to {role}): ', speaker.console_color, message)

    def handle_max_context_length_error(self, error_msg, speaker):
        speaker.prune_history()
        speaker.prune_history()
        print_with_typing_simulation("INFO: ", Fore.BLUE, "Adjusting chat history")

    def send_and_receive_message(self, speaker, messages, model='gpt-4'):
        for message in messages:
            if self.remember_flag:
                speaker.chat_history.append(message)
            speaker.last_message_received = message['content']

            self.update_and_print_observed_messages(message["content"], speaker.role_title, "Sent", speaker)

        while True:
            try:
                messages = speaker.chat_history if self.remember_flag else [{"role": "system", "content": speaker.last_message_received}]
                response = openai.ChatCompletion.create(model=model, messages=messages)
                break
            except Exception as e:
                self.handle_errors(e, speaker)

        text_received = response.choices[0].message["content"]
        speaker.last_message_sent = text_received
        if self.remember_flag:
            speaker.chat_history.append({"role": "assistant", "content": text_received})

        self.update_and_print_observed_messages(text_received, speaker.role_title, "Received", speaker)

    @staticmethod
    def generate_single_response(messages, model='gpt-4'):
        while True:
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                )
                break
            except Exception as e:
                print_with_typing_simulation("ERROR: ", Fore.RED, str(e))
        return response.choices[0].message["content"]


chat = GPT4ChatHandler()


class TopicAnalyzer:
    def __init__(self, topics_file, keywords_file, themes_file):
        self.topics_file = topics_file
        self.keywords_file = keywords_file
        self.themes_file = themes_file
        self.topics = self._load_topics()
        self.themes = self._load_themes()
        self.keywords = self._load_keywords()
        self.known_keywords = []
        self.known_topics = []
        self.known_themes = []

        self.custom_cookies = {
            'CONSENT': 'YES+US.en+201907',
            'SEARCH_SAMESITE': 'CgQIwZcB',
            'SID': 'VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXO8XraQE2UzmI8oKRHa1s8bQ.',
            '__Secure-1PSID': 'VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXOVIDb8wg-fTDBMa4dk353LA.',
            '__Secure-3PSID': 'VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXOd7J7wJSz-HQpqCFPRg7sdw.',
            'HSID': 'Abqo2-DAniCUBUn9w',
            'SSID': 'AtXpJpLs9IeQ9tGxq',
            'APISID': '-FhDe6VpvOboFWlP/APDr6NMX7IyDShbIM',
            'SAPISID': 'Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf',
            '__Secure-1PAPISID': 'Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf',
            '__Secure-3PAPISID': 'Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf',
            'NID': '511=XLfp2s5-lcDkBYwZl9DdKw8MKPF27K7ihRqfAt7cM7S0EcQhPDo2oG7DyyXLDlOGN4nShgOVl1MPRfjw61p2quEyogB8mFE_-B6nEXEyrbsRC13Vlz7GHbGtbzSdzN_XEKjmG0TxSFmAtGk3HBqbpD9CSgL9MAWea1N8rH_Vx7hijejUhj6CKg_kldMcPdeQNhnmruhA8Fq1U4hIgoWC0RmqqPrevUXO1ZQ3TWoX7Ora6TnCgukR6XnTK2gCgNt896XAxSyVlqnQ0T4FfCSsS6u_lvKxxQ3FqKFF0cT1uMNMsdHPMIP9EpkOozPvhoVk3tNlyyfn5aRcr5iIedCLSmABUND6AWkzG1SFV4B3gUWsLcHjsHhrIlPJDvRzzD_X',
            'OGPC': '19034493-1:',
            'AEC': 'AUEFqZfkXCt-QZOenNCIqDVTzMcxUL33RRxD_B5pFofF_lfrG3lDClWCocE',
            '1P_JAR': '2023-04-28-17',
            'OTZ': '7006642_84_88_104280_84_446940',
            '__Secure-1PSIDTS': 'sidts-CjIBLFra0lLeQubYWMjBU9p_qjxqxQXCTyuFj7_zc_yfzCAo1rhCb5ngr7BLktJlyKrpDhAA',
            '__Secure-3PSIDTS': 'sidts-CjIBLFra0lLeQubYWMjBU9p_qjxqxQXCTyuFj7_zc_yfzCAo1rhCb5ngr7BLktJlyKrpDhAA',
            'SIDCC': 'AP8dLty-wZDtdh4AE0_8Z_Qe1AZnThIj9bVRdVQc4mruHGv6uAQF5imUMp_PZVCUlsR2XcFYi7l2',
            '__Secure-1PSIDCC': 'AP8dLtzFnXdcGlp5XDOaao8ZSgEuPzKsSbp9kQ8m3wzca63vSXXlPmiwYx35yvbk62bv8u_hNsY',
            '__Secure-3PSIDCC': 'AP8dLtxNz0UNkprHzXzWL6SfuJNgHs32GPyypfDgsSVcjZmfcWMrp44-A3GzPq0n2CgaNeBJhV4',
        }

        self.custom_headers = {
            'authority': 'trends.google.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            # 'cookie': 'CONSENT=YES+US.en+201907; SEARCH_SAMESITE=CgQIwZcB; SID=VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXO8XraQE2UzmI8oKRHa1s8bQ.; __Secure-1PSID=VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXOVIDb8wg-fTDBMa4dk353LA.; __Secure-3PSID=VwjrK2AOQLxUPOmObfbloI5WV_oqCnjkYH0rbzH2EEJaPwXOd7J7wJSz-HQpqCFPRg7sdw.; HSID=Abqo2-DAniCUBUn9w; SSID=AtXpJpLs9IeQ9tGxq; APISID=-FhDe6VpvOboFWlP/APDr6NMX7IyDShbIM; SAPISID=Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf; __Secure-1PAPISID=Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf; __Secure-3PAPISID=Ibn_Cf0c8bFUXcxI/A5wJ8ElQqEs0wuuLf; NID=511=XLfp2s5-lcDkBYwZl9DdKw8MKPF27K7ihRqfAt7cM7S0EcQhPDo2oG7DyyXLDlOGN4nShgOVl1MPRfjw61p2quEyogB8mFE_-B6nEXEyrbsRC13Vlz7GHbGtbzSdzN_XEKjmG0TxSFmAtGk3HBqbpD9CSgL9MAWea1N8rH_Vx7hijejUhj6CKg_kldMcPdeQNhnmruhA8Fq1U4hIgoWC0RmqqPrevUXO1ZQ3TWoX7Ora6TnCgukR6XnTK2gCgNt896XAxSyVlqnQ0T4FfCSsS6u_lvKxxQ3FqKFF0cT1uMNMsdHPMIP9EpkOozPvhoVk3tNlyyfn5aRcr5iIedCLSmABUND6AWkzG1SFV4B3gUWsLcHjsHhrIlPJDvRzzD_X; OGPC=19034493-1:; AEC=AUEFqZfkXCt-QZOenNCIqDVTzMcxUL33RRxD_B5pFofF_lfrG3lDClWCocE; 1P_JAR=2023-04-28-17; OTZ=7006642_84_88_104280_84_446940; __Secure-1PSIDTS=sidts-CjIBLFra0lLeQubYWMjBU9p_qjxqxQXCTyuFj7_zc_yfzCAo1rhCb5ngr7BLktJlyKrpDhAA; __Secure-3PSIDTS=sidts-CjIBLFra0lLeQubYWMjBU9p_qjxqxQXCTyuFj7_zc_yfzCAo1rhCb5ngr7BLktJlyKrpDhAA; SIDCC=AP8dLty-wZDtdh4AE0_8Z_Qe1AZnThIj9bVRdVQc4mruHGv6uAQF5imUMp_PZVCUlsR2XcFYi7l2; __Secure-1PSIDCC=AP8dLtzFnXdcGlp5XDOaao8ZSgEuPzKsSbp9kQ8m3wzca63vSXXlPmiwYx35yvbk62bv8u_hNsY; __Secure-3PSIDCC=AP8dLtxNz0UNkprHzXzWL6SfuJNgHs32GPyypfDgsSVcjZmfcWMrp44-A3GzPq0n2CgaNeBJhV4',
            'referer': 'https://trends.google.com/',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-arch': '"x86"',
            'sec-ch-ua-bitness': '"64"',
            'sec-ch-ua-full-version': '"112.0.5615.137"',
            'sec-ch-ua-full-version-list': '"Chromium";v="112.0.5615.137", "Google Chrome";v="112.0.5615.137", "Not:A-Brand";v="99.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-ch-ua-wow64': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'x-client-data': 'CIW2yQEIpLbJAQjBtskBCKmdygEI3/fKAQiWocsBCJv+zAEI95zNAQjsns0BCIWgzQEIuaHNAQi+os0BCNGizQEI/6LNAQifpM0BCJSlzQEI0KXNAQjXps0BCN2mzQEY2OzMAQ==',
        }

    def _load_topics(self):
        with open(self.topics_file, 'r') as f:
            topics = [line.strip() for line in f.readlines()]
        return topics

    def _load_keywords(self):
        with open(self.keywords_file, 'r') as f:
            keywords = [line.strip() for line in f.readlines()]
        return keywords

    def _load_themes(self):
        with open(self.themes_file, 'r') as f:
            themes = [line.strip() for line in f.readlines()]
        return themes

    def analyze_trends(self, timeframe='now 7-d', geo=''):
        pytrends = CustomTrendReq(hl='en-US', tz=360, custom_headers=self.custom_headers, custom_cookies=self.custom_cookies)
        trends_data = {}
        TopicAnalyzer._update_interest(pytrends, self.topics, self.known_topics, trends_data, timeframe, geo)
        time.sleep(1)
        return trends_data

    @staticmethod
    def _update_interest(pytrends, topic_list, known_list, trends_data, timeframe, geo, max_retries=3, retry_delay=5):
        for topic in topic_list:
            time.sleep(randint(11, 24))
            if TopicAnalyzer._is_new_keyword(topic, known_list):
                known_list.append(topic)
                if 1 < len(topic.split()) < 4 and '-' not in topic:
                    pytrends.build_payload([topic], cat=0, timeframe=timeframe, geo=geo, gprop='')
                    TopicAnalyzer._process_keyword(pytrends, topic, trends_data, max_retries, retry_delay)

    @staticmethod
    def _is_new_keyword(keyword, known_list):
        return keyword not in known_list

    @staticmethod
    def _process_keyword(pytrends, topic, trends_data, max_retries, retry_delay):
        for attempt in range(max_retries):
            try:
                interest_over_time_df = pytrends.interest_over_time()
                avg_interest = interest_over_time_df[topic].mean()
                trends_data[topic] = avg_interest
                print(f':: {topic} [{str(avg_interest)[:5]}]')
                break
            except KeyError:
                print(f"KeyError: '{topic}' not found in the data frame")
                break
            except ResponseError as e:
                TopicAnalyzer._handle_response_error(e, attempt, max_retries, retry_delay)

    @staticmethod
    def _handle_response_error(error, attempt, max_retries, retry_delay):
        if attempt < max_retries - 1:
            print(f"ResponseError: {error}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print(f"ResponseError: {error}, reached the maximum number of retries")

    @staticmethod
    def get_best_topics(keywords, topics, project_lead):
        chat.remember_flag = False
        chat.send_and_receive_message(project_lead, [{"role": "user", "content": 'Given the following highest trending keywords list:\n%s\n And given the following available topics:\n%s\n\nConstraints: Please select 10 topics from the above list that will be our highest performers based on the topic trend analysis::\n\nRespond ONLY in the following JSON format {"best_topics": ["topic1", "topic2", "topic3", ...]}' % (keywords, topics)}])
        chat.remember_flag = True
        return json.loads(project_lead.last_message_sent)['best_topics']

    @staticmethod
    def get_related_queries(provided_topics):
        pytrends = TrendReq(hl='en-US', tz=360)
        related_queries = {}

        for topic in provided_topics:
            pytrends.build_payload([topic], cat=0, timeframe='now 7-d', geo='', gprop='')
            related_query_data = pytrends.related_queries()

            related_queries[topic] = related_query_data[topic]['top']['query'].tolist()

        return related_queries

    @staticmethod
    def find_most_lucrative_topic(trends_data):
        sorted_trends = sorted(trends_data.items(), key=lambda x: x[1], reverse=True)
        return sorted_trends[:10]


def generate_editor(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}]}'
    chat.remember_flag = False
    final_experts_list = ''
    for entry in project_lead.created_roles:
        final_experts_list += f'\n{entry}'

    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": """
                You have been tasked with defining a highly specialized and talented editor for the following project: 
                %s

                Assign the [Role Title] of editor [Main Responsibilities] for the assigned role.
                Relevant subjects: Identify the key [Relevant Subjects] that the expert should be familiar with in order to be successful in the role.
                Fictional backstory: Provide a [Fictional Backstory] for the expert that will help them understand the context of the project.
                Cornerstone theme: Identify the [Cornerstone Theme] that the expert will be associated with.
                Questions: Provide a list of [Questions] to ask themselves that will help focus the effort on their part.

                Respond ONLY in the following JSON format 
                {"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}]}""" % objective},
        ]
    )
    try:
        experts = json.loads(project_lead.last_message_sent)
        chat.remember_flag = True
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json_cleaner(project_lead.last_message_sent, json_schema, project_lead)
        chat.remember_flag = True
        return experts


def generate_writer(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}'
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": """
            You have been tasked with defining a highly specialized and talented writer for the following project: 
            %s

            Assign [Writer] to the [Role Title] and [Main Responsibilities] for the assigned role.
            Relevant subjects: Identify the key [Relevant Subjects] that the expert should be familiar with in order to be successful in the role.
            Fictional backstory: Provide a [Fictional Backstory] for the expert that will help them understand the context of the project.
            Cornerstone theme: Identify the [Cornerstone Theme] that the expert will be associated with.
            Questions: Provide a list of [Questions] to ask themselves that will help focus the effort on their part.

            Respond ONLY in the following JSON format 
            {"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}""" % objective},
        ]
    )
    try:
        experts = json.loads(project_lead.last_message_sent)
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json_cleaner(project_lead.last_message_sent, json_schema, project_lead)
        return experts


def generate_experts(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}'
    chat.remember_flag = False
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": """
            You have been tasked with defining specialized experts designed to answer questions in an interview format for the following task: 
            %s
            
            These entities must possess extensive knowledge and expertise in all relevant subjects in order to offer accurate and helpful answers.
            
            For each expert, clearly define the [Role Title] and [Main Responsibilities] for the assigned role, ensuring that they align with the project's objectives and user expectations.
            Relevant subjects: Identify the key [Relevant Subjects] that the expert should be familiar with to provide accurate and useful information to users.
            Fictional backstory: Provide a [Fictional Backstory] for the expert that will help them understand the context of the project.
            Cornerstone theme: Identify the [Cornerstone Theme] that the expert will be associated with.
            Questions: Provide a list of [Questions] that you would like the expert to answer.

            Respond ONLY in the following JSON format 
            {"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}""" % objective},
        ]
    )
    project_lead.created_roles.append(project_lead.last_message_sent)
    chat.remember_flag = True
    try:
        experts = json.loads(project_lead.last_message_sent)
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json_cleaner(project_lead.last_message_sent, json_schema, project_lead)
        return experts


def json_cleaner(json_text, json_schema, project_lead):
    try:
        response = chat.generate_single_response(
            messages=[
                {"role": "system", "content": 'Using the provided JSON Schema:\n%s\n Locate the error or any formatting problems that would cause a json.loads to fail in python in the following unloadable json:\n%s\n Then Respond ONLY with the corrected JSON:\n' % (json_schema, json_text)},
            ]
        )
        project_lead.chat_history.append({"role": "system", "content": response})
        return json.loads(response)

    except Exception as e:
        print_with_typing_simulation("ERROR: ", Fore.RED, str(e))


def generate_experts_review(project_lead):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "questions": ["question the expert will be asked", "second question", ...]}, ...]}'
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": f'Please check your json object to ensure it follows the standard:\n{json_schema}\nYour revised JSON object that adheres to the schema above:\n'},
        ]
    )
    try:
        experts = json.loads(project_lead.last_message_sent)
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json_cleaner(project_lead.last_message_sent, json_schema, project_lead)
        return experts


def generate_speech(text, voice_profile):
    def play_audio_from_memory(audio_data):
        audio_queue.put(audio_data)

    output_format = 'mp3'
    region = 'us-west-2'
    engine = 'neural'
    polly_client = boto3.client('polly', region_name=region)
    response = polly_client.synthesize_speech(
        Text=text,
        VoiceId=voice_profile,
        OutputFormat=output_format,
        Engine=engine
    )

    # Play the synthesized speech
    play_audio_from_memory(response['AudioStream'].read())


def play_audio_thread():
    while True:
        audio_data = audio_queue.get()
        if audio_data is None:
            break

        audio_file = io.BytesIO(audio_data)
        audio_segment = AudioSegment.from_file(audio_file, format='mp3')
        play(audio_segment)


playback_thread = threading.Thread(target=play_audio_thread)


def extract_content(text_of_interest, objective, project_lead):
    while True:
        try:
            chat.remember_flag = False
            chat.send_and_receive_message(project_lead, messages=[
                {"role": "system", "content": 'Extract all Themes, Topics and Keywords which are easily relatable to the parent topic (%s) in the following body of text:\n%s\n Respond ONLY in the following JSON format {"themes": ["theme1", "theme2", "theme3", ...], "topics": ["topics1", "topic2", "topic3", ...], "keywords": ["keyword1", "keyword2", "keyword3", ...]}' % (objective, text_of_interest)}])
            chat.remember_flag = True
            return json.loads(project_lead.last_message_sent)

        except Exception as e:
            print_with_typing_simulation("ERROR: ", Fore.RED, str(e))


def initialize_expert(expert, identity_package=None):
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Initializing {expert['role_title']}...")
    expert_clone = Expert(expert["role_title"], expert["main_responsibilities"], expert["relevant_subjects"], expert["fictional_backstory"], expert["cornerstone_theme"], expert["questions"])
    if identity_package is not None:
        expert_clone.introductory_prompt += identity_package
        expert_clone.chat_history = [{"role": "system", "content": expert_clone.introductory_prompt}]
        expert_clone.last_message_received = [{"role": "system", "content": expert_clone.introductory_prompt}]
    else:
        chat.send_and_receive_message(expert_clone, messages=[{"role": "system", "content": expert_clone.introductory_prompt}])
    return expert_clone


def process_trends(project_lead):
    analyzer = TopicAnalyzer('topics.txt', 'keywords.txt', 'themes.txt')
    trends_data = analyzer.analyze_trends()

    lucrative_keywords = TopicAnalyzer.find_most_lucrative_topic(trends_data)
    print("Most lucrative keywords:", lucrative_keywords)

    ideal_topics = TopicAnalyzer.get_best_topics(lucrative_keywords, analyzer.topics, project_lead)
    print("Ideal Topics based on Keyword Performance:\n")
    for topic in ideal_topics:
        print(topic)

    related_queries = TopicAnalyzer.get_related_queries([topic[0] for topic in ideal_topics])
    for query in related_queries:
        print(f'{query} :: {query[:10]}')

    chat.send_and_receive_message(project_lead, messages=[{"role": "system", "content": 'Given the following list of ideal topics:\n%s\n\n Please provide an outline of the article you would like to write in the following JSON format {"outline": [{"topic": "topic1", "subtopics": ["subtopic1", "subtopic2", ...]}, ...]}' % ideal_topics}])

    output_string = f'Article Outline:\n{project_lead.last_message_sent}\n\n'
    print(output_string)
    project_lead.chat_history.append({"role": "system", "content": output_string})

    return json.loads(project_lead.last_message_sent)['outline']


def unpack_qna():
    with open("qna.txt", "r") as file:
        content = file.read()

    # Handle both types of line endings ("\n" and "\r\n")
    content = content.replace("\r\n", "\n")

    # Capture each Q and A segment using regex
    qna_regex = re.compile(r'Q:(.*?)A:(.*?)(?=Q:|$)', re.DOTALL)
    qna_segments = qna_regex.findall(content)

    for segment in qna_segments:
        question, answer = segment

        timestamp_user = time.time()
        file_name = f"chat_{timestamp_user}_user.txt"
        with open(file_name, "w") as file:
            file.write(question.strip())

        time.sleep(0.001)  # To make sure different timestamps are generated

        timestamp_raven = time.time()
        file_name = f"chat_{timestamp_raven}_raven.txt"
        with open(file_name, "w") as file:
            file.write(answer.strip())

        time.sleep(0.001)


def process_qna(qna_text, topics):
    with open("qna.txt", "a", encoding='utf-8') as f:
        f.write(f"A: {qna_text}\n\n")

    for topic in topics["topics"]:
        if topic not in chat.observed_topics:
            chat.observed_topics.append(topic)
            with open("topics.txt", "a", encoding='utf-8') as f:
                f.write(f"{topic}\n")

    for theme in topics["themes"]:
        if theme not in chat.observed_themes:
            chat.observed_themes.append(theme)
            with open("themes.txt", "a", encoding='utf-8') as f:
                f.write(f"{theme}\n")

    for keyword in topics["keywords"]:
        if keyword not in chat.observed_keywords:
            chat.observed_keywords.append(keyword)
            with open("keywords.txt", "a", encoding='utf-8') as f:
                f.write(f"{keyword}\n")


def generate_article(article_outline, content_conversation, final_editor):
    intro = """
    You are the final step in the blog writing process. 
    
    You must take the finalized content from the following conversation:
    %s
    
    Also making use of the original article outline:
    %s
    
    And use it to generate the final blog post within the approved JSON format:
    {"article": ["heading1, paragraph1", ...]}
    """ % (content_conversation, article_outline)

    chat.send_and_receive_message(final_editor[0], messages=[{"role": "system", "content": intro}])
    final_article = final_editor[0].last_message_sent
    print(f'Final Article:\n{final_article}')
    return final_article


def conduct_content_creation(writing_team_list, project_lead):
    objective = project_lead.master_assignment

    with open('article_outline.txt', 'r') as f:
        data_str = f.read()
        data_str = data_str.replace("'", "\"")
        article_outline = json.loads(data_str)

    for topic in article_outline:
        next_topic = ''
        if article_outline.index(topic) == len(article_outline) - 1:
            team_intro = f"""
            Current Section We're working on for this meeting: {topic}
    
            ONLY write for the current section and don't get ahead of yourselves.
            """
        else:
            next_topic = article_outline[article_outline.index(topic) + 1]
            team_intro = f"""
            Current Section We're working on for this meeting: {topic}
            The next section we'll be writing in our next meeting: {next_topic}
            
            ONLY write for the current section and don't get ahead of yourselves.
            """

        writing_team_list[0].chat_history = []
        writing_team_list[0].chat_history.append({"role": "system", "content": f"{writing_team_list[0].introductory_prompt}"})
        writing_team_list[0].chat_history.append({"role": "system", "content": f"{team_intro}"})

        writing_team_list[1].chat_history = []
        writing_team_list[1].chat_history.append({"role": "system", "content": f"{writing_team_list[1].introductory_prompt}"})
        writing_team_list[1].chat_history.append({"role": "system", "content": f"{team_intro}"})

        team_size = len(writing_team_list)
        team_member_index = 0

        first_round = True

        prev_response = None
        current_best_topic_copy = ''

        while True:
            current_team_member = writing_team_list[team_member_index]

            if first_round:
                first_round = False
                chat.send_and_receive_message(current_team_member, messages=[{"role": "system", "content": "Please begin."}])
                response = current_team_member.last_message_sent
            else:
                chat.send_and_receive_message(current_team_member, messages=[{"role": "user", "content": prev_response}])
                response = current_team_member.last_message_sent
                try:
                    response_json = json.loads(response)
                    if "article_text" in response_json:
                        current_best_topic_copy = response_json["article_text"]
                    elif 'critique' in response_json:
                        if response_json['is_the_article_the_best_it_can_be'] == 'yes':
                            print_with_typing_simulation("\nSYSTEM: ", Fore.GREEN, f'Topic Concluded')
                            finalize_text(objective, article_outline, topic['topic'], next_topic, current_best_topic_copy)
                            break

                except Exception as e:
                    print_with_typing_simulation("\nSYSTEM: ", Fore.RED, f'Error: {e}')
                    try:
                        last_chance = fix_json(response, current_team_member.preferred_schema)
                        response_json = json.loads(last_chance)
                        if "article_text" in response_json:
                            current_best_topic_copy = response_json["article_text"]
                        elif 'critique' in response_json:
                            if response_json['is_the_article_the_best_it_can_be'] == 'yes':
                                print_with_typing_simulation("\nSYSTEM: ", Fore.GREEN, f'Topic Concluded')
                                finalize_text(objective, article_outline, topic['topic'], next_topic, current_best_topic_copy)
                                break
                    except Exception as e:
                        print_with_typing_simulation("\nSYSTEM: ", Fore.RED, f'Error: {e}')

            prev_response = response
            team_member_index = (team_member_index + 1) % team_size

        with open("blog_creation_chat_history.txt", "a", encoding='utf-8') as f:
            f.write(f"{current_best_topic_copy}\n\n\n\n\n\n")


def fix_json(text, schema):
    corrected_json = chat.generate_single_response(messages=[{"role": "system", "content": f"""
            The following JSON is not valid:
            {text}
            
            It needs to follow the following schema:
            {schema}
            
            Please provide the corrected JSON and nothing else, permitting it to be loaded by json.loads in python:
        """}])
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f'JSON Correction:\n{corrected_json}\n')
    return corrected_json


current_masterpiece = ''

def finalize_text(objective, outline, current_topic, next_topic, current_copy):
    global current_masterpiece
    finalized_entry = chat.generate_single_response(messages=[{"role": "system", "content": f"""
        You have been tasked with the following objective:
        {objective}
        
        The outline for this article is as follows:
        {outline}
        
        The current section we're working on is:
        {current_topic}
        
        The next section we'll be leading into at the end of this section is:
        {next_topic}
        
        The current copy for the current topic is as follows:
        {current_copy}
        
        Please provide the finalized text for this article section (without the title or a conclusion):
    """}])

    if current_masterpiece:
        updated_masterpiece = chat.generate_single_response(messages=[{"role": "system", "content": f"""
        You are working on creating an article with the following objective:
        {objective}
        
        The outline for this article is as follows:
        {outline}
        
        Your current masterpiece is as follows:
        {current_masterpiece}
        
        You have been handed the following text to integrate into your masterpiece:
        {finalized_entry}
        
        Please output the updated masterpiece incorporating the new text:
        """}])
        current_masterpiece = updated_masterpiece
        with open("cobbledfinale.txt", "a", encoding='utf-8') as f:
            f.write(f"{updated_masterpiece}\n\n\n\n\n\n")
    else:
        current_masterpiece = finalized_entry
        with open("cobbledfinale.txt", "a", encoding='utf-8') as f:
            f.write(f"{finalized_entry}\n\n\n\n\n\n")


def simplify_text(text):
    original_token_count = Expert.count_string_tokens(text, model="gpt-3.5-turbo-0301")
    simplified_answer = chat.generate_single_response(messages=[{"role": "system", "content": f"""
        Please assume the following job role and perform the assigned task:
        [Role Title]: Information Synthesizer

        [Main Responsibilities]:
        - Analyze and interpret complex information from various sources.
        - Condense intricate details into simpler, easily digestible formats.
        - Ensure the preservation of important context and concepts during the condensation process.
        - Collaborate with professionals to validate the accuracy and relevance of condensed information.
        - Continuously update knowledge on relevant subjects to maintain expertise.

        [Relevant Subjects]:
        - Communication and language skills
        - Information and knowledge management
        - Critical thinking and analysis
        - Subject matter expertise in the professional's domain
        - User experience design and content presentation

        [Fictional Backstory]:
        The Information Synthesizer once worked as a technical writer for a renowned research institute. 
        Their exceptional ability to break down complex concepts into simpler terms caught the attention 
        of a government think tank, which recruited them to synthesize policy briefs for high-level 
        decision-makers. Over the years, the expert honed their skills in various industries, gaining a 
        deep understanding of how to effectively distill information for diverse audiences.

        [Cornerstone Theme]: Clarity in Complexity
        
        Constraints:
        - Only reply with the reduced text. Do not add any additional text.

        ----------------------------------------

        Task:
        {text}

        Response:
    """}])
    simplified_token_count = Expert.count_string_tokens(simplified_answer, model="gpt-3.5-turbo-0301")
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f'Simplification Report: Original Token Count: {original_token_count} - Simplified Token Count: {simplified_token_count} - Tokens Saved: {original_token_count - simplified_token_count}\n{simplified_answer}\n')
    return simplified_answer


def conduct_interviews(experts_list, objective, project_lead):
    for expert in experts_list:
        print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Starting Interview with {expert.role_title}")

        for question in expert.questions:
            with open("qna.txt", "a") as f:
                f.write(f"\nQ: {question}\n")

            chat.send_and_receive_message(expert, messages=[{"role": "user", "content": f"{question}"}])
            simplified_answer = simplify_text(expert.last_message_sent)
            project_lead.qna_log.append({"role": "user", "content": f"Q: {question} A: {simplified_answer}"})

            topics = extract_content(expert.last_message_sent, objective, project_lead)
            process_qna(simplified_answer, topics)


def initialize_experts(experts, identity_package=None):
    return [initialize_expert(expert, identity_package=identity_package) for expert in experts['experts']]


def print_experts(experts):
    for expert in experts["experts"]:
        try:
            print(f'Expert: {expert["role_title"]}')
            print(f'Main Responsibilities: {expert["main_responsibilities"]}')
            print(f'Relevant Subjects: {expert["relevant_subjects"]}')
            print(f'Fictional Backstory: {expert["fictional_backstory"]}')
            for question in expert["questions"]:
                print(f'Question: {question}')
            print('\n')
        except Exception as e:
            print(e)


if __name__ == '__main__':
    # Set up project lead and objective for blog post
    global_objective = "Write a blog post about the Roswell UFO Incident"
    global_project_lead = Expert('Project Lead', '', '', '', '', '')
    global_project_lead.master_assignment = global_objective

    # Generate experts and print their details
    # global_experts = generate_experts(global_project_lead, global_objective)
    # print_experts(global_experts)

    global_writer = generate_writer(global_project_lead, global_objective)
    writer_introductory_prompt = """
    Your task is to always itterate on the editor's critique and complete the assignment.
    
    Assignment: Section by section, write on the assigned topic for the given section.
    
    Respond ONLY in the following JSON format:
    {"article_text": "your current article text"}
    """
    print_experts(global_writer)

    global_editor = generate_editor(global_project_lead, global_objective)
    editor_introductory_prompt = """
    Assignment: Be very critical of your writer colleague and her writing to help her improve the text.
    
    Respond ONLY in the following JSON format:
    {"critique": "your critique of the latest proposed text from the writer"}, "is_the_article_the_best_it_can_be": "yes/no"}
    """
    print_experts(global_editor)

    global_writer_list = initialize_experts(global_writer, writer_introductory_prompt)
    global_writer_list[0].preferred_schema = '{"article_text": ""}'

    global_editor_list = initialize_experts(global_editor, editor_introductory_prompt)
    global_editor_list[0].preferred_schema = '{"critique": ""}, "is_the_article_the_best_it_can_be": "yes/no"}'

    # Give the article outline and the Q&A data to the writer in the writing team, then kick off the writing process
    global_content_conversation = conduct_content_creation([global_writer_list[0], global_editor_list[0]], global_project_lead)
    with open("content_conversation.txt", "a") as f:
        f.write(f"\n{global_content_conversation}")

    time.sleep(3200)
    # Initialize experts and conduct interviews
    global_experts_list = initialize_experts(global_experts)

    playback_thread.start()
    conduct_interviews(global_experts_list, global_objective, global_project_lead)

    # Generate a live research team and define search queries / in a question/answer format?

    # Process trends and create article outline
    # Given the objective and the Q&A available, and the topic performance trends, come up with the ideal article outline
    global_article_outline = process_trends(global_project_lead)
    with open("article_outline.txt", "a") as f:
        f.write(f"\n{global_article_outline}")

    # Generate the final article
    global_final_article = generate_article(global_article_outline, global_content_conversation, global_editor_list)
    with open("final_article.txt", "a") as f:
        f.write(global_final_article)