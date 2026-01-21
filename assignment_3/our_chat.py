from time import time

from openai import Client

from usage import print_usage


def main():
    client = Client()
    model = "gpt-5-nano"
    history = []
    usages = []
    try:
        while True:
            message = input('User: ')
            history.append({'role': 'user', 'content': message})
            start = time()
            response = client.responses.create(
                model=model,
                input=history,
                reasoning={'effort': 'low'}
            )
            history.append({'role': 'assistant', 'content': response.output_text})
            usages.append(response.usage)
            print(f'Took {round(time() - start, 2)} seconds')
            print('Agent:', response.output_text)
    except KeyboardInterrupt:
        pass

    print_usage(model, usages)


if __name__ == '__main__':
    main()
