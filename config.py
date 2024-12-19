# Typing protocols
from typing import Optional, Protocol

class TextAndButtonsDataclass(Protocol):
    text: str
    buttons: Optional[list[list[tuple[str, str]]]]


from aiogram import html

home_button = ('↩️ На главную', 'home')
settings_button = ('⚙️ Настройки', 'cl_settings')
settings_back_button = ('↩️ Назад', 'cl_settings')

home_button_markup = [
    [
        home_button,
    ],
]

class welcome:
    text = html.bold('Добро пожаловать в HomeWork, бот для отслеживания выполнения домашних заданий, поддерживающий функцию создания классов или групп')
    buttons = [
        [
            ('➕ Создать класс', 'wc_create_class'),
            ('👥 Вступить в класс', 'wc_join_class')
        ],
    ]

class wc_create_class1:
    text = 'Дайте имя классу'

class wc_create_class2:
    text = 'Напишите свое имя'

class wc_create_class3:
    text = 'Класс создан. Приглашайте своих одноклассников при помощи кнопки "Добавить"'
    buttons = home_button_markup


class wc_join_class:
    text = 'Чтобы вступить в класс, скиньте ваши айди любому участнику класса, а он добавит вас через кнопку "Добавить".\n\nВаш айди: '\
            + html.code('{user_id}\n')
    buttons = home_button_markup


class home:
    text = html.bold('👋 Привет, {user_name} ({current_class} {current_group})!\n') + 'Выполнено {hw_completed}/{hw_all} домашних заданий.'
    buttons = [
        [
            ('📆 ДЗ', 'hw'),
            ('🗓️ Расписание', 'schedule')
        ],
        [
            settings_button,
        ]
    ]


class cl_settings:
    text = 'Настройки класса ' + html.bold('{current_class}\n\n') + 'Кол-во участников: {cl_members_num}\nГруппы: {cl_groups_list}'
    buttons = [
        [
            ('👤 Участники', 'cl_members'),
            ('👥 Группы', 'cl_groups')
        ],
        [
            home_button
        ]
    ]

class cl_members:
    text = 'Участники класса ' + html.bold('{current_class}') + ':\n\n{cl_members_text}'
    buttons = [
        [
            ('➕ Добавить', 'cl_add_member')
        ],
        [
            settings_back_button
        ]
    ]

class cl_add_member1:
    text = 'Напишите айди человека, которого вы хотите добавить в класс'
class cl_add_member2:
    text = 'Напишите имя участника, которого вы добавляете'
class cl_add_member3:
    text = 'Участник успешно добавлен в класс ' + html.bold('{current_class}')
    buttons = [
        [
            ('👤 Посмотреть в участниках', 'cl_members'),
        ],
        [
            settings_button,
            home_button
        ]
    ]


class cl_groups:
    text = 'Текущие группы:\n\n{cl_groups_members_text}'
    buttons = [
        [
            ('➕ Создать', 'cl_groups_create'),
            ('✍️ Изменить', 'cl_groups_edit'),
            ('✖️ Удалить', 'cl_groups_delete')
        ],
        [
            settings_back_button
        ]
    ]

class cl_groups_create1:
    text = 'Напишите название группы'
class cl_groups_create2:
    text = 'На отдельных строчках напишите имена тех, кого хотите добавить в группу (в будущем можно изменить)'
class cl_groups_create3:
    text = 'Группа ' + html.bold('{ctx.g}') + ' создана!'
    buttons = [
        [
            ('👥 Посмотреть в группах', 'cl_groups'),
        ],
        [
            settings_button,
            home_button
        ]
    ]

class cl_groups_edit1:
    text = 'Введите название группы, которую хотите изменить'
class cl_groups_edit2:
    text = 'Что вы хотите изменить в группе ' + html.bold('{ctx.g}')
    buttons = [ [
            ('✍️ Название', 'cl_groups_edit_name'),
            ('👤 Участники', 'cl_groups_edit_members'),
        ],
        [
            ('Назад', 'cl_groups'),
            settings_button,
            home_button
        ]
    ]

class cl_groups_edit_name1:
    text = 'Введите новое название'
class cl_groups_edit_name2:
    text = 'Группа переименована в ' + html.bold('{ctx.g}')
    buttons = [
        [
            ('👥 Посмотреть в группах', 'cl_groups'),
        ],
        [
            settings_button,
            home_button
        ]
    ]


class hw:
    text = 'Домашнее задание'
    buttons = [
        [
            ('⬅️', 'hw_left'),
            ('📖', 'hw_open'),
            ('✅', 'hw_complete'),
            ('➡️', 'hw_right')
        ],
        [
            ('✍️ Записать', 'hw_write'),
            home_button,
        ]
    ]
    

class schedule:
    text = 'Расписание\nВ разработке'
    buttons = [
        [
            ('⬅️', 'schedule_left'),
            ('ℹ️', 'schedule_info'),
            ('➡️', 'schedule_right')
        ],
        [
            ('⚙️ Изменить расписание', 'schedule_settings'),
            home_button
        ]
    ]
