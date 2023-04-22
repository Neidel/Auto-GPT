
import openai
from config import Config
import json
from colorama import Fore, Style, init
from itertools import cycle
import random
import time
from typing import Union

config = Config()
init()


def print_with_typing_simulation(title: str, title_color_code: str, content: Union[str, list], min_typing_speed: float = 0.05, max_typing_speed: float = 0.01) -> None:
    """Print content to the console with a colored title and simulate typing."""
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


class GPT4ChatHandler:
    def __init__(self):
        self.model = 'gpt-4'
        self.observed_messages = []

    def generate_single_response(self, messages, model='gpt-4'):
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

    def send_and_receive_message(self, speaker_obj, messages, model='gpt-4'):
        for message in messages:
            speaker_obj.chat_history.append(message)
            speaker_obj.last_message_received = message['content']
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
        if text_received not in self.observed_messages:
            self.observed_messages.append(text_received)
            print_with_typing_simulation(f"\nReceived (from {speaker_obj.function}):", speaker_obj.console_color, text_received)


chat = GPT4ChatHandler()


def generate_experts(project_lead, objective):
    chat.send_and_receive_message(
        project_lead,
        messages=[
            {"role": "system", "content": 'You want to %s. Please describe ten prolific experts you would like to interview to help inform you to achieve your goal. Respond ONLY in the following JSON format {"experts": [{"function": "the experts function","skills": "single string overview of their skills", "introduction": "your imprinting introduction to tell them when they manifest, this message is specifically for the target, speak to them.", "questions": ["question1", "question2" ...]}, ...]}' % objective},
        ]
    )
    experts = json.loads(project_lead.last_message_sent)
    return experts


def extract_topics(text_of_interest):
    try:
        response = chat.generate_single_response(
            messages=[
                {"role": "system", "content": 'Extract all Themes, Topics in the following body of text:\n%s\n Respond ONLY in the following JSON format {"themes": ["theme1", "theme2", "theme3", ...], "topics": ["topics1", "topic2", "topic3", ...]}' % text_of_interest},
            ]
        )
        return json.loads(response)
    except Exception as e:
        print_with_typing_simulation("ERROR: ", Fore.RED, str(e))


def initialize_expert(expert):
    print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Initializing {expert['function']}...")
    expert_clone = Expert(expert["function"], expert["skills"], expert["introduction"], expert["questions"])
    chat.send_and_receive_message(expert_clone, messages=[{"role": "system", "content": expert_clone.introductory_prompt}])
    return expert_clone


def conduct_interviews(experts_list):
    for expert in experts_list:
        print_with_typing_simulation("\nSYSTEM: ", Fore.YELLOW, f"Starting Interview with {expert.function}")

        for question in expert.questions:
            with open("qna.txt", "a") as f:
                f.write(f"\nQ: {question}\n")
            chat.send_and_receive_message(expert, messages=[{"role": "user", "content": f"{question}"}])
            topics = extract_topics(expert.last_message_sent)
            with open("qna.txt", "a") as f:
                f.write(f"A: {expert.last_message_sent}\n\n")

            for topic in topics["topics"]:
                with open("topics.txt", "a") as f:
                    f.write(f"{topic}\n")

            for theme in topics["themes"]:
                with open("themes.txt", "a") as f:
                    f.write(f"{theme}\n")


if __name__ == '__main__':
    objective = "Create blog post copy for an article about the history of metallic sphere ufos or uaps."
    project_lead = Expert('Project Lead', '', '', '')

    experts = generate_experts(project_lead, objective)
    for expert in experts["experts"]:
        try:
            print(f'Expert: {expert["function"]}')
            print(f'Skills: {expert["skills"]}\n')
        except Exception as e:
            print(e)

    experts_list = [initialize_expert(expert) for expert in experts['experts']]
    conduct_interviews(experts_list)
