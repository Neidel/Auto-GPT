import requests
from bs4 import BeautifulSoup
from config import Config
from llm_utils import create_chat_completion

cfg = Config()


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


def extract_hyperlinks(soup):
    hyperlinks = []
    for link in soup.find_all('a', href=True):
        hyperlinks.append((link.text, link['href']))
    return hyperlinks


def format_hyperlinks(hyperlinks):
    formatted_links = []
    for link_text, link_url in hyperlinks:
        formatted_links.append(f"{link_text} ({link_url})")
    return formatted_links


def scrape_links(url):
    response = requests.get(url, headers=cfg.user_agent_header)

    # Check if the response contains an HTTP error
    if response.status_code >= 400:
        return "error"

    soup = BeautifulSoup(response.text, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    hyperlinks = extract_hyperlinks(soup)

    return format_hyperlinks(hyperlinks)


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


def create_message(chunk, desired_information):
    return {
        "role": "user",
        "content": f"\"\"\"{chunk}\"\"\" Using the above text, create a bulleted list of salient facts related to the desired inquiry:\n{desired_information}\nYour list of related salient facts:\n"
    }


def create_final_message(messages):
    return {
        "role": "user",
        "content": f"\"\"\"{messages}\"\"\" Using the list of salient facts above, clean the list of any duplicates and consolidate factual data where necessary:\n"
    }


def summarize_text(text, desired_information):
    if not text:
        return "Error: No text to summarize"

    text_length = len(text)
    print(f"Text length: {text_length} characters")

    summaries = []
    chunks = list(split_text(text, 4097))

    for i, chunk in enumerate(chunks):
        print(f"Summarizing chunk {i + 1} / {len(chunks)}")
        messages = [create_message(chunk, desired_information)]

        summary = create_chat_completion(
            model=cfg.fast_llm_model,
            messages=messages,
            max_tokens=1000,
        )
        summaries.append(summary)

    print(f"Summarized {len(chunks)} chunks.")

    combined_summary = "\n".join(summaries)
    messages = [create_final_message(combined_summary)]

    final_summary = create_chat_completion(
        model=cfg.fast_llm_model,
        messages=messages,
        max_tokens=2000,
    )

    return final_summary
