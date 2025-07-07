import os
from abc import ABC
import random
import torch
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
        url = os.environ.get('URL')
        # url = 'http://127.0.0.1:11434/v1'
        # url = 'https://openrouter.ai/api/v1'
        self.client = OpenAI(
            base_url=url,
            api_key=api_key,
        )
        # self.model = 'deepseek/deepseek-r1-0528:free'
        self.model = 'llama3'
        self.memory = []

    def send_message(self, message: str, role: str = 'user', temperature: float = 0.0, presence_penalty: float = 0.0) -> str:
        self.memory.append(
            {
                'role': role,
                'content': message
            }
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=self.memory,
            temperature=temperature,
            presence_penalty=presence_penalty,
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
        if bot:
            self.send_message(prompts.START + prompts.ROLES, role='system')
            self.send_message(prompts.BOT_RULES.format(name=self.name.upper(), role=self.role), role='system')

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
        message = f'Говорит {self.name}: {message}'
        self.game.memory.append(
            {
                'role': 'user',
                'content': message
            }
        )

    def introduce(self):
        if self.bot:
            answer = self.send_message(
                'Теперь представься, расскажи о себе другим игрокам так, чтобы они не узнали твою роль, но при этом, '
                'чтобы они доверяли тебе. Расскажи ту информацию о своей личности, которую считаешь нужной.', presence_penalty=0.7, temperature=0.2)
        else:
            answer = input('Представьтесь и расскажите о себе:\n')
        self.say_to_all(answer)

    def do_step(self, message, **kwargs) -> str:
        if self.bot:
            return self.send_message(message, **kwargs)
        else:
            return input('Введите сообщение:\n')

    def __str__(self):
        return f'Я {self.name}. Моя роль - {self.role}'


class Game(BaseNeuroObject):
    def __init__(self):
        torch.manual_seed(random.randint(0, 50))
        super().__init__()
        self.players = []
        self.end = False
        self.players_count = 5

    def find_player_by_name(self, name: str, only_alive: bool = True) -> Player | None:
        for player in self.players:
            if player.name == name:
                if only_alive:
                    return player if player.alive else None
                else:
                    return player
        return None

    def find_players_by_role(self, role: str | int, only_alive: bool = True) -> list[Player]:
        result = []
        if isinstance(role, str):
            match role:
                case 'Мирный':
                    role = Roles.CIVILIAN
                case 'Шериф':
                    role = Roles.SHERIFF
                case 'Мафия':
                    role = Roles.MAFIA
                case 'Дон':
                    role = Roles.DON_MAFIA
        for player in self.players:
            if player.role == role:
                if only_alive:
                    if player.alive:
                        result.append(player)
                else:
                    result.append(player)
        return result

    def say_to_player(self, player: Player, message: str):
        player.memory.append(
            {
                'role': 'user',
                'content': message,
            }
        )
        if not player.bot:
            print(message)

    def say_to_all(self, message: str):
        for player in self.players:
            self.say_to_player(player, message)

    def choose_roles(self):
        print('start choose roles')
        self.send_message(prompts.CHOOSE_ROLES, 'user')
        for i in range(self.players_count):
            correct = False
            player = None
            while not correct:
                correct = True
                bot = False if i == 0 else True
                answer = self.send_message(f'Создай игрока {i + 1}', 'user')
                name, role = answer.strip().split()
                if not bot:
                    name = input('Введите имя:\n')
                match role:
                    case 'Мирный':
                        role = Roles.CIVILIAN
                    case 'Шериф':
                        role = Roles.SHERIFF
                    case 'Мафия':
                        role = Roles.MAFIA
                    case 'Дон':
                        role = Roles.DON_MAFIA
                    case _:
                        correct = False
                        self.send_message(
                            'Неправильный формат ответа. Вспомни первое сообщение и отвечай только так, как там сказано. Формат ответа: <имя> <роль>. Два слова на руссокм языке.')
                player = Player(self, name, True, role, bot)
            self.players.append(player)
        all_players = '\n'.join([f'Имя: {player.name} Роль: {player.role},' for player in self.players])
        self.send_message(f'Больше игроков не будет.\nИтоговый список игроков: {all_players}', 'user')

    def night(self):
        answer = self.send_message(prompts.START_NIGHT, temperature=0.1)
        print(f'Ведущий: {answer}')
        '''
        Выбор порядка ходом можно строго задать алгоритмом, а можно сгенерировать нейронкой???
        '''
        # order = self.send_message(prompts.CREATE_ORDER)
        # for player in self.players:
        #     print(player)
        # print(order)
        order = []
        first = self.find_players_by_role(2)
        second = self.find_players_by_role(3)
        third = self.find_players_by_role(4)
        order.append(first)
        order.append(second)
        order.append(third)
        if first:
            sheriff = first[0]
            answer = self.send_message('Скажи, что сейчас должен проснуться шериф и проверить роль какого-то игрока. НЕ ПРИДУМЫВАЙ И НЕ ВЫБИРАЙ ИМЁН. Не выходи из роли рассказчика.', temperature=0.2)
            print(f'Ведущий говорит: {answer}')
            # answer = sheriff.send_message(prompts.SHERIFF_WAKE_UP).strip().replace('.', '').split()[-1]
            answer = sheriff.do_step(prompts.SHERIFF_WAKE_UP).strip().replace('.', '').split()[-1]
            # print(f'{sheriff.name} говорит: {answer}')
            answer = 'Роль игрока, которого ты проверил:' + self.send_message(f'Скажи роль игрока {answer}.')
            # print(f'Ведущий говорит: {answer}')
            self.say_to_player(sheriff, answer)
        if second or third:
            don = third[0]
            answer = self.send_message('Скажи, что сейчас должны проснуться мафия и дон. Они должны выбрать какого игрока убить. НЕ ПРИДУМЫВАЙ И НЕ ВЫБИРАЙ ИМЁН. Не выходи из роли рассказчика.', temperature=0.2)
            print(f'Ведущий говорит: {answer}')
            for mafia in second:
                # answer = mafia.send_message(prompts.MAFIA_WAKE_UP)
                answer = mafia.do_step(prompts.MAFIA_WAKE_UP)
                # print(f'{mafia.name} говорит: {answer}')
                self.say_to_player(don, answer)
            answer = self.send_message('Скажи, что сейчас дон должен выбрать игрока. НЕ ПРИДУМЫВАЙ И НЕ ВЫБИРАЙ ИМЁН. Не выходи из роли рассказчика.', temperature=0.2)
            print(f'Ведущий говорит: {answer}')
            # answer = don.send_message(prompts.MAFIA_WAKE_UP + '\nТеперь, Дон (ты), должен выбрать, кого убить. Ты можешь согласиться или нет с вариантом из прошлых сообщений. Скажи ТОЛЬКО ОДНО ИМЯ из списка живых игроков.').strip().replace('.', '').split()[-1]
            answer = don.do_step(prompts.MAFIA_WAKE_UP + '\nТеперь, Дон (ты), должен выбрать, кого убить. Ты можешь согласиться или нет с вариантом из прошлых сообщений. Скажи ТОЛЬКО ОДНО ИМЯ из списка живых игроков.').strip().replace('.', '').split()[-1]
            target_to_kill = self.find_player_by_name(answer.strip().replace('.', ''))
            # print(f'{don.name} говорит: {answer}')
            don.say_to_narrator(f'Члены мафии решили убить игрока {answer}')
            target_to_kill.alive = False

    def day(self):
        answer = self.send_message('Наступает день, скажи об этом игрокам, не забудь добавить, что город просыпается. Подведи итог: кого убила мафия.', temperature=0.2)
        print(f'Ведущий говорит: {answer}')
        self.say_to_all(answer)
        answer = self.send_message(prompts.START_DISCUSSION)
        for player in self.players:
            if player.alive:
                # print(f'{player.name} говорит: {player.send_message(answer, temperature=0.2)}')
                answer = player.do_step(answer, temperature=0.2)
                # print(f'{player.name} говорит: {answer}')
                self.say_to_all(f'{player.name} говорит: {answer}')
        answer = self.send_message(prompts.START_VOTING)
        print(f'Ведущий говорит: {answer}')
        count_votings = dict([(player.name, 0) for player in self.players])
        for player in self.players:
            if player.alive:
                name = player.do_step(answer).strip().replace('.', '').split()[-1]
                # print(f'{player.name} говорит: {name}')
                self.say_to_all(f'{player.name} говорит: {name}')
                count_votings[name] += 1
        count_votings = sorted(count_votings.items(), key=lambda x: x[1], reverse=True)
        if count_votings[0][1] == count_votings[1][1]:
            return
        target_to_exclude = self.find_player_by_name(count_votings[0][0])
        message = f'{target_to_exclude.name} исключён (убит) в ходе голосования.'
        print(message)
        self.say_to_all(message)
        target_to_exclude.alive = False
        if target_to_exclude.role == Roles.DON_MAFIA:
            self.choose_new_don()

    # def check_order(self, order: str) -> bool:
    #     count_alive = self.players.count(lambda player: player.alive == True)
    #
    # def parse_order(self, order: str) -> list[Player]:
    #     pass

    def main_loop(self):
        print('start game')
        iteration = 1
        while not self.end:
            self.night()
            self.day()
            iteration += 1
            answer = self.send_message('Игра закончена? Ответь ТОЛЬКО ОДНО СЛОВО: "ДА" или "НЕТ".').strip().replace('.', '')
            if answer == 'ДА':
                self.end = True

    def first_day(self):
        print('start introducing')
        for player in self.players:
            player.introduce()
        players_status = 'Итак, список всех игроков и их статус. Запомни этот список. В дальнейшем обращайся к игрокам только по их именам.'
        players_status += '\n'.join([f'Имя:{player.name} Живой:{player.alive}' for player in self.players])
        for player in self.players:
            if player.bot:
                message = players_status.replace(player.name, f'{player.name} (Ты)')
                self.say_to_player(player, message)
        players_status = 'Итак, список всех игроков и их статус. Запомни этот список. В дальнейшем обращайся к игрокам только по их именам.'
        players_status += '\n'.join(
            [f'Имя:{player.name} Живой:{player.alive} Роль:{player.role}' for player in self.players])
        self.send_message(players_status)

    def end_game(self):
        answer = self.send_message('Скажи, кто победил? Мирные или мафия?', temperature=0.3)
        print(f'Ведущий говорит: {answer}')
        torch.cuda.empty_cache()

    def start_game(self):
        print('start start game')
        self.send_message(prompts.START, 'system')
        self.send_message(prompts.RULES, 'user')
        self.choose_roles()
        self.first_day()
        self.main_loop()
        self.end_game()

    def choose_new_don(self):
        mafia = self.find_players_by_role(Roles.MAFIA)
        new_don = random.choice(mafia)
        new_don.role = Roles.DON_MAFIA


def main():
    logging_format = '%(asctime)s %(levelname)s %(message)s'
    logging.basicConfig(filename='log.log', filemode='w', encoding='utf-8', level=logging.INFO, format=logging_format)
    game = Game()
    game.start_game()


if __name__ == '__main__':
    main()
