# Typing protocols
from typing import Optional, Protocol
from datetime import date
from aiogram import html

START_OF_YEAR = date(2024, 9, 2)
END_OF_YEAR = date(2025, 6, 1)
HOLIDAYS = [
    date(2024, 10, 28),
    date(2024, 12, 30),
    date(2025, 1, 6),
    date(2025, 4, 7),
    date(2025, 5, 26)
]
VERSION = '1.2.2_1'
DEVELOPER = '@bleuuu1'
TGC = 'https://t.me/HoneyTeamC'
GITHUB = 'https://github.com/honey-team/hw-bot'

class TextDataclass(Protocol):
    text: str

class TextAndButtonsDataclass(TextDataclass):
    buttons: Optional[list[list[tuple[str, str]]]]


back_button_text = '↩️ Назад'
settings_back_button = (back_button_text, 'cl_settings')
groups_back_button = (back_button_text, 'cl_groups')
schedule_back_button = (back_button_text, 'schedule')
schedule_settings_back_button = (back_button_text, 'schedule_settings')

home_button = ('↩️ На главную', 'home')
settings_button = ('⚙️ Настройки', 'cl_settings')

hw_button = ('📆 ДЗ', 'hw')
schedule_button = ('🗓️ Расписание', 'schedule')

home_button_markup = [[home_button]]

sch_subj_edit_markup = [
    [ (back_button_text, 'sch_info_edit') ],
    [ schedule_button, home_button ]
]

class Emojies:
    admin = '👮'
    owner = '👑'

