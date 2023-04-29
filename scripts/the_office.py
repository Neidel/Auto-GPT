
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
        self.chat_history = []
        self.last_message_sent = ""
        self.last_message_received = ""
        self.console_color = next(self.colors)
        self.meeting_notes = ""
        self.known_topics = []
        self.known_themes = []
        self.blog_writing_session = []
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

    def prune_history(self, cutoff=6000):
        total_tokens = 0
        pruned_history = deque()
        for chat_entry in reversed(self.chat_history):
            current_tokens = Expert.count_message_tokens([chat_entry])
            if total_tokens + current_tokens > cutoff:
                print_with_typing_simulation("WARNING: ", Fore.YELLOW, str(total_tokens + current_tokens) + " tokens in chat history, pruning to " + str(total_tokens) + " tokens")
                break
            total_tokens += current_tokens
            pruned_history.appendleft(chat_entry)
        self.chat_history = list(pruned_history)


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

    def send_and_receive_message(self, speaker_obj, messages, model='gpt-4'):
        for message in messages:
            if self.remember_flag:
                speaker_obj.chat_history.append(message)
            speaker_obj.last_message_received = message['content']

            if message["content"] not in self.observed_messages:
                self.observed_messages.append(message["content"])
                print_with_typing_simulation(f'\nSent (to {speaker_obj.role_title}): ', speaker_obj.console_color, message["content"])

        speaker_obj.prune_history()

        while True:
            try:
                if self.remember_flag:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=speaker_obj.chat_history,
                    )
                    break
                else:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=[{"role": "system", "content": speaker_obj.last_message_received}],
                    )
                    break

            except Exception as e:
                error_msg = str(e)
                print_with_typing_simulation("ERROR: ", Fore.RED, error_msg)

                if "maximum context length" in error_msg:
                    retry = False

                    # Extract the number of tokens from the error message
                    tokens_result = re.search(r"resulted in (\d+) tokens", error_msg)
                    if tokens_result:
                        current_tokens = int(tokens_result.group(1))
                        max_tokens = 7192
                        tokens_to_trim = current_tokens - max_tokens

                        # Prune the chat_history based on the required tokens to trim
                        speaker_obj.prune_history(cutoff=max_tokens - tokens_to_trim)

                        # Print a message to inform the user
                        print_with_typing_simulation("INFO: ", Fore.BLUE, f"Reducing the chat history to {max_tokens} tokens")
                        print(f'INFO: {speaker_obj.chat_history}')
                        retry = True
                    else:
                        # If tokens information cannot be extracted, remove the oldest message
                        speaker_obj.chat_history.pop(0)
                        print_with_typing_simulation("INFO: ", Fore.BLUE, "Removing the oldest message from the chat history")
                        print(f'INFO: {speaker_obj.chat_history}')
                        retry = True

                    # Condition to handle cases when the tokenizer calculator is off
                    if not retry and len(speaker_obj.chat_history) > 0:
                        speaker_obj.chat_history.pop(0)
                        print_with_typing_simulation("INFO: ", Fore.BLUE, "Removing another entry from the chat history")
                        print(f'INFO: {speaker_obj.chat_history}')
                else:
                    time.sleep(3)

        text_received = response.choices[0].message["content"]
        speaker_obj.last_message_sent = text_received
        if self.remember_flag:
            speaker_obj.chat_history.append({"role": "assistant", "content": text_received})
            speaker_obj.prune_history()
        if text_received not in self.observed_messages:
            self.observed_messages.append(text_received)
            print_with_typing_simulation(f"\nReceived (from {speaker_obj.role_title}):", speaker_obj.console_color, text_received)

    @staticmethod
    def generate_single_response(messages, model='gpt-3.5-turbo'):
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


def generate_final_editor(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}]}'
    chat.remember_flag = False
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": """
                You have been tasked with defining a final specialist that will take the final conversation between the writer and editor and provide the final blog post text for the following project: 
                %s
                
                The following is a log of all of the experts currently assigned to the project that have contributed, 
                so do your best to make sure that the final specialist is not a duplicate of any of the experts already assigned to the project:
                %s

                Assign the [Role Title] most appropriate to the task and [Main Responsibilities] for the assigned role.
                Relevant subjects: Identify the key [Relevant Subjects] that the expert should be familiar with in order to be successful in the role.
                Fictional backstory: Provide a [Fictional Backstory] for the expert that will help them understand the context of the project.
                Cornerstone theme: Identify the [Cornerstone Theme] that the expert will be associated with.
                Questions: Provide a list of [Questions] to ask themselves that will help focus the effort on their part.

                Respond ONLY in the following JSON format 
                {"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}]}""" % (objective, project_lead.chat_history)},
        ]
    )
    try:
        experts = json.loads(project_lead.last_message_sent)
        chat.remember_flag = True
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json.loads(json_cleaner(project_lead.last_message_sent, json_schema, project_lead))
        chat.remember_flag = True
        return experts


def generate_writing_team(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}'
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": """
            You have been tasked with defining a specialized writing team composed of a single writer and editor for the following project: 
            %s

            For each expert, assign the [Role Title] of writer or editor and [Main Responsibilities] for the assigned role.
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
        experts = json.loads(json_cleaner(project_lead.last_message_sent, json_schema, project_lead))
        return experts


def generate_experts(project_lead, objective):
    json_schema = '{"experts": [{"role_title": "", "main_responsibilities": "", "relevant_subjects": "", "fictional_backstory": "", "cornerstone_theme": "", "questions": ["", ...]}, ...]}'
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
    try:
        experts = json.loads(project_lead.last_message_sent)
        return experts
    except json.decoder.JSONDecodeError:
        print(f'JSON Decoder Failed - Cleaning JSON')
        print(project_lead.last_message_sent)
        experts = json.loads(json_cleaner(project_lead.last_message_sent, json_schema, project_lead))
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
        experts = json.loads(json_cleaner(project_lead.last_message_sent, json_schema, project_lead))
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


