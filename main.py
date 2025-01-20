import asyncio
import logging
import os.path
import sys
from datetime import timedelta, datetime
from os import getenv
from random import choice
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BufferedInputFile,
    InputMediaDocument
)
from aiogram.exceptions import TelegramBadRequest
from ujson import dumps, loads

from config import *
from db import *
from db import get_hw_for_day, hw_mark_uncompleted
from db import get_lesson_or_break
from logger import logger

TOKEN = getenv("HW_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def generate_markup(dataclass: TextAndButtonsDataclass = None,
                    buttons: list[list[tuple[str, str]]] = None) -> Optional[InlineKeyboardMarkup]:
    try:
        if dataclass:
            buttons = dataclass.buttons
    except AttributeError:
        pass
    try:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=txt, callback_data=cdata)
                for txt, cdata in i
            ]
            for i in buttons
        ])
    except AttributeError:
        return None

async def format_text(txt: str, message: Message | CallbackQuery, ctx_g: Optional[str] = None) -> str:
    user_id = message.from_user.id
    member = x[0] if (x := await get_members(user_id)) else {}
    cl = await get_class(member['class_id']) if member else {}
    
    user_name = message.from_user.full_name if message else 'ошибка'
    cl_name = 'ошибка'
    gr_name = ''
    subjects_text = ''
    sch_bells = ''
    groups_text = ''
    members_text = ''
    members_count = 0
    groups_list = []
    
    if member:
        user_name = member['name']
        cl_name = cl['name']
        gr_name = ', '.join([i['name'] for i in (await get_groups_by_ids(member['groups_ids']))])
        for gr in (await get_groups_by_ids(cl['groups_ids'])):
            if gr and (x := gr.get('name')):
                groups_text += html.bold(f'{x}:\n')
                groups_list.append(x)
            for mb in (await get_members(class_id=cl['id'])):
                if gr['id'] in mb['groups_ids']:
                    groups_text += mb['name'] + html.code(f' ({mb['id']})\n')
            groups_text += '\n'
        for mb in (await get_members(class_id=cl['id'])):
            members_count += 1
            members_text += mb['name'] + html.code(f' ({mb['id']})\n')
        for i, subj in enumerate(await get_subjects(class_id=member['class_id'])):
            gr_names = [(await get_group(i))['name'] for i in subj['groups_ids']]
            gr_names_text = f' ({', '.join(gr_names)})' if gr_names else ''
            subjects_text += f'{i + 1}. {subj['name']}{gr_names_text}\n'
        for st, et, tp, n in ((await get_bells_schedule(member['class_id'])) or []):
            sch_bells += f'{st.strftime('%H:%M')}-{et.strftime('%H:%M')} '
            if tp == 0:
                sch_bells += n
            else:
                sch_bells += f'{tp} урок'
            sch_bells += '\n'

    schedule_text = ''
    hw_text = ''
    current_day = ''
    hw_completed = 0
    hw_all = 0
    les = current_lesson.get(user_id, {})
    hw = {}
    
    weekdays = [
        'понедельник', 'вторник', 'среда',
        'четверг', 'пятница', 'суббота',
        'воскресенье'
    ]
    months = [
        'января', 'февраля', 'марта',
        'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября',
        'октября', 'ноября', 'декабря'
    ]
    
    if current_date.get(user_id):
        d = current_date[user_id]
        current_day = f'{d.day} {months[d.month-1]} {d.year} ({weekdays[d.weekday()]})'
        
        h = []
        
        for i in holidays:
            for j in range(7):
                h.append(i + timedelta(days=j))
        
        if d in h or d.weekday() in [5, 6]:
            schedule_text = hw_text = 'Сегодня уроков нет (выходной)'
        elif member:
            sch = await get_schedule_for_day(member['class_id'], member['groups_ids'], d)
            hw_sch = await get_hw_for_day(member['class_id'], member['groups_ids'], d)
            hw = (await get_hw(subject_id=les.get('id', 0), d=d)) or {}

            bells = await get_bells_schedule(member['class_id'])

            def _get_bell(ln: int):
                for b in bells:
                    if b[2] == ln:
                        return b
                return [None, None, None, None]

            for lesson, subj in sch.items():
                sch2 = sch.copy()
                del sch2[0]
                if lesson != 0 and not any(list(sch2.values())[list(sch2.keys()).index(lesson):]):
                    break
                st, et, tp, n = _get_bell(lesson)
                if st and et:
                    schedule_text += html.code(f'{st.strftime('%H:%M')} - {et.strftime('%H:%M')} ')
                if lesson == 0:
                    if n:
                        schedule_text += f'{n} 🍽️'
                else:
                    schedule_text += f'{lesson}. '
                    hw_text += f'{lesson}. '
                    if subj:
                        schedule_text += html.bold(subj['name'])
                        hw_text += html.bold(subj.get('name', '❌'))
                        if x := subj.get('office'):
                            schedule_text += f' в {x}'
                    else:
                        schedule_text += '❌'
                        hw_text += '❌'
                    if hw_sch[lesson]:
                        hw_text += ': '
                        l = len(hw_sch[lesson].get('files', []))
                        tmp = hw_sch[lesson].get('text', '')
                        if tmp is None: tmp = ''
                        if l > 0:
                            if tmp:
                                tmp += f' +{l}📄'
                            else:
                                tmp += f'{l}📄'

                        hw_text += html.strikethrough(tmp)\
                                   if member['id'] in hw_sch[lesson].get('completed', [])\
                                   else tmp
                    hw_text += '\n'
                schedule_text += '\n'

    tommorrow = date.today() + timedelta(days=1)
    now_information = [None, None, None, {}, None]
    if member:
        hw_tommorrow = await get_hw_for_day(member['class_id'], member['groups_ids'], tommorrow)
        for _hw in hw_tommorrow.values():
            if _hw is not None:
                hw_all += 1
                if member['id'] in _hw.get('completed', []):
                    hw_completed += 1
    
        now_information = ((await get_lesson_or_break(datetime.now(), member['class_id'], member['groups_ids']))
                           or now_information)
    cl = current_lesson.get(user_id, {})

    hellos = ['Привет', 'Здравствуйте', 'Салют', 'Приветствую']
    n = datetime.now()
    _si = n.year, n.month, n.day
    if datetime(*_si, hour=18) < n < datetime(*_si, hour=22): hellos += ['Добрый вечер']
    elif n < datetime(*_si, hour=7): hellos += ['Доброй ночи', 'Спокойной ночи']
    elif n < datetime(*_si, hour=12): hellos += ['Доброе утро']
    else: hellos += ['Добрый день']

    general_info = {
        'home.hello': choice(hellos),
        'home.hw': home.if_holiday if tommorrow.weekday() in [5, 6] else home.if_not_holiday
                                                                    if hw_all > 0 else home.if_there_isnt_hw,
        'user_name': user_name,
        'user_id': message.from_user.id if message else 'ошибка',
        'hw_comp_text': '✅' * hw_completed + '❌' * (hw_all-hw_completed),
        'current_class': cl_name,
        'current_group': ' ' + gr_name if gr_name else '',
        'cl_members_text': members_text,
        'cl_groups_members_text': groups_text,
        'cl_members_num': members_count,
        'cl_groups_list': ', '.join(groups_list) if groups_list else 'нет',
        'current_day': current_day,
        'hw_text': hw_text or 'Сегодня уроков нет',
        'current_lesson': les.get('name', 'не найдено'),
        'hw_is_completed': ' ✅' if member.get('id') in hw.get('completed', []) else '',
        'hw': hw.get('text', 'Нет текста') or '',
        'schedule_text': schedule_text or 'Сегодня уроков нет',
        'subjects_text': subjects_text or 'Предметов нет',
        'sch_bells': sch_bells or 'Расписания звонков нет',
        'cles.name': cl.get('name') or 'ошибка',
        'cles.office': cl.get('office') or 'не указан',
        'cles.teacher': cl.get('teacher') or 'не указан',
        'now.bell': f'{now_information[1].strftime('%H:%M')}-{now_information[2].strftime('%H:%M')}'
                    if any(now_information) and now_information[1] and now_information[2] else '',
        'now.lesson_or_break': (now.is_break if now_information[0] else now.is_lesson.format(
            now_lesson=now_information[3].get('name', '') if now_information[3] else '',
            now_office=f' в {x}' if now_information[3] and (x := now_information[3].get('office')) else ''
        )) if now_information and any(now_information) else '',
        'now.minutes_to_end': (now_information[4].seconds+59) // 60 if any(now_information) else '',
        'now.time': datetime.now().strftime('%H:%M'),
        'now.info': (
            (now.is_break_info + now.is_lesson_info if now_information[3] else now.is_break_info)
            if now_information[0] else now.is_lesson_info)
            .replace('{now_office}', (x if (x := y['office']) else 'не записан') if (y := now_information[3]) else '')
            .replace('{now_teacher}', (x if (x := y['teacher']) else 'не записан') if (y := now_information[3]) else '')
            .replace('{now_next_lesson}', x['name'] if (x := now_information[3]) else 'нет'
        ) if any(now_information) else '',
        'ctx.g': ctx_g or 'ошибка',
    }
    
    for k, v in general_info.items():
        txt = txt.replace('{' + k + '}', str(v))    
    return txt

