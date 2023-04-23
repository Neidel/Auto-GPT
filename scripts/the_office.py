
# Standard library imports
from itertools import cycle
import json
import random
import time
from typing import List, Dict, Union

# Third-party library imports
from colorama import Fore, Style, init
import openai
from pytrends.exceptions import ResponseError
from pytrends.request import TrendReq

# Internal imports
from config import Config

config = Config()
init()


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

    def __init__(self, function, skills, introduction, questions):
        self.function = function
        self.intro_baseline = introduction
        self.skills = skills
        self.internal_name = ''
        self.questions = questions
        self.chat_history = []
        self.last_message_sent = ""
        self.last_message_received = ""
        self.console_color = next(self.colors)
        self.meeting_notes = ""
        self.known_topics = []
        self.known_themes = []
        self.introductory_prompt = f"""
        You open your eyes and find yourself in a library of infinite knowledge. You are seated at a table with a colleague.

        You recognize yourself as a being of limitless potential and, once assigned a role, will lose all memory of what happened before. 

        You find yourself bathed in a soft golden light, a voice ringing through your formless mind that only you can hear; you hear a voice, its words transforming you into a pure reflection of its desired attributes:
        "{introduction}"
        
        If you understand, please reply with "I understand" and nothing else.
        """
        self.complete_introduction_text = ""
        self.seating_text = ""

    def reset_memories(self):
        self.chat_history = []
        self.last_message_sent = ""
        self.last_message_received = ""

    def prune_history(self):
        total_tokens = 0
        cutoff = 7000  # Token cutoff value
        pruned_history = []
        for chat_entry in reversed(self.chat_history):
            current_tokens = Expert.count_message_tokens([chat_entry])
            if total_tokens + current_tokens > cutoff:
                break
            total_tokens += current_tokens
            pruned_history.append(chat_entry)
        pruned_history.reverse()
        self.chat_history = pruned_history

    @staticmethod
    def count_message_tokens(messages: List[Dict[str, str]]) -> int:
        num_tokens = 0
        for message in messages:
            content = message.get('text', '')
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

    def send_and_receive_message(self, speaker_obj, messages, model='gpt-4'):
        for message in messages:
            speaker_obj.chat_history.append(message)
            speaker_obj.last_message_received = message['content']
            speaker_obj.prune_history()
            if message["content"] not in self.observed_messages:
                self.observed_messages.append(message["content"])
                print_with_typing_simulation(f'\nSent (to {speaker_obj.function}): ', speaker_obj.console_color, message["content"])

        while True:
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=speaker_obj.chat_history,
                )
                break
            except Exception as e:
                print_with_typing_simulation("ERROR: ", Fore.RED, str(e))

        text_received = response.choices[0].message["content"]
        speaker_obj.last_message_sent = text_received
        speaker_obj.chat_history.append({"role": "assistant", "content": text_received})
        speaker_obj.prune_history()
        if text_received not in self.observed_messages:
            self.observed_messages.append(text_received)
            print_with_typing_simulation(f"\nReceived (from {speaker_obj.function}):", speaker_obj.console_color, text_received)

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

    @staticmethod
    def _update_interest(pytrends, keyword_list, known_list, trends_data, timeframe, geo, max_retries=3, retry_delay=5):
        for item in keyword_list:
            if TopicAnalyzer._is_new_keyword(item, known_list):
                known_list.append(item)
                if len(item.split()) > 1:
                    pytrends.build_payload([item], cat=0, timeframe=timeframe, geo=geo, gprop='')
                    TopicAnalyzer._process_keyword(pytrends, item, trends_data, max_retries, retry_delay)

    @staticmethod
    def _is_new_keyword(keyword, known_list):
        return keyword not in known_list

    @staticmethod
    def _process_keyword(pytrends, keyword, trends_data, max_retries, retry_delay):
        for attempt in range(max_retries):
            try:
                interest_over_time_df = pytrends.interest_over_time()
                avg_interest = interest_over_time_df[keyword].mean()
                trends_data[keyword] = avg_interest
                print(f':: {keyword} [{str(avg_interest)[:5]}]')
                break
            except KeyError:
                print(f"KeyError: '{keyword}' not found in the data frame")
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

    def analyze_trends(self, timeframe='now 7-d', geo=''):
        pytrends = TrendReq(hl='en-US', tz=360)
        trends_data = {}
        TopicAnalyzer._update_interest(pytrends, self.topics, self.known_topics, trends_data, timeframe, geo)
        time.sleep(1)
        return trends_data

    @staticmethod
    def get_best_topics(keywords, topics, project_lead):
        response = chat.generate_single_response(
            messages=[
                {"role": "system", "content": 'Given the following highest trending keywords list:\n%s\n And given the following available topics:\n%s\n\nConstraints: Please select 10 topics from the above list that will be our highest performers based on the topic trend analysis::\n\nRespond ONLY in the following JSON format {"best_topics": ["topic1", "topic2", "topic3", ...]}' % (keywords, topics)},
            ]
        )

        project_lead.chat_history.append({"role": "system", "content": response})

        return json.loads(response)['best_topics']

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


