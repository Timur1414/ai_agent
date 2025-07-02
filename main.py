import os
from abc import ABC
from openai import OpenAI
from dotenv import load_dotenv
import prompts
import logging


logger = logging.getLogger(__name__)

class Roles:
    CIVILIAN = 1
    SHERIFF = 2
    MAFIA = 3
    DON_MAFIA = 4


class BaseNeuroObject(ABC):
    def __init__(self):
        load_dotenv()
        api_key = os.environ.get('OPENROUTER_API')
        self.client = OpenAI(
            base_url='https://openrouter.ai/api/v1',
            api_key=api_key,
        )
        self.model = 'deepseek/deepseek-r1-0528:free'
        self.memory = []

    def send_message(self, message: str, role: str = 'user') -> str:
        self.memory.append(
            {
                'role': role,
                'content': message
            }
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory,
        )
        self.memory.append(
            {
                'role': 'assistant',
                'content': completion.choices[0].message.content
            }
        )
        logger.info(f'>>> {message}')
        logger.info(f'<<< {completion.choices[0].message.content}')
        return completion.choices[0].message.content


class Player(BaseNeuroObject):
    def __init__(self, game, name: str = '', alive: bool = True, role: int = 0, bot: bool = False):
        super().__init__()
        self.game = game
        self.alive = alive
        self.role = role
        self.bot = bot
        self.name = name

    def say_to_all(self, message: str):
        print(f'Говорит {self.name}: {message}')
        players = [player for player in self.game.players if player != self]
        for player in players:
            player.memory.append(
                {
                    'role': 'user',
                    'content': message
                }
            )
        self.game.memory.append(
            {
                'role': 'user',
                'content': message
            }
        )

    def say_to_narrator(self, message: str):
        self.game.memory.append(
            {
                'role': 'user',
                'content': message
            }
        )

    def introduce(self):
        self.send_message(prompts.START + prompts.ROLES, role='system')
        self.send_message(prompts.BOT_RULES.format(name=self.name, role=self.role), role='system')
        answer = self.send_message('Теперь представься, расскажи о себе другим игрокам так, чтобы они не узнали твою роль, но при этом, чтобы они доверяли тебе. Расскажи ту информацию о своей личности, которую считаешь нужной.')
        self.say_to_all(answer)

    def do_step(self):
        pass

    def vote(self):
        pass

    def __str__(self):
        return f'Я {self.name}. Моя роль - {self.role}'


class Game(BaseNeuroObject):
    def __init__(self):
        super().__init__()
        self.players = []
        self.end = False

    def choose_roles(self):
        print('start choose roles')
        self.send_message(prompts.CHOOSE_ROLES, 'user')
        for i in range(7):
            answer = self.send_message(f'Создай игрока {i + 1}', 'user')
            name, role = answer.strip().split()
            bot = True if i == 0 else False
            match role:
                case 'Мирный':
                    role = Roles.CIVILIAN
                case 'Шериф':
                    role = Roles.SHERIFF
                case 'Мафия':
                    role = Roles.MAFIA
                case 'Дон':
                    role = Roles.DON_MAFIA
            player = Player(self, name, True, role, bot)
            self.players.append(player)
        self.send_message('Больше игроков не будет. ', 'user')

    def main_loop(self):
        pass

    def first_day(self):
        for player in self.players:
            player.introduce()

    def end_game(self):
        pass

    def start_game(self):
        print('start start game')
        self.send_message(prompts.START, 'system')
        self.send_message(prompts.RULES, 'user')
        self.choose_roles()
        self.first_day()
        self.main_loop()
        self.end_game()


def main():
    logging_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(filename='log.log', filemode='w', encoding='utf-8', level=logging.INFO, format=logging_format)
    game = Game()
    game.start_game()


if __name__ == '__main__':
    main()