# Main page
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    logging.log(logging.INFO, f'user {message.from_user.id} sended {message.text!r}')
    if await get_members(message.from_user.id):
        h = []
        for i in holidays:
            for j in range(7):
                h.append(i + timedelta(days=j))
        d = date.today()
        if d in h or d.weekday() in [5, 6]:
            await message.answer(await format_text(home.text, message),
                                 reply_markup=generate_markup(buttons=home.no_classes_buttons))
        else:
            await message.answer(await format_text(home.text, message), reply_markup=generate_markup(home))
    else:
        await message.answer(await format_text(welcome.text, message), reply_markup=generate_markup(welcome))

w_wc_cc_class_name = []
w_wc_cc_creator_name = []
wc_cc_class_name = {}

w_cl_am_member_id = []
w_cl_am_name = []
cl_am_member_id = {}

w_cl_gc_name = []
w_cl_gc_members = []
cl_gc_name = {}

w_cl_ge_name = []
cl_ge_id = {}

w_cl_ge_n_name = []

w_cl_ge_m_members = []

w_cl_gd_name = []

w_sch_set_sc_name = []
w_sch_set_sc_groups = []
w_sch_set_sc_schedule = []
sch_set_sc_name = {}
sch_set_sc_groups_ids = {}

current_date: dict[int, date] = {}