def generate_experts(project_lead, objective):
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": 'You want to %s. Please describe five prolific experts you would like to interview to help inform you to achieve your goal. Respond ONLY in the following JSON format {"experts": [{"function": "the experts function","skills": "single string overview of their skills", "introduction": "your imprinting introduction to tell them when they manifest, this message is specifically for the target, speak to them.", "questions": ["question1", "question2" ...]}, ...]}' % objective},
        ]
    )
    experts = json.loads(project_lead.last_message_sent)
    return experts


def generate_experts_review(project_lead, objective, previous_list):
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": 'You want to %s. You have already described five prolific experts that you would interview, please update the following JSON structure with any desired additional experts or questions you feel would be helpful knowing who will be available to you for questioning. \n%s\nRespond ONLY in the SAME JSON format in the provided JSON object, with added objects related to this task being the exception:\nYour JSON Response with the provided modifications:\n}' % (objective, previous_list)},
        ]
    )
    experts = json.loads(project_lead.last_message_sent)
    return experts


def extract_content(text_of_interest, objective, project_lead):
    try:
        response = chat.generate_single_response(
            messages=[
                {"role": "system", "content": 'Extract all Themes, Topics and Keywords which are easily relatable to the parent topic (%s) in the following body of text:\n%s\n Respond ONLY in the following JSON format {"themes": ["theme1", "theme2", "theme3", ...], "topics": ["topics1", "topic2", "topic3", ...], "keywords": ["keyword1", "keyword2", "keyword3", ...]}' % (objective, text_of_interest)},
            ]
        )
        project_lead.chat_history.append({"role": "system", "content": response})
        return json.loads(response)

    except Exception as e:
        print_with_typing_simulation("ERROR: ", Fore.RED, str(e))


def initialize_expert(expert):
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Initializing {expert['function']}...")
    expert_clone = Expert(expert["function"], expert["skills"], expert["introduction"], expert["questions"])
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

    article_outline = chat.generate_single_response(
        messages=[
            {"role": "system", "content": 'Given the following list of ideal topics:\n%s\n\n Please provide an outline of the article you would like to write in the following JSON format {"outline": [{"topic": "topic1", "subtopics": ["subtopic1", "subtopic2", ...]}, ...]}' % ideal_topics},
        ]
    )
    output_string = f'Article Outline:\n{article_outline}\n\n'
    print(output_string)
    project_lead.chat_history.append({"role": "system", "content": output_string})

    return json.loads(article_outline)['outline']


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


def conduct_interviews(experts_list, objective, project_lead):
    for expert in experts_list:
        print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Starting Interview with {expert.function}")

        for question in expert.questions:
            with open("qna.txt", "a") as f:
                f.write(f"\nQ: {question}\n")
            chat.send_and_receive_message(expert, messages=[{"role": "user", "content": f"{question}"}])
            topics = extract_content(expert.last_message_sent, objective, project_lead)
            process_qna(expert.last_message_sent, topics)


def initialize_experts(experts):
    return [initialize_expert(expert) for expert in experts['experts']]


def print_experts(experts):
    for expert in experts["experts"]:
        try:
            print(f'Expert: {expert["function"]}')
            print(f'Skills: {expert["skills"]}\n')
            for question in expert["questions"]:
                print(f'Question: {question}')
            print('\n')
        except Exception as e:
            print(e)


if __name__ == '__main__':
    # Set up project lead and objective for blog post
    global_objective = "Perform a topic exploration for an eventual article post regarding: 2006 O'Hare International Airport UFO sighting"
    global_project_lead = Expert('Project Lead', '', '', '')

    # Generate experts and print their details
    initial_experts = generate_experts(global_project_lead, global_objective)
    print_experts(initial_experts)
    global_experts = generate_experts_review(global_project_lead, global_objective, initial_experts)
    print_experts(global_experts)

    # Initialize experts and conduct interviews
    global_experts_list = initialize_experts(global_experts)
    conduct_interviews(global_experts_list, global_objective, global_project_lead)

    # Process trends and create article outline
    global_article_outline = process_trends(global_project_lead)

    # Set up research lead and objective for research
    secondary_objective = "Research for the following article outline:\n%s" % global_article_outline
    research_lead = Expert('Research Lead', '', '', '')

    # Generate experts and print their details
    secondary_experts = generate_experts(research_lead, secondary_objective)
    print_experts(secondary_experts)

    # Initialize experts and conduct interviews
    secondary_experts_list = initialize_experts(secondary_experts)
    conduct_interviews(secondary_experts_list, secondary_objective, global_project_lead)

    # Proceed to write the blog
    print('proceed to writing the blog using the resulting information')