class info:
    text = (f'{html.bold('Информация о HomeWork')}\n'
            f'💻 Версия: {html.bold(VERSION)}\n'
            f'👨‍💻 Разработчик: {html.bold(DEVELOPER)}\n'
            f'🌐 Телеграмм канал: {html.link(TGC.replace('https://t.me/', ''), TGC)}\n'
            f'🐈‍⬛ GitHub: {html.link(GITHUB.replace('https://github.com/', ''), GITHUB)}')
    buttons = [[home_button]]


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
    text = (
        'Чтобы вступить в класс, скиньте ваши айди любому участнику класса, а он добавит вас через кнопку "Добавить".'
        '\n\nВаш айди: '
    ) + html.code('{user_id}\n')
    buttons = home_button_markup


class home:
    if_not_holiday = 'ДЗ: {hw_comp_text}'
    if_there_isnt_hw = 'На завтра нет домашних заданий'
    if_holiday = 'Завтра нет занятий'
    text = html.bold('👋 {home.hello}, {user_name} ({current_class}{current_group})!\n') + '{home.hw}'
    no_classes_basic_user_buttons = [
        [
            hw_button,
            schedule_button
        ],
        [
            ('📕 Инфо', 'info')
        ]
    ]
    no_classes_buttons_admin = [
        no_classes_basic_user_buttons[0],
        [settings_button] + no_classes_basic_user_buttons[1]
    ]
    basic_user_buttons = [
        [
            ('⏰ Сейчас', 'now')
        ]
    ] + no_classes_basic_user_buttons
    buttons = [
        [
            ('⏰ Сейчас', 'now')
        ]
    ] + no_classes_buttons_admin


class now:
    is_break = 'Перемена'
    is_lesson = '{now_lesson}{now_office}'
    is_lesson_info = ('🚪 Кабинет: ' + html.bold('{now_office}\n') +
                      '👩‍🏫 Учитель: ' + html.bold('{now_teacher}'))
    is_break_info = '➡️ Следующий урок - ' + html.bold('{now_next_lesson}\n')

    text = html.bold('({now.time})') + (' {now.bell} {now.lesson_or_break} ({now.minutes_to_end} минут до конца)\n'
                                        '{now.info}\n')
    text_lessons_ended = '{now.time} ❌ Уроки закончились'
    text_food = '({now.time}) {now.bell} 🍽️ {food.name} ({now.minutes_to_end} минут до конца)\n'
    text_fallback_bells = '⚠️ Настройте расписание звонков в настройках расписания.'

    buttons = home_button_markup


class cl_settings:
    text = 'Настройки класса ' + html.bold('{current_class}\n\n') + 'Кол-во участников: {cl_members_num}\nГруппы: {cl_groups_list}'
    buttons = [
        [
            ('👤 Участники', 'cl_members'),
            ('👥 Группы', 'cl_groups'),
        ],
        [
            ('🗓️ Расписание', 'schedule_settings'),
            ('📄 Импорт/Экспорт', 'import_export'),
        ],
        [
            home_button
        ]
    ]
class import_export:
    text = 'Выберите, хотите ли вы экспортировать или импортировать JSON файл с данными о классе'
    buttons = [
        [
            ('⬇️ Импорт', 'import'),
            ('⬆️ Экспорт', 'export')
        ],
        [
            home_button
        ]
    ]

class import1:
    text = 'Отправьте json файл конфигурации для импорта данных.'
    buttons = [
        [
            ('❌ Отмена', 'import_cancel')
        ]
    ]
class import2:
    text = 'Готово!'
    buttons = [
        [
            (back_button_text, 'import_export'),
            home_button
        ]
    ]
class import_not_finded_file:
    text = 'Файл конфигурации не обнаружен, попробуйте еще раз'
    buttons = [
        [
            ('❌ Отмена', 'import_cancel')
        ]
    ]

class export:
    text = 'Вот ваш экспортированный файл конфигурации для будущего импорта данных'
    buttons = [
        [
            (back_button_text, 'import_export'),
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
    buttons = [[
        ('❌ Отмена', 'cl_add_member_return')
    ]]
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
    text = f'Группа {html.bold('{ctx.g}')} создана!'
    buttons = [
        [
            groups_back_button,
        ],
        [
            settings_button,
            home_button
        ]
    ]

class cl_groups_edit1:
    text = 'Введите название группы, которую хотите изменить'
class cl_groups_edit2:
    text = f'Что вы хотите изменить в группе {html.bold('{ctx.g}')}'
    buttons = [ [
            ('✍️ Название', 'cl_groups_edit_name'),
            ('👤 Участники', 'cl_groups_edit_members'),
        ],
        [
            groups_back_button,
            settings_button,
            home_button
        ]
    ]

class cl_groups_edit_name1:
    text = 'Введите новое название'
class cl_groups_edit_name2:
    text = f'Группа переименована в {html.bold('{ctx.g}')}'
    buttons = [
        [
            ('👥 Посмотреть в группах', 'cl_groups'),
        ],
        [
            settings_button,
            home_button
        ]
    ]

class cl_groups_edit_members1:
    text = f'Введите список участников которые должны быть прикреплёнными к группе {html.bold('{ctx.g}')}'
class cl_groups_edit_members2:
    text = f'Список участников группы {html.bold('{ctx.g}')} обновлён!'
    buttons = [
        [
            ('👥 Посмотреть в группах', 'cl_groups'),
        ],
        [
            settings_button,
            home_button
        ]
    ]

class cl_groups_delete1:
    text = 'Введите название группы, которую хотите удалить'

class cl_groups_delete2:
    text = f'Группа {html.bold('{ctx.g}')} удалена'
    buttons = [
        [
            groups_back_button,
        ],
        [
            settings_button,
            home_button
        ]
    ]


class hw:
    text = 'Домашнее задание на {current_day}\n{hw_text}'
    buttons = [
        [
            ('⬅️', 'hw_left'),
            ('📆', 'hw_tommorrow'),
            ('📖', 'hw_open'),
            ('✅', 'hw_complete'),
            ('➡️', 'hw_right')
        ],
        [
            home_button,
        ]
    ]

class hw_open1:
    text = 'Выберите предмет для открытия'
    buttons = [
        [
            (back_button_text, 'back_to_hw'),
        ]
    ]
class hw_open2:
    text = 'Домашнее задание на {current_day} по предмету {current_lesson}{hw_is_completed}\n\n{hw}'
    buttons = [
        [
            ('✍️ Изменить', 'hw_open_edit'),
            ('✅ Выполнено', 'hw_open_complete'),
            (back_button_text, 'hw_return')
        ]
    ]
class hw_open_btn_uncomplete:
    text = 'Домашнее задание на {current_day} по предмету {current_lesson}{hw_is_completed}\n\n{hw}'
    buttons = [
        [
            ('✍️ Изменить', 'hw_open_edit'),
            ('❌ Не выполнено', 'hw_open_complete'),
            (back_button_text, 'hw_return')
        ]
    ]
class hw_open_none:
    text = 'Домашнее задание на {current_day} по предмету {current_lesson}\n\nДомашнее задание отсутствует'
    buttons = [
        [
            ('✍️ Записать', 'hw_open_edit'),
            (back_button_text, 'hw_return')
        ]
    ]

class hw_open_complete:
    text = 'Готово!'
    buttons = [
        [
            (back_button_text, 'hw_return_open')
        ],
        [
            hw_button,
            home_button
        ]
    ]
class hw_open_complete_none:
    text = (f'{html.bold('❌ Ошибка')}\n\n'
            'Сначала впишите домашнее задание, а затем отмечайте его как выполненное!')
    buttons = [
        [
            (back_button_text, 'hw_return_open')
        ]
    ]

class hw_open_edit1:
    text = ('Введите текст домашнего задания, а также, если хотите, добавьте фотографии или файлы. '
            'Когда закончите, нажмите на кнопку')
    buttons = [
        [
            ('✅', 'hw_open_edit_end'),
        ]
    ]
class hw_open_edit2:
    text = 'Готово!'
    buttons = [
        [
            (back_button_text, 'hw_return_open')
        ],
        [
            hw_button,
            home_button
        ]
    ]

class hw_complete1:
    text = 'Выберите домашнее задание для того, чтобы отметить как выполненное/невыполненное'
    buttons = [
        [
            (back_button_text, 'back_to_hw')
        ],
        [
            hw_button,
            home_button
        ]
    ]
class hw_complete2:
    text = 'Готово!'
    buttons = [
        [
            hw_button,
            home_button
        ]
    ]
    

class schedule:
    text = 'Расписание на {current_day}\n{schedule_text}'
    buttons = [
        [
            ('⬅️⬅️', 'schedule_left_week'),
            ('⬅️', 'schedule_left'),
            ('📆', 'schedule_today'),
            ('ℹ️', 'schedule_info'),
            ('➡️', 'schedule_right'),
            ('➡️➡️', 'schedule_right_week')
        ],
        [
            home_button
        ]
    ]

class schedule_info1:
    text = 'Выберите урок для просмотра информации'
class schedule_info2:
    text = 'Информация о ' + html.bold('{cles.name}') + '\nКабинет: {cles.office}\nУчитель: {cles.teacher}'
    buttons = [
        [
            ('️✍️ Изменить', 'sch_info_edit')
        ],
        [
            schedule_back_button
        ]
    ]

class schedule_settings:
    text = 'Настройки расписания'
    buttons = [
        [
            ('📚 Предметы', 'sch_subj'),
            ('🔔 Звонки', 'sch_bells')
        ],
        [
            schedule_back_button,
            home_button
        ]
    ]

class sch_subj:
    text = 'Текущие предметы:\n{subjects_text}'
    buttons = [
        [
            ('➕ Создать', 'sch_subj_create'),
            ('️️✍️ Изменить', 'sch_subj_edit'),
            ('❌ Удалить', 'sch_subj_delete')
        ],
        [
            schedule_settings_back_button,
            home_button
        ]
    ]

class sch_subj_create1:
    text = 'Напишите название предмета'
class sch_subj_create2:
    text = 'Введите список групп которые должны будут иметь данный предмет (на каждой строке - одна группа). Если вы хотите создать общий для всех участников класса предмет, то нажмите на кнопку'
    buttons = [
        [
            ('❌', 'sch_subj_create_general')
        ]
    ]
class sch_subj_create3:
    text = \
    '''
    Введите расписание по следующему формату:
    - Строка, состоящяя из цифр
    - Каждая нечетная цифра - день в расписании (0, 1, 2, 3, 4 - дни недели в нечетной неделе; 5, 6, 7, 8, 9 - дни недели в четной неделе)
    Если хотите указать, что предмет будет каждую неделю, то указывайте сразу в двух неделях (0151 - каждый понедельник первым уроком)
    - Каждая четная цифра - номер урока (от 1 до 9)
    '''
class sch_subj_create4:
    text = 'Ваш предмет создан!'
    buttons = [
        [
            schedule_settings_back_button,
            home_button
        ],
    ]

class sch_subj_edit1:
    text = 'Введите название предмета для изменения'
class sch_subj_edit2:
    text = 'Выберите то, что хотите изменить в предмете'
    buttons = [
        [
            ('📝 Название', 'sch_subj_edit_name'),
            ('👥 Группы', 'sch_subj_edit_groups'),
            ('📆 Расписание', 'sch_subj_edit_schedule'),
            ('🚪 Кабинет', 'sch_subj_edit_office'),
            ('👩‍🏫 Учитель', 'sch_subj_edit_teacher')
        ],
        [
            schedule_settings_back_button,
            home_button
        ]
    ]

class sch_subj_edit_name1:
    text = 'Введите новое название'
class sch_subj_edit_name2:
    text = 'Название изменено!'
    buttons = sch_subj_edit_markup

class sch_subj_edit_groups1:
    text = 'Введите список групп которые должны будут иметь данный предмет (на каждой строке - одна группа). Если вы хотите создать общий для всех участников класса предмет, то нажмите на кнопку'
    buttons = [
        [
            ('❌', 'sch_subj_edit_general')
        ]
    ]
class sch_subj_edit_groups2:
    text = 'Список групп изменен!'
    buttons = sch_subj_edit_markup

class sch_subj_edit_schedule1:
    text = \
    '''
    Введите расписание по следующему формату:
    - Строка, состоящяя из цифр
    - Каждая нечетная цифра - день в расписании (0, 1, 2, 3, 4 - дни недели в нечетной неделе; 5, 6, 7, 8, 9 - дни недели в четной неделе)
    Если хотите указать, что предмет будет каждую неделю, то указывайте сразу в двух неделях (0151 - каждый понедельник первым уроком)
    - Каждая четная цифра - номер урока (от 1 до 9)
    '''
class sch_subj_edit_schedule2:
    text = 'Расписание изменено!'
    buttons = sch_subj_edit_markup

class sch_subj_edit_office1:
    text = 'Введите новый номер кабинета'
class sch_subj_edit_office2:
    text = 'Номер кабинета изменен!'
    buttons = sch_subj_edit_markup

class sch_subj_edit_teacher1:
    text = 'Введите новое имя учителя'
class sch_subj_edit_teacher2:
    text = 'Имя учителя изменено!'
    buttons = sch_subj_edit_markup

class sch_bells:
    text = 'Расписание звонков:\n{sch_bells}'
    buttons = [
        [
            ('Изменить', 'sch_bells_edit'),
        ],
        [
            schedule_settings_back_button,
            home_button
        ]
    ]

class sch_bells_edit1:
    text = ('Введите новое расписание в следующем формате (каждая строка - отдельное расписание звонков):\n'
            '{час_начала} {минута_начала} {час_конца} {минута_конца} {номер урока (0, если прием пищи)} {название (если прием пищи)}\n'
            'пример: 8 0 8 45 1 - 1 урок 8:00-8:45')
class sch_bells_edit2:
    text = 'Расписание звонков обновлено!'
    buttons = [
        [
            schedule_settings_back_button,
            home_button
        ],
    ]
