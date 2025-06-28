import os
from openai import OpenAI
from dotenv import load_dotenv


def main():
    load_dotenv()
    api_key = os.environ.get('OPENROUTER_API')
    client = OpenAI(
        base_url='https://openrouter.ai/api/v1',
        api_key=api_key,
    )

    completion = client.chat.completions.create(
        model='deepseek/deepseek-r1-0528:free',
        messages=[
            {
                'role': 'user',
                # 'content': 'Tell me the latest news from the playing sphere. And indicate the date.'
                'content': 'Расскажи последние новости из сферы игр. И укажи даты.'
            }
        ]
    )
    print(completion.choices[0].message.content)


def giga_chat():
    load_dotenv()
    api_key = os.environ.get('GIGA_API')
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_gigachat.chat_models import GigaChat

    giga = GigaChat(
        credentials=api_key,
        verify_ssl_certs=False,
    )

    messages = [
        SystemMessage(
            content='Ты эмпатичный бот, который помогает пользователю узнавать новости.'
        )
    ]

    while True:
        user_input = input('Пользователь: ')
        if user_input == 'пока':
            break
        messages.append(HumanMessage(content=user_input))
        res = giga.invoke(messages)
        messages.append(res)
        print('GigaChat: ', res.content)


if __name__ == '__main__':
    main()