w_sch_info_lesson = []
current_lesson: dict[int, dict[str, Any]] = {}

w_sch_set_se_name = []
w_sch_set_se_new_name = []
w_sch_set_se_groups = []
w_sch_set_se_schedule = []
w_sch_set_se_office = []
w_sch_set_se_teacher = []

sch_set_se_csubj = {}

w_sch_be_bells = []

w_hw_o_name = []

w_hw_oe = []
hw_oe_text = {}
hw_oe_files = {}

w_hw_c_name = []

w_set_conf_file = []

now_updating = []

# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    user_id = callback_query.from_user.id
    logging.log(logging.INFO, f'user {user_id} clicked {callback_query.data!r}')
    memb = x[0] if (x := await get_members(user_id)) else None
    async def __edit(dcls: TextAndButtonsDataclass, text: Optional[str] = None,
                     buttons: Optional[list[list[tuple[int, int]]]] = None, **additional):
        try:
            if text is None:
                text = dcls.text
        except AttributeError: pass
        try:
            if buttons is None:
                buttons = dcls.buttons
        except AttributeError: pass
        try:
            await callback_query.message.edit_text(await format_text(text, callback_query, **additional),
                                                   reply_markup=generate_markup(buttons=buttons))
        except TelegramBadRequest:
            await __answer(dcls, text=text, buttons=buttons)
            await callback_query.message.delete()

    async def __answer(dcls: TextAndButtonsDataclass, text = None,
                       buttons: Optional[list[list[tuple[int, int]]]] = None,**additional):
        try:
            if text is None:
                text = dcls.text
        except AttributeError: pass
        try:
            if buttons is None:
                buttons = dcls.buttons
        except AttributeError: pass
        try:
            await callback_query.message.answer(await format_text(text, callback_query, **additional),
                                                reply_markup=generate_markup(buttons=buttons))
        except TelegramBadRequest:
            pass

    def __check_new_day(d: date):
        if d.month <= 6:
            y = d.year - 1
        else:
            y = d.year
        if date(y, 9, 1) <= d < date(y + 1, 6, 1): return d
        if date(y, 9, 1) > d: return date(y, 9, 1)
        return date(y + 1, 6, 1) - timedelta(days=1)

    if callback_query.data != 'now' and user_id in now_updating: now_updating.remove(user_id)
    match callback_query.data:
        case 'wc_create_class':
            await __edit(wc_create_class1)
            w_wc_cc_class_name.append(user_id)
        case 'wc_join_class':
            await __edit(wc_join_class)
        case 'home':
            if await get_members(user_id):
                h = []
                for i in holidays:
                    for j in range(7):
                        h.append(i + timedelta(days=j))
                d = date.today()
                if d in h or d.weekday() in [5, 6]:
                    await __edit(home, buttons=home.no_classes_buttons)
                else:
                    await __edit(home)
            else:
                await __edit(welcome)
        case 'cl_settings':
            await __edit(cl_settings)
        case 'cl_members':
            await __edit(cl_members)
        case 'cl_add_member':
            await __edit(cl_add_member1)
            w_cl_am_member_id.append(user_id)
        case 'cl_add_member_return':
            await __edit(cl_members)
            w_cl_am_member_id.remove(user_id)
        case 'cl_groups':
            await __edit(cl_groups)
        case 'cl_groups_create':
            await __edit(cl_groups_create1)
            w_cl_gc_name.append(user_id)
        case 'cl_groups_edit':
            cl = await get_class((await get_members(user_id))[0]['class_id'])
            await callback_query.message.answer(await format_text(cl_groups_edit1.text, callback_query), reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text=i['name']) for i in (await get_groups_by_ids(cl['groups_ids'])) or []]
            ], one_time_keyboard=True))
            w_cl_ge_name.append(user_id)
        case 'cl_groups_edit_name':
            await __edit(cl_groups_edit_name1)
            w_cl_ge_n_name.append(user_id)
        case 'cl_groups_edit_members':
            gr = await get_group(cl_ge_id[user_id])
            await __edit(cl_groups_edit_members1, ctx_g=gr['name'])
            w_cl_ge_m_members.append(user_id)
        case 'cl_groups_delete':
            cl = await get_class((await get_members(user_id))[0]['class_id'])
            await callback_query.message.answer(await format_text(cl_groups_delete1.text, callback_query), reply_markup=ReplyKeyboardMarkup(keyboard=[
                [KeyboardButton(text=i['name']) for i in (await get_groups_by_ids(cl['groups_ids'])) or []]
            ], one_time_keyboard=True))
            w_cl_gd_name.append(user_id)
        case 'schedule':
            if current_date.get(user_id) is None:
                current_date[user_id] = date.today()
            await __edit(schedule)
        case 'schedule_left_week':
            current_date[user_id] = __check_new_day(current_date[user_id] - timedelta(days=7))
            await __edit(schedule)
        case 'schedule_left':
            current_date[user_id] = __check_new_day(current_date[user_id] - timedelta(days=1))
            await __edit(schedule)
        case 'schedule_today':
            current_date[user_id] = __check_new_day(date.today())
            await __edit(schedule)
        case 'schedule_info':
            await __edit(schedule_info1)
            await callback_query.message.answer(
                await format_text(schedule_info1.text, callback_query),
                reply_markup=ReplyKeyboardMarkup(keyboard=[[
                    KeyboardButton(text=i['name'])
                    for i in (
                        await get_schedule_for_day(memb['class_id'], memb['groups_ids'], current_date[user_id])
                    ).values() if i
                ]], one_time_keyboard=True))
            w_sch_info_lesson.append(user_id)
        case 'sch_info_edit':
            if current_lesson.get(user_id):
                sch_set_se_csubj[user_id] = current_lesson[user_id]
            await __edit(sch_subj_edit2)
        case 'schedule_right':
            current_date[user_id] = __check_new_day(current_date[user_id] + timedelta(days=1))
            await __edit(schedule)
        case 'schedule_right_week':
            current_date[user_id] = __check_new_day(current_date[user_id] + timedelta(days=7))
            await __edit(schedule)
        case 'schedule_settings':
            await __edit(schedule_settings)
        case 'sch_subj':
            await __edit(sch_subj)
        case 'sch_subj_create':
            await __edit(sch_subj_create1)
            w_sch_set_sc_name.append(user_id)
        case 'sch_subj_create_general':
            sch_set_sc_groups_ids[user_id] = []
            await __edit(sch_subj_create3)
            w_sch_set_sc_groups.remove(user_id)
            w_sch_set_sc_schedule.append(user_id)
        case 'sch_subj_edit':
            await callback_query.message.answer(
                await format_text(sch_subj_edit1.text, callback_query),
                reply_markup=ReplyKeyboardMarkup(keyboard=[
                    [KeyboardButton(text=i['name']) for i in (await get_subjects(class_id=memb['class_id']))]
                ], one_time_keyboard=True))
            w_sch_set_se_name.append(user_id)
        case 'sch_subj_edit_name':
            await __edit(sch_subj_edit_name1)
            w_sch_set_se_new_name.append(user_id)
        case 'sch_subj_edit_groups':
            await __edit(sch_subj_edit_groups1)
            w_sch_set_se_groups.append(user_id)
        case 'sch_subj_edit_schedule':
            await __edit(sch_subj_edit_schedule1)
            w_sch_set_se_schedule.append(user_id)
        case 'sch_subj_edit_office':
            await __edit(sch_subj_edit_office1)
            w_sch_set_se_office.append(user_id)
        case 'sch_subj_edit_teacher':
            await __edit(sch_subj_edit_teacher1)
            w_sch_set_se_teacher.append(user_id)
        case 'sch_subj_edit_general':
            await edit_subject(sch_set_se_csubj[user_id]['id'], groups_ids=[])
            await __edit(sch_subj_edit_groups2)
            w_sch_set_se_groups.remove(user_id)
        case 'sch_bells':
            await __edit(sch_bells)
        case 'sch_bells_edit':
            await __edit(sch_bells_edit1)
            w_sch_be_bells.append(user_id)
        case 'hw':
            if current_date.get(user_id) is None:
                current_date[user_id] = date.today() + timedelta(days=1)
            await __edit(hw)
        case 'hw_return':
            if current_date.get(user_id) is None:
                current_date[user_id] = date.today() + timedelta(days=1)
            await __answer(hw)
        case 'hw_left':
            current_date[user_id] =  __check_new_day(current_date[user_id] - timedelta(days=1))
            await __edit(hw)
        case 'hw_tommorrow':
            current_date[user_id] = __check_new_day(date.today() + timedelta(days=1))
            await __edit(hw)
        case 'hw_open':
            sch = await get_schedule_for_day(memb['class_id'], memb['groups_ids'], current_date[user_id])
            schn = []
            for i in sch.values():
                if i and i['name'] not in schn:
                    schn.append(i['name'])
            await callback_query.message.answer(await format_text(hw_open1.text, callback_query), reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=i) for i in schn]], one_time_keyboard=True))
            w_hw_o_name.append(user_id)
        case 'back_to_hw':
            w_hw_o_name.remove(user_id)
            await __edit(hw)
        case 'hw_open_edit':
            await __edit(hw_open_edit1)
            hw_oe_files[user_id] = []
            w_hw_oe.append(user_id)
        case 'hw_open_edit_end':
            _hw = await get_hw(subject_id=current_lesson[user_id]['id'], d=current_date[user_id])
            if _hw:
                await edit_hw(_hw['id'], text=hw_oe_text.get(user_id, None), files=hw_oe_files[user_id])
            else:
                await create_hw(current_lesson[user_id]['id'], hw_oe_text.get(user_id, None),
                                d=current_date[user_id], files=hw_oe_files[user_id])
            await __answer(hw_open_edit2)
            w_hw_oe.remove(user_id)
        case 'hw_return_open':
            _hw = await get_hw(subject_id=current_lesson[user_id]['id'], d=current_date[user_id])
            if memb['id'] in _hw.get('completed', []):
                await __edit(hw_open_btn_uncomplete)
            else:
                await __edit(hw_open2)
        case 'hw_open_complete':
            _hw = await get_hw(subject_id= current_lesson[user_id]['id'], d=current_date[user_id])

            if _hw is None:
                await __edit(hw_open_complete_none)
            else:
                if memb['id'] in _hw['completed']:
                    await hw_mark_uncompleted(memb['id'], _hw['id'])
                else:
                    await hw_mark_completed(memb['id'], _hw['id'])
                await __edit(hw_open_complete)
        case 'hw_complete':
            sch = (await get_hw_for_day(memb['class_id'], memb['groups_ids'], current_date[user_id])).values()
            schn = set()
            for i in sch:
                if i:
                    schn.add((await get_subjects(i['subject_id']))[0]['name'])
            await callback_query.message.answer(await format_text(hw_complete1.text, callback_query), reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=i) for i in list(schn)]], one_time_keyboard=True))
            w_hw_c_name.append(user_id)
        case 'hw_right':
            current_date[user_id] =  __check_new_day(current_date[user_id] + timedelta(days=1))
            await __edit(hw)
        case 'now':
            last_minute = datetime.now().minute - 1
            now_updating.append(user_id)
            while True:
                if user_id not in now_updating: break
                if datetime.now().minute > last_minute:
                    try:
                        if await get_bells_schedule(memb['class_id']):
                            now_information = await get_lesson_or_break(
                                              datetime.now(), memb['class_id'], memb['groups_ids'])
                            if now_information:
                                await __edit(now)
                            else:
                                await callback_query.message.edit_text(
                                    await format_text(now.text_lessons_ended, callback_query),
                                    reply_markup=generate_markup(now))
                        else:
                            await callback_query.message.edit_text(await format_text(now.text_fallback_bells,
                                                                   callback_query), reply_markup=generate_markup(now))
                    except TelegramBadRequest:
                        pass
                    last_minute = datetime.now().minute
                await asyncio.sleep(1)
        case 'import_export':
            await __edit(import_export)
        case 'import':
            await __edit(import1)
            w_set_conf_file.append(user_id)
        case 'import_cancel':
            w_set_conf_file.remove(user_id)
            await __edit(import_export)
        case 'export':
            data = await get_conf(memb['class_id'])
            exported = BufferedInputFile(bytes(dumps(data, ensure_ascii=False, indent=2), 'utf-8'),
                                          filename=f"{datetime.now().strftime('%d.%m.%Y %H %M')}.json")
            await callback_query.message.edit_media(
                InputMediaDocument(media=exported, caption=await format_text(export.text, callback_query)),
                reply_markup=generate_markup(export))


