import time
import openai
from dotenv import load_dotenv
from config import Config
import token_counter

cfg = Config()

from llm_utils import create_chat_completion


def create_chat_message(role, content):
    """
    Create a chat message with the given role and content.

    Args:
    role (str): The role of the message sender, e.g., "system", "user", or "assistant".
    content (str): The content of the message.

    Returns:
    dict: A dictionary containing the role and content of the message.
    """
    return {"role": role, "content": content}


def generate_context(prompt, full_message_history, model):
    current_context = [
        create_chat_message(
            "system", prompt),
        create_chat_message(
            "system", f"The current time and date is {time.strftime('%c')}"),]

    # Add messages from the full message history until we reach the token limit
    next_message_to_add_index = len(full_message_history) - 1
    insertion_index = len(current_context)
    # Count the currently used tokens
    current_tokens_used = token_counter.count_message_tokens(current_context, model)
    return next_message_to_add_index, current_tokens_used, insertion_index, current_context


def chat_with_ai(
        prompt,
        user_input,
        full_message_history):
    while True:
        try:
            model = cfg.fast_llm_model

            current_context = [
                create_chat_message("system", prompt),
            ]
            # Append user input, the length of this is accounted for above
            # current_context.extend([create_chat_message("user", user_input)])

            assistant_reply = create_chat_completion(
                model=model,
                messages=current_context,
                max_tokens=4000,
            )

            print("\n\n------------ CONTEXT SENT TO AI ---------------")
            for message in current_context:
                print(
                    f"{message['role'].capitalize()}: {message['content']}")
                print()
            print("----------- END OF CONTEXT ----------------\n\n")

            # Update full message history
            full_message_history.append(
                create_chat_message(
                    "user", user_input))
            full_message_history.append(
                create_chat_message(
                    "assistant", assistant_reply))

            return assistant_reply
        except openai.error.RateLimitError:
            print("Error: ", "API Rate Limit Reached. Waiting 10 seconds...")
            time.sleep(10)