def initialize_expert(expert):
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Initializing {expert['role_title']}...")
    expert_clone = Expert(expert["role_title"], expert["main_responsibilities"], expert["relevant_subjects"], expert["fictional_backstory"], expert["cornerstone_theme"], expert["questions"])
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

    chat.send_and_receive_message(final_editor, messages=[{"role": "system", "content": intro}])
    final_article = final_editor.last_message_sent
    print(f'Final Article:\n{final_article}')
    return final_article


def conduct_content_creation(writing_team_list, article_outline, project_lead):
    qna_dicts = project_lead.chat_history
    qna_text_blocks = [qna_dict["content"] for qna_dict in qna_dicts if qna_dict["role"] == "user"]
    qna_pretty = "\n\n".join(qna_text_blocks)
    team_intro = f"""
    Welcome to the Content Creation Team! I am your project lead, and I will be guiding you through the process of creating the content for this article.
    Our task is to write a blog with the following outline structure:
    {article_outline}
    We will be using the following Q&A text as the basis for our article:
    {qna_pretty}
    
    Let's get started! Please introduce yourself and begin.
    """
    team_size = len(writing_team_list)
    team_member_index = 0

    # Set a limit on the number of rounds of conversation.
    max_rounds = 10
    current_round = 0

    # Initialize a variable to store the previous response.
    prev_response = None
    blog_creation_chat_history = []

    while current_round < max_rounds:
        # Select the current team member.
        current_team_member = writing_team_list[team_member_index]

        # If this is the first round, send the team_intro message.
        if current_round == 0 and team_member_index == 0:
            chat.send_and_receive_message(current_team_member, messages=[{"role": "system", "content": team_intro}])
            response = current_team_member.last_message_sent
            blog_creation_chat_history.append({"role": "system", "content": team_intro})

        else:
            # Send a message to the current team member to continue the discussion,
            # including the previous response in the message.
            chat.send_and_receive_message(current_team_member, messages=[{"role": "user", "content": prev_response}])
            response = current_team_member.last_message_sent
            blog_creation_chat_history.append({"role": "user", "content": prev_response})

        # Update the chat history of the current team member.
        current_team_member.chat_history.append({"role": "user", "content": response})

        # Store the current response as the previous response for the next iteration.
        prev_response = response

        # Move on to the next team member.
        team_member_index = (team_member_index + 1) % team_size

        # If we have looped through all team members, increment the round counter.
        if team_member_index == 0:
            current_round += 1
            # You can add a small delay between rounds to simulate real-time conversation.
            time.sleep(1)

    return blog_creation_chat_history


def conduct_interviews(experts_list, objective, project_lead):
    for expert in experts_list:
        print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Starting Interview with {expert.role_title}")

        for question in expert.questions:
            with open("qna.txt", "a") as f:
                f.write(f"\nQ: {question}\n")

            chat.send_and_receive_message(expert, messages=[{"role": "user", "content": f"{question}"}])
            project_lead.chat_history.append({"role": "system", "content": f"{question}"})
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
                
                ----------------------------------------
                
                Task:
                {expert.last_message_sent}
                
                Response:
            """}])
            project_lead.chat_history.append({"role": "assistant", "content": f"{expert.role_title}: {simplified_answer}"})
            print(f'\n\n\n\n\n\nChat History Snapshot for {project_lead.role_title}:\n')
            for entry in project_lead.chat_history:
                print(f'Project Lead Memory Entry: {entry["content"]}\n')
            print(f'\n\n\n\n\n\n')

            # generate_speech(question, 'Kendra')           # Play question with Kendra voice
            # generate_speech(expert.last_message_sent, 'Joanna')  # Play expert's response with Joanna voice
            topics = extract_content(expert.last_message_sent, objective, project_lead)
            process_qna(simplified_answer, topics)


def initialize_experts(experts):
    return [initialize_expert(expert) for expert in experts['experts']]


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

    # Generate experts and print their details
    global_experts = generate_experts(global_project_lead, global_objective)
    print_experts(global_experts)

    global_writing_team = generate_writing_team(global_project_lead, global_objective)
    print_experts(global_writing_team)

    final_editor = generate_final_editor(global_project_lead, global_objective)
    print_experts(final_editor)

    # Initialize experts and conduct interviews
    global_experts_list = initialize_experts(global_experts)
    global_writing_team_list = initialize_experts(global_writing_team)
    global_final_editor = initialize_experts(final_editor)

    playback_thread.start()
    conduct_interviews(global_experts_list, global_objective, global_project_lead)

    # Generate a live research team and define search queries / in a question/answer format?

    # Process trends and create article outline
    # Given the objective and the Q&A available, and the topic performance trends, come up with the ideal article outline
    global_article_outline = process_trends(global_project_lead)
    with open("article_outline.txt", "a") as f:
        f.write(f"\n{global_article_outline}")

    # Give the article outline and the Q&A data to the writer in the writing team, then kick off the writing process
    global_content_conversation = conduct_content_creation(global_writing_team_list, global_article_outline, global_project_lead)
    with open("content_conversation.txt", "a") as f:
        f.write(f"\n{global_content_conversation}")

    # Generate the final article
    global_final_article = generate_article(global_article_outline, global_content_conversation, global_final_editor)
    with open("final_article.txt", "a") as f:
        f.write(global_final_article)