@dp.message(Command('hw', ignore_case=True))
async def hw_command(message: Message) -> None:
    logging.log(logging.INFO, f'user {message.from_user.id} sended {message.text!r}')
    if current_date.get(user_id := message.from_user.id) is None:
        current_date[user_id] = date.today() + timedelta(days=1)
    await message.answer(await format_text(hw.text, message), reply_markup=generate_markup(hw))


@dp.message(Command('sch', ignore_case=True))
async def sch_command(message: Message) -> None:
    logging.log(logging.INFO, f'user {message.from_user.id} sended {message.text!r}')
    if current_date.get(user_id := message.from_user.id) is None:
        current_date[user_id] = date.today()
    await message.answer(await format_text(schedule.text, message), reply_markup=generate_markup(schedule))


@dp.message(Command('settings', ignore_case=True))
async def settings_command(message: Message) -> None:
    logging.log(logging.INFO, f'user {message.from_user.id} sended {message.text!r}')
    await message.answer(await format_text(cl_settings.text, message), reply_markup=generate_markup(cl_settings))


@dp.message(Command('now', ignore_case=True))
async def now_command(message: Message) -> None:
    user_id = message.from_user.id
    logging.log(logging.INFO, f'user {user_id} sended {message.text!r}')
    memb = x[0] if (x := await get_members(user_id)) else None

    if memb:
        if await get_bells_schedule(memb['class_id']):
            now_information = await get_lesson_or_break(datetime.now(), memb['class_id'], memb['groups_ids'])
            if now_information:
                now_mes = await message.answer(await format_text(now.text, message), reply_markup=generate_markup(now))
            else:
                now_mes = await message.answer(await format_text(now.text_lessons_ended, message),
                                               reply_markup=generate_markup(now))
        else:
            now_mes = await message.answer(await format_text(now.text_fallback_bells, message),
                                           reply_markup=generate_markup(now))
        if user_id in now_updating:
            return
        last_minute = datetime.now().minute
        now_updating.append(user_id)
        while True:
            if message.from_user.id not in now_updating: break
            if datetime.now().minute > last_minute:
                try:
                    if await get_bells_schedule(memb['class_id']):
                        now_information = await get_lesson_or_break(datetime.now(), memb['class_id'], memb['groups_ids'])
                        if now_information:
                            await now_mes.edit_text(await format_text(now.text, message), reply_markup=generate_markup(now))
                        else:
                            await now_mes.edit_text(await format_text(now.text_lessons_ended, message),
                                                                   reply_markup=generate_markup(now))
                    else:
                        await now_mes.edit_text(await format_text(now.text_fallback_bells, message),
                                                               reply_markup=generate_markup(now))
                except TelegramBadRequest:
                    pass
                last_minute = datetime.now().minute
            await asyncio.sleep(1)


