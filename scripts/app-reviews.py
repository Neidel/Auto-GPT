
import json
import time

from chat import create_chat_completion

from tqdm import tqdm



def execute_command(command_name, arguments):

    try:
        if command_name == "app_reviews":
            return app_review_blog_writer(arguments["app_name"])

        else:
            return f"Unknown command '{command_name}'. Please refer to the 'COMMANDS' list for availabe commands and only respond in the specified JSON format."
    # All errors, return "Error: + error message"
    except Exception as e:
        return "Error: " + str(e)



def app_reviews(app_name='com.fliff.fapp', sample_size=400):
    import http.client

    conn = http.client.HTTPSConnection("store-apps.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': "68229cdbe2msh5723f22e8f8ab56p1eaefajsn20eccd66fc3c",
        'X-RapidAPI-Host': "store-apps.p.rapidapi.com"
    }

    conn.request("GET", f"/app-reviews?app_id={app_name}&limit={sample_size}&region=us&language=en", headers=headers)

    res = conn.getresponse()
    data = res.read()

    return json.loads(data.decode("utf-8"))['data']['reviews']


def process_app_reviews(app_name):
    reviews = app_reviews(app_name)
    time.sleep(10)
    aggregated_review_block = ''
    total_reviews = 0
    current_aggregate_pros = ''
    current_aggregate_cons = ''
    for review in tqdm(reviews):
        total_reviews += 1
        if total_reviews > 10:
            # print(f'Threshold reached: {total_reviews}. Submitting...')
            total_reviews = 0
            prompt = f'Please evaluate the provided app reviews and compile a list of positive feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_pros}\n\nUpdated bulleted positive feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the pro is> (Reported 3 Times)"}, ]
            )
            print('\n\nPositive\n' + assistant_reply + '\n\n')
            current_aggregate_pros = f'{assistant_reply}'

            # print(f'Threshold reached: {total_reviews}. Submitting...')
            prompt = f'Please evaluate the provided app reviews and compile a list of negative feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_cons}\n\nUpdated bulleted negative feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the con is> (Reported 3 Times)"}, ]
            )
            print('\n\nNegative\n' + assistant_reply + '\n\n')
            current_aggregate_cons = f'{assistant_reply}'

            aggregated_review_block = ''

        aggregated_review_block += '\n' + review["review_text"] + f'({review["author_name"]})' + '\n'

    return current_aggregate_pros, current_aggregate_cons


def aggregate_pros_and_cons(app_name):
    pros_list, cons_list = process_app_reviews(app_name)

    prompt = f'Please write a blog themed summary of the pros:\n{pros_list}'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, {"role": "system", "content": 'In your summary, ignore any issues that only have a single reporter.'}, ]
    )
    final_pros = f'{assistant_reply}'
    prompt = f'Please write a blog themed summary of the cons:\n{cons_list}'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, {"role": "system", "content": 'In your summary, ignore any issues that only have a single reporter.'}, ]
    )
    final_cons = f'{assistant_reply}'

    return final_pros, final_cons, pros_list, cons_list


def app_review_blog_writer(app_name='com.fliff.fapp'):
    pros, cons, pros_list, cons_list = aggregate_pros_and_cons(app_name)

    print(f'Final Pros Summary:\n{pros}')
    print(f'Final Cons Summary:\n{cons}\n\n')

    prompt = f'Please write a blog based on the provided pros and cons:\nPros:\n{pros}\nCons:\n{cons}\n'
    assistant_reply = create_chat_completion(
        model='gpt-4',
        messages=[{"role": "user", "content": prompt}, ]
    )
    return pros_list + '\n\n' + cons_list + '\n\n' + assistant_reply


def process_app_reviews(app_name):
    reviews = app_reviews(app_name)
    time.sleep(10)
    aggregated_review_block = ''
    total_reviews = 0
    current_aggregate_pros = ''
    current_aggregate_cons = ''
    for review in tqdm(reviews):
        total_reviews += 1
        if total_reviews > 10:
            # print(f'Threshold reached: {total_reviews}. Submitting...')
            total_reviews = 0
            prompt = f'Please evaluate the provided app reviews and compile a list of positive feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_pros}\n\nUpdated bulleted positive feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the pro is> (Reported 3 Times)"}, ]
            )
            print('\n\nPositive\n' + assistant_reply + '\n\n')
            current_aggregate_pros = f'{assistant_reply}'

            # print(f'Threshold reached: {total_reviews}. Submitting...')
            prompt = f'Please evaluate the provided app reviews and compile a list of negative feedback. Add to the reported count if the issue already exists in the listing. If its new, list as (Reported 1 Time):\n{aggregated_review_block}\n\nOur current aggregate list is as follows:\n{current_aggregate_cons}\n\nUpdated bulleted negative feedback list:\n'
            time.sleep(5)
            assistant_reply = create_chat_completion(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}, {"role": "system", "content": "Constraints: Do not use the original feedback from the post, summarize yourself instead."}, {"role": "system", "content": "Constraints: If there is a similar review for a given piece of feedback, add to the total count (ex. - <whatever the con is> (Reported 3 Times)"}, ]
            )
            print('\n\nNegative\n' + assistant_reply + '\n\n')
            current_aggregate_cons = f'{assistant_reply}'

            aggregated_review_block = ''

        aggregated_review_block += '\n' + review["review_text"] + f'({review["author_name"]})' + '\n'

    return current_aggregate_pros, current_aggregate_cons



if __name__ == '__main__':
    app_review_blog_writer()