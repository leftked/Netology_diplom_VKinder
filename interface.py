# импорты
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import re
from datetime import datetime
from config import comunity_token, acces_token
from core import VkTools
from data_store import check_user, add_user, engine


# отправка сообщений
class BotInterface():
    def __init__(self, comunity_token, acces_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.params = {}
        self.worksheets = []
        self.keys = []
        self.offset = 0

    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def bdate_toyear(self, bdate):
        user_year = bdate.split('.')[2]
        now = datetime.now().year
        return now - int(user_year)

    def photos_send(self, worksheet):
        photos = self.vk_tools.get_photos(worksheet['id'])
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'

        return photo_string

    # проверка корректности ввода отсутствующих данных
    def mis_inf(self, missing):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:

                if missing == 1:
                    contains_digit = False
                    for i in event.text:
                        if i.isdigit():
                            contains_digit = True
                            break
                    if contains_digit:
                        self.message_send(event.user_id,
                                          'Неверно указан город. Введите название города без чисел!(например "Москва")')
                    else:
                        return event.text

                if missing == 2:
                    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
                    if not re.match(pattern, event.text):
                        self.message_send(event.user_id, 'Введите вашу дату '
                                                         'рождения в формате (дд.мм.гггг):')
                    else:
                        return self.bdate_toyear(event.text)

    # недостающие данные
    def empty_data(self, event):

        if self.params['city'] is None:
            self.message_send(event.user_id, 'Укажите свой город (например, "Москва")')
            return self.mis_inf(1)

        elif self.params['year'] is None:
            self.message_send(event.user_id, 'Введите дату рождения (дд.мм.гггг):')
            return self.mis_inf(2)

    def get_profile(self, worksheets, event):
        while True:
            if worksheets:
                worksheet = worksheets.pop()

                'проверка анкеты в бд'
                if not check_user(engine, event.user_id, worksheet['id']):
                    'добавить анкету в бд'
                    add_user(engine, event.user_id, worksheet['id'])

                    yield worksheet

            else:
                worksheets = self.vk_tools.search_worksheet(
                    self.params, self.offset)

    # обработка событий / получение сообщений
    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if event.text.lower() == 'привет':
                    '''Логика для получения данных о пользователе'''
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(
                        event.user_id, f'Привет, {self.params["name"]}')

                    # обработка данных, которые не получили
                    self.keys = self.params.keys()
                    for i in self.keys:
                        if self.params[i] is None:
                            self.params[i] = self.empty_data(event)

                    self.message_send(event.user_id, 'Вы успешно зарегистрировались! Введите команду "поиск"')

                elif event.text.lower() == 'поиск':
                    '''Логика для поиска анкет'''
                    self.message_send(
                        event.user_id, 'Начинаю поиск...')

                    ank = next(iter(self.get_profile(self.worksheets, event)))
                    if ank:
                        photo_string = self.photos_send(ank)
                        self.offset += 10

                        self.message_send(
                            event.user_id,
                            f'Гляньте кого мы нашли: {ank["name"]} vk.com/id{ank["id"]}',
                            attachment=photo_string
                        )

                elif event.text.lower() == 'пока':
                    self.message_send(
                        event.user_id, 'До новых встреч')
                else:
                    self.message_send(
                        event.user_id,
                        'Неизвестная команда! Я пока распознаю только команды "привет", "поиск" и "пока"')


if __name__ == '__main__':
    bot_interface = BotInterface(comunity_token, acces_token)
    bot_interface.event_handler()
