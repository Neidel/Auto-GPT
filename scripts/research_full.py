
import time
import requests
from bs4 import BeautifulSoup
import openai
from config import Config

import logging
import threading

from tqdm import tqdm

cfg = Config()


class ChatGPT:
    def __init__(self, model, temperature, max_tokens):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def create_chat_completion(self, messages, model=None, temperature=None, max_tokens=None) -> str:
        while True:
            try:
                if cfg.use_azure:
                    response = openai.ChatCompletion.create(
                        deployment_id=cfg.openai_deployment_id,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                else:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

                return response.choices[0].message["content"]
            except Exception as e:
                if 'maximum context length' in str(e):
                    print('Context too long, switching to gpt4 temporarily.')
                    response = openai.ChatCompletion.create(
                        model='gpt-4',
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message["content"]
                print(e)
                print("Retrying...")
                time.sleep(10)

    def create_message(self, chunk):
        return {
            "role": "user",
            "content": f"\"\"\"{chunk}\"\"\" Using the above text, please create a bulleted list of salient facts related to the contents:\n"
        }


gpt = ChatGPT(model='gpt-4', temperature=0.9, max_tokens=100)


class WebScraper:
    def __init__(self, user_agent_header):
        self.user_agent_header = user_agent_header
        self.known_research_urls = self.extract_sources('research.txt')

    def scrape_text(self, url):
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

    def split_text(self, text, max_length=8192):
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

    def extract_sources(self, file_path):
        sources = []
        with open(file_path, 'r') as file:
            for line in file:
                # Check if the line starts with "Source:"
                if line.startswith("Source:"):
                    # Extract the URL by removing the "Source:" prefix and stripping whitespace
                    url = line[len("Source:"):].strip()
                    sources.append(url)
        return sources

    def scrape(self, text, desired_conditions):
        if not text:
            return "Error: No text to summarize"

        text_length = len(text)
        print(f"Text length: {text_length} characters")

        summaries = []
        chunks = list(self.split_text(text, 4097))

        for i, chunk in enumerate(chunks):
            print(f"Summarizing chunk {i + 1} / {len(chunks)}")
            messages = [gpt.create_message(chunk)]

            summary = gpt.create_chat_completion(
                model=cfg.fast_llm_model,
                messages=messages,
                max_tokens=1000,
            )
            summaries.append(summary)

        print(f"Summarized {len(chunks)} chunks.")

        combined_summary = "\n".join(summaries)

        final_summary = gpt.create_chat_completion(
            model='gpt-4',
            messages=[{"role": "user", "content": combined_summary}, {"role": "system", "content": f"Constraints: Please provide a detailed summary of facts related to {desired_conditions}]"}],
            max_tokens=2000,
        )

        return final_summary

    def get_text_summary_with_conditions(self, url, desired_information):
        if url not in self.known_research_urls:
            self.known_research_urls.append(url)
            print(f"Processing new research source: {url}")
            text = self.scrape_text(url)
            summary = self.scrape(text, desired_information)
            if '404' not in summary:
                with open("research.txt", "a") as f:
                    f.write(f'Source: {url}\nSummary:\n{summary}\n\n')

            return summary
        else:
            return "This URL has already been visited and researched. Proceed to another URL on the list."

    def browse_website(self, url, desired_information=None):
        result = self.get_text_summary_with_conditions(url, desired_information)
        return result


scraper = WebScraper(cfg.user_agent_header)


class GoogleSearcher:
    def __init__(self):
        self.rapidapi_key = "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c"
        self.rapidapi_host = "google-web-search1.p.rapidapi.com"
        self.google_search_url = "https://google-web-search1.p.rapidapi.com/"

    def fetch(self, query, num_results=3):
        query_params = {"query": query, "limit": num_results, "related_keywords": "false"}
        headers = {"X-RapidAPI-Key": self.rapidapi_key, "X-RapidAPI-Host": self.rapidapi_host}
        response = requests.get(self.google_search_url, headers=headers, params=query_params)
        results = [result["url"] for result in response.json().get("results", [])]
        # print(f"Searched for: {query}\nFound {len(results)} results\n{results}")
        return results

    def search(self, query, num_results=3):
        raw_results = self.scrub(self.fetch(query, num_results))
        return raw_results

    def scrub(self, url_list):
        cleaned_list = [url for url in url_list if url not in scraper.known_research_urls]
        return cleaned_list


searcher = GoogleSearcher()


class ResearchProject:
    def __init__(self, project_name, search_engine='google'):
        self.project_name = project_name
        self.search_engine = search_engine
        self.logger = logging.getLogger('ResearchProject')
        self.research_objective = None
        self.research_context = None
        self.research_urls = []
        self.current_research_objective = ''
        self.current_research_context = ''
        self.current_research_results = []
        self.known_research_urls = []

    def set_research_objective(self, desired_objective):
        self.current_research_objective = desired_objective

    def extract_research_context(self):
        message = f"User's research objective: {self.current_research_objective}\nContext extraction: Using relevant keywords, entities, or relationships within the text, extract contextual information from the user's research objective that can help guide the creation of subtopics to research."
        response = gpt.create_chat_completion(model='gpt-4', messages=[{"role": "user", "content": message},])
        self.current_research_context = response

    def generate_research_topics(self):
        message = f"Generate a list of research topics related to {self.current_research_objective}\nContext: {self.current_research_context}\nTopics:"
        result = gpt.create_chat_completion(model='gpt-4', messages=[{"role": "user", "content": message}])
        research_topics = result.split("\n")
        return research_topics

    def execute_research_project(self):
        self.extract_research_context()

        research_topics = self.generate_research_topics()

        for research_topic in research_topics:

            research_queries = self.generate_research_queries(research_topic)

            for research_query in research_queries:

                research_urls = searcher.search(research_query)

                for research_url in research_urls:
                    if research_url not in self.known_research_urls:
                        with open('research_urls.txt', "a") as f:
                            f.write(research_url + f' ({research_topic}) ' + "\n")

                        research = scraper.scrape(research_url, research_topic)

                        display_string = f'{research_url}\n{research_topic}\n{research}\n\n'
                        with open('research_summaries.txt', "a") as f:
                            f.write(display_string)

    def generate_research_queries(self, research_topic):
        message = f"Using optimal Google search formatting, generate a comma-separated list of Google search queries related to {research_topic} that will give us the most relevant results:"
        result = gpt.create_chat_completion(model='gpt-4', messages=[{"role": "user", "content": message}])
        search_queries = result.split(", ")
        return search_queries

    def get_next_research_link(self):
        if not self.research_urls:
            return None
        next_url = self.research_urls.pop(0)
        return next_url


if __name__ == '__main__':
    project = ResearchProject('Online Gambling in Maryland')
    project.execute_research_project()
    print('done')
