import json
from call_ai_function import call_ai_function
from llm_utils import create_chat_completion
from config import Config

cfg = Config()


def fix_and_parse_json(json_str: str, try_to_fix_with_gpt: bool = True):
    json_schema = """
    {
        "thoughts":
        {
            "text": "thought",
            "reasoning": "reasoning",
            "plan": "- short bulleted\\n- list that conveys\\n- long-term plan",
            "criticism": "constructive self-criticism"
        },
        "command": {
            "name": "command name",
            "args":{
                "arg name": "value"
            }
        }
    }
    """
    try:
        json_str = json_str.replace('\t', '')
        return json.loads(json_str)
    except Exception as e:
        # Let's do something manually - sometimes GPT responds with something BEFORE the braces:
        # "I'm sorry, I don't understand. Please try again."{"text": "I'm sorry, I don't understand. Please try again.", "confidence": 0.0}
        # So let's try to find the first brace and then parse the rest of the string
        try:
            brace_index = json_str.index("{")
            json_str = json_str[brace_index:]
            last_brace_index = json_str.rindex("}")
            json_str = json_str[:last_brace_index + 1]
            return json.loads(json_str)
        except Exception as e:
            if try_to_fix_with_gpt:
                # print(f"Warning: Failed to parse AI output, attempting to fix.\n If you see this warning frequently, it's likely that your prompt is confusing the AI. Try changing it up slightly.")
                # print(f"Original JSON: {json_str}")
                # Now try to fix this up using the ai_functions
                ai_fixed_json = fix_json(json_str, json_schema, cfg.debug)
                if ai_fixed_json != "failed":
                    return json.loads(ai_fixed_json)
                else:
                    print(f"Failed to fix ai output, telling the AI.")  # This allows the AI to react to the error message, which usually results in it correcting its ways.
                    return json_str
            else:
                raise e


def fix_json(json_str: str, schema: str, debug=False) -> str:
    # Try to fix the JSON using gpt:
    # function_string = "def fix_json(json_str: str, schema:str=None) -> str:"
    args = f"'''Broken JSON String:\n{json_str}'''" + '\n\n' + f'''Destination Target Schema:\n{schema}'''
    description_string = """Fix the provided JSON string to make it parseable and fully complient with the provided schema.\n This function is brilliant at guessing when the format is incorrect or determining the desired command."""
    approved_commands = """
    1. Google Search: "google", args: "input": "<search>"
    2. Browse Website: "browse_website", args: "url": "<url>", "desired_information": "<desired_information>"
    3. Mark Project Completed: "mark_project_completed", args: ""
    """

    result_string = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": f'{args}\n{description_string}\nApproved Command List: {approved_commands}\n!! If the command supplied by the user isnt on the approved list, substitute as best you can !!\n\nCorrected JSON Structure:'}, ]
    )

    # If it doesn't already start with a "`", add one:
    # if not json_str.startswith("`"):
    # json_str = "```json\n" + json_str + "\n```"
    # result_string = call_ai_function(
    # function_string, args, description_string, model=cfg.fast_llm_model
    # )
    if debug:
        print("------------ JSON FIX ATTEMPT ---------------")
        print(f"Original JSON: {json_str}")
        print("-----------")
        print(f"Fixed JSON: {result_string}")
        print("----------- END OF FIX ATTEMPT ----------------")
    try:
        json.loads(result_string)  # just check the validity
        return result_string
    except:
        # Get the call stack:
        # import traceback
        # call_stack = traceback.format_exc()
        # print(f"Failed to fix JSON: '{json_str}' "+call_stack)
        return "failed"