@dp.message()
async def user_answer_handler(message: Message) -> None:
    # Logging
    user_id = message.from_user.id
    logging.log(logging.INFO, f'user {user_id} sended {message.text!r}')
    async def __answer(dcls: TextAndButtonsDataclass, **additional_data):
        await message.answer(await format_text(dcls.text, message, **additional_data), reply_markup=generate_markup(dcls))

    async def check_name_for_lines_and_length() -> str | None:
        if len(message.text) > 10:
            await message.answer("Имя слишком длинное. Попробуйте выбрать имя меньше 10 символов.")
            return
        return message.text.replace('\n', '')

    memb = x[0] if (x := await get_members(user_id)) else None

    # Create class
    if user_id in w_wc_cc_class_name:
        if len(message.text) > 10:
            await message.answer("Ваше название класса слишком длинное."
                                 "Попробуйте выбрать название класса меньше 10 символов")
            return
        w_wc_cc_class_name.remove(user_id)
        _class_name = message.text.replace('\n', '')
        wc_cc_class_name[user_id] = _class_name
        await __answer(wc_create_class2)
        w_wc_cc_creator_name.append(user_id)
    elif user_id in w_wc_cc_creator_name:
        if (_name := await check_name_for_lines_and_length()) is None:
            return
        w_wc_cc_creator_name.remove(user_id)
        cl = await create_class(wc_cc_class_name[user_id])
        await create_member(user_id, cl['id'], _name)
        await __answer(wc_create_class3)
    #

    # Add member
    elif user_id in w_cl_am_member_id:
        try:
            _id = int(message.text)
        except ValueError:
            await message.answer('Пожалуйста, пишите айди участника без лишних символов, кроме цифр.\n' + cl_add_member1.text)
            return
        w_cl_am_member_id.remove(user_id)
        cl_am_member_id[user_id] = _id
        await __answer(cl_add_member2)
        w_cl_am_name.append(user_id)
    elif user_id in w_cl_am_name:
        if (_name := await check_name_for_lines_and_length()) is None:
            return
        w_cl_am_name.remove(user_id)
        await create_member(cl_am_member_id[user_id], memb['class_id'], _name)
        await __answer(cl_add_member3)
        del cl_am_member_id[user_id]
    #

    # Group create
    elif user_id in w_cl_gc_name:
        if (_name := await check_name_for_lines_and_length()) is None:
            return
        w_cl_gc_name.remove(user_id)
        cl_gc_name[user_id] = _name
        await __answer(cl_groups_create2)
        w_cl_gc_members.append(user_id)
    elif user_id in w_cl_gc_members:
        members = message.text.splitlines()
        members_ids = [
            x[0]['id']
            for i in members if (x := await get_members(class_id=memb['class_id'], name=i))
        ]
        gr = await create_group(memb['class_id'], cl_gc_name[user_id])
        for i in members_ids:
            await assign_to_group(i, int(gr['id']))
        await __answer(cl_groups_create3, ctx_g=cl_gc_name[user_id])
        del cl_gc_name[user_id]
        w_cl_gc_members.remove(user_id)
    #
    
    # Group edit
    elif user_id in w_cl_ge_name:
        if gr := await get_group(name=message.text):
            cl_ge_id[user_id] = gr['id']
            await __answer(cl_groups_edit2, ctx_g=message.text)
            w_cl_ge_name.remove(user_id)
        else:
            await message.answer('Не удалось найти группу с данным названием. Попробуйте еще раз.')
    
    elif user_id in w_cl_ge_n_name:
        if (_name := await check_name_for_lines_and_length()) is None:
            return
        w_cl_ge_n_name.remove(user_id)
        await edit_group(cl_ge_id[user_id], _name)
        await __answer(cl_groups_edit_name2, ctx_g=_name)

    elif user_id in w_cl_ge_m_members:
        members = message.text.splitlines()
        members_ids = [x[0]['id'] for i in members if (x := await get_members(class_id=memb['class_id'], name=i))]

        for i in (await get_members(class_id=memb['class_id'])):
            if i and i['id'] not in members_ids:
                await unassign_to_group(i['id'], cl_ge_id[user_id])
        for i in members_ids:
            await assign_to_group(i, cl_ge_id[user_id])
        
        gr = await get_group(cl_ge_id[user_id])
        await __answer(cl_groups_edit_members2, ctx_g=gr['name'])
        w_cl_ge_m_members.remove(user_id)
    #
    
    # Group delete
    elif user_id in w_cl_gd_name:
        gr_id = x['id'] if (x := await get_group(name=message.text)) else None
        if gr_id:
            await delete_group(gr_id, memb['class_id'])
            await __answer(cl_groups_delete2, ctx_g=message.text)
            w_cl_gd_name.remove(user_id)
        else:
            await message.answer(f'Не удалось найти группу с именем {html.bold(message.text)}')
    #
    
    # Schedule settings subjects create
    elif user_id in w_sch_set_sc_name:
        if (_name := await check_name_for_lines_and_length()) is None:
            return
        if (await get_subjects(name=_name, class_id=memb['class_id'])) or _name in sch_set_sc_name.values():
            await message.answer('Предмет с таким названием уже есть, выберите уникальное название.')
            return
        w_sch_set_sc_name.remove(user_id)
        sch_set_sc_name[user_id] = _name
        await __answer(sch_subj_create2)
        w_sch_set_sc_groups.append(user_id)
    elif user_id in w_sch_set_sc_groups:
        sch_set_sc_groups_ids[user_id] = [x['id'] for i in message.text.splitlines() if (x := await get_group(name=i))]
        await __answer(sch_subj_create3)
        w_sch_set_sc_groups.remove(user_id)
        w_sch_set_sc_schedule.append(user_id)
    elif user_id in w_sch_set_sc_schedule:
        # Check schedule:
        _schedule = message.text.replace(' ', '').replace('\n', '')
        if not (len(_schedule) % 2 == 0
                and len(_schedule) <= 9*5*4
                and _schedule.isdigit()
                and all([int(i) > 0 for i in _schedule[1::2]])
        ):
            await message.answer('Неправильный формат расписания. Попробуйте еще раз')
            return
        w_sch_set_sc_schedule.remove(user_id)
        await create_subject(memb['class_id'], sch_set_sc_groups_ids[user_id], sch_set_sc_name[user_id], message.text)
        await __answer(sch_subj_create4)
        del sch_set_sc_groups_ids[user_id]
        del sch_set_sc_name[user_id]
    #

    # Schedule settings subjects edit
    elif user_id in w_sch_set_se_name:
        sch_set_se_csubj[user_id] = x[0] if (x := await get_subjects(name=message.text)) else None

        if sch_set_se_csubj[user_id]:
            await __answer(sch_subj_edit2)
            w_sch_set_se_name.remove(user_id)
        else:
            await message.answer('Не найдено такого предмета с данным названием')

    elif user_id in w_sch_set_se_new_name:
        await edit_subject(sch_set_se_csubj[user_id]['id'], name=message.text)
        await __answer(sch_subj_edit_name2)
        w_sch_set_se_new_name.remove(user_id)
    elif user_id in w_sch_set_se_groups:
        await edit_subject(sch_set_se_csubj[user_id]['id'],
                           groups_ids=[(await get_group(name=i))['id'] for i in message.text.splitlines()])
        await __answer(sch_subj_edit_groups2)
        w_sch_set_se_groups.remove(user_id)
    elif user_id in w_sch_set_se_schedule:
        await edit_subject(sch_set_se_csubj[user_id]['id'], schedule=message.text)
        await __answer(sch_subj_edit_schedule2)
        w_sch_set_se_schedule.remove(user_id)
    elif user_id in w_sch_set_se_office:
        await edit_subject(sch_set_se_csubj[user_id]['id'], office=message.text)
        await __answer(sch_subj_edit_office2)
        w_sch_set_se_office.remove(user_id)
    elif user_id in w_sch_set_se_teacher:
        await edit_subject(sch_set_se_csubj[user_id]['id'], teacher=message.text)
        await __answer(sch_subj_edit_teacher2)
        w_sch_set_se_teacher.remove(user_id)
    #

    # Schedule info
    elif user_id in w_sch_info_lesson:
        current_lesson[user_id] = x[0] if (x := await get_subjects(class_id=memb['class_id'], name=message.text)) else None
        await __answer(schedule_info2)
    #

    # Bells edit
    elif user_id in w_sch_be_bells:
        await delete_bells_schedule(memb['class_id'])
        bells = [i.split(' ', 5) for i in message.text.splitlines()]

        for b in bells: # sh, sm, eh, em, tp, n
            for i in range(5):
                b[i] = int(b[i])
            st = (b[0], b[1])
            et = (b[2], b[3])
            if b[4] == 0:
                await create_bell(memb['class_id'], b[4], b[5], st, et)
            else:
                await create_bell(memb['class_id'], b[4], start_time=st, end_time=et)
        await __answer(sch_bells_edit2)
        w_sch_be_bells.remove(user_id)
    #

    # Hw open
    elif user_id in w_hw_o_name:
        subj = await get_subjects(name=message.text)

        if subj:
            current_lesson[user_id] = subj[0]
            _hw = await get_hw(subject_id=subj[0]['id'], d=current_date[user_id])

            if _hw and _hw.get('files', []):
                for f in _hw.get('files', []):
                    try:
                        await message.answer_document(f)
                    except TelegramBadRequest:
                        await message.answer_photo(f)

            if _hw:
                if memb['id'] in _hw['completed']:
                    await __answer(hw_open_btn_uncomplete)
                else:
                    await __answer(hw_open2)
            else:
                await __answer(hw_open_none)
            w_hw_o_name.remove(user_id)
        else:
            await message.answer(await format_text('Попробуйте еще раз\n' + hw_open1.text, message),
                                 reply_markup=ReplyKeyboardMarkup(
                                    keyboard=[[
                                        KeyboardButton(text=i['name'])
                                        for i in (await get_schedule_for_day(memb['class_id'], memb['groups_ids'],
                                                                             current_date[user_id])).values()
                                ]], one_time_keyboard=True))
    #

    # Hw open edit
    elif user_id in w_hw_oe:
        if message.text:
            hw_oe_text[user_id] = message.text
        elif message.caption:
            hw_oe_text[user_id] = message.caption
        if not hw_oe_files.get(user_id):
            hw_oe_files[user_id] = []

        if message.photo:
            hw_oe_files[user_id].append(message.photo[0].file_id)
        elif message.document:
            hw_oe_files[user_id].append(message.document.file_id)
    #

    # Hw complete
    elif user_id in w_hw_c_name:
        subj = await get_subjects(name=message.text)

        if subj:
            subj = subj[0]
            _hw = await get_hw(subject_id=subj['id'], d=current_date[user_id])

            if memb['id'] in _hw['completed']:
                await hw_mark_uncompleted(memb['id'], _hw['id'])
            else:
                await hw_mark_completed(memb['id'], _hw['id'])
            await __answer(hw_complete2)
            w_hw_c_name.remove(user_id)
        else:
            sch = (await get_hw_for_day(memb['class_id'], memb['groups_ids'], current_date[user_id])).values()
            schn = set()
            for i in sch:
                if i:
                    schn.add((await get_subjects(i['subject_id']))[0]['name'])
            await message.answer(await format_text('Попробуйте еще раз\n' + hw_complete1.text, message),
                                                reply_markup=ReplyKeyboardMarkup(
                                                keyboard=[[KeyboardButton(text=i) for i in list(schn)]],
                                                one_time_keyboard=True))
    #

    # Import
    elif user_id in w_set_conf_file:
        if message.document:
            bindata = await bot.download(message.document)
            if bindata and isinstance(x := loads(bindata.read()), dict):
                await set_conf(memb['class_id'], x)
                await __answer(import2)
            else:
                await __answer(import_not_finded_file)
        else:
            await __answer(import_not_finded_file)
    #

async def main() -> None:
    await init_all()
    logging.info('Bot is online')
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=logger)
    asyncio.run(main())
