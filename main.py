import asyncio
from datetime import timedelta
from os import getenv
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.exceptions import TelegramBadRequest

from config import *
from db import *
from db import get_hw_for_day

TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def generate_markup(dataclass: TextAndButtonsDataclass) -> Optional[InlineKeyboardMarkup]:
    try:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=txt, callback_data=cdata)
                for txt, cdata in i
            ]
            for i in dataclass.buttons
        ])
    except AttributeError:
        return None

async def format_text(txt: str, message: Message | CallbackQuery, ctx_g: Optional[str] = None) -> str:
    user_id = message.from_user.id
    member = x[0] if (x := await get_members(user_id)) else None
    cl = await get_class(member['class_id']) if member else None
    
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
        else:
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
                        hw_text += ': ' + hw_sch[lesson].get('text', 'Прикреплены файлы')
                    elif subj:
                        hw_text += ': Нет домашнего задания'
                    hw_text += '\n'
                schedule_text += '\n'

    cl = current_lesson.get(user_id, {
        'name': None,
        'office': None,
        'teacher': None
    })
    general_info = {
        'user_name': user_name,
        'user_id': message.from_user.id if message else 'ошибка',
        'hw_completed': '0',
        'hw_all': '0',
        'current_class': cl_name,
        'current_group': ' ' + gr_name if gr_name else '',
        'cl_members_text': members_text,
        'cl_groups_members_text': groups_text,
        'cl_members_num': members_count,
        'cl_groups_list': ', '.join(groups_list) if groups_list else 'нет',
        'current_day': current_day,
        'hw_text': hw_text or 'Сегодня уроков нет',
        'current_lesson': les.get('name', 'не найдено'),
        'hw': hw.get('text', 'Нет текста'),
        'schedule_text': schedule_text or 'Сегодня уроков нет',
        'subjects_text': subjects_text or 'Предметов нет',
        'sch_bells': sch_bells or 'Расписания звонков нет',
        'cles.name': cl['name'] or 'ошибка',
        'cles.office': cl['office'] or 'не указан',
        'cles.teacher': cl['teacher'] or 'не указан',
        'ctx.g': ctx_g or 'ошибка',
    }
    
    for k, v in general_info.items():
        txt = txt.replace('{' + k + '}', str(v))    
    return txt

# Main page
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if await get_members(message.from_user.id):
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

w_hw_oe_text = []
w_hw_oe_files = []
hw_oe_text = {}
hw_oe_files = {}

# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    user_id = callback_query.from_user.id
    memb = x[0] if (x := await get_members(user_id)) else None
    async def __edit(dcls: TextAndButtonsDataclass, **additional):
        try:
            await callback_query.message.edit_text(await format_text(dcls.text, callback_query, **additional), reply_markup=generate_markup(dcls))
        except TelegramBadRequest:
            pass

    match callback_query.data:
        case 'wc_create_class':
            await __edit(wc_create_class1)
            w_wc_cc_class_name.append(user_id)
        case 'wc_join_class':
            await __edit(wc_join_class)
        case 'home':
            if await get_members(user_id):
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
            current_date[user_id] -= timedelta(days=7)
            await __edit(schedule)
        case 'schedule_left':
            current_date[user_id] -= timedelta(days=1)
            await __edit(schedule)
        case 'schedule_today':
            current_date[user_id] = date.today()
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
            sch_set_se_csubj[user_id] = current_lesson[user_id]
            await __edit(sch_subj_edit2)
        case 'schedule_right':
            current_date[user_id] += timedelta(days=1)
            await __edit(schedule)
        case 'schedule_right_week':
            current_date[user_id] += timedelta(days=7)
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
                current_date[user_id] = date.today()
            await __edit(hw)
        case 'hw_left':
            current_date[user_id] -= timedelta(days=1)
            await __edit(hw)
        case 'hw_tommorrow':
            current_date[user_id] = date.today() + timedelta(days=1)
            await __edit(hw)
        case 'hw_open':
            sch = await get_schedule_for_day(memb['class_id'], memb['groups_ids'], current_date[user_id])
            schn = list(set([i['name'] for i in sch.values() if i]))
            await callback_query.message.answer(await format_text(hw_open1.text, callback_query), reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=i) for i in schn]], one_time_keyboard=True))
            w_hw_o_name.append(user_id)
        case 'hw_open_edit':
            await __edit(hw_open_edit1)
            w_hw_oe_text.append(user_id)
        case 'back_to_hw':
            w_hw_o_name.remove(user_id)
            await __edit(hw)
        case 'hw_open_edit_skip_text':
            hw_oe_text[user_id] = None
            await __edit(hw_open_edit2)
            hw_oe_files[user_id] = []
            w_hw_oe_text.remove(user_id)
            w_hw_oe_files.append(user_id)
        case 'hw_open_edit_end_files':
            if hw_oe_text[user_id] is None:
                await callback_query.message.edit_text('Вы должны указать либо текст, либо файлы, либо и текст и файлы.'
                                                       'Ничего указать вы не можете')
            else:
                w_hw_oe_files.remove(user_id)
                _hw = await get_hw(subject_id=current_lesson[user_id]['id'], d=current_date[user_id])
                if _hw:
                    await edit_hw(_hw['id'], text=hw_oe_text[user_id] or None, filepaths=hw_oe_files[user_id])
                else:
                    await create_hw(current_lesson[user_id]['id'], hw_oe_text[user_id] or None,
                                    d=current_date[user_id], files=hw_oe_files[user_id])
                await __edit(hw_open_edit3)
        case 'hw_return_open':
            await __edit(hw_open2)
        case 'hw_complete':
            ...
        case 'hw_right':
            current_date[user_id] += timedelta(days=1)
            await __edit(hw)
            

@dp.message()
async def echo_handler(message: Message) -> None:
    user_id = message.from_user.id
    async def __answer(dcls: TextAndButtonsDataclass, **additional_data):
        await message.answer(await format_text(dcls.text, message, **additional_data), reply_markup=generate_markup(dcls))
    
    memb = x[0] if (x := await get_members(user_id)) else None

    # Create class
    if user_id in w_wc_cc_class_name:
        wc_cc_class_name[user_id] = message.text
        await __answer(wc_create_class2)
        w_wc_cc_class_name.remove(user_id)
        w_wc_cc_creator_name.append(user_id)
    elif user_id in w_wc_cc_creator_name:
        cl = await create_class(wc_cc_class_name[user_id])
        await create_member(user_id, cl['id'], message.text)
        await __answer(wc_create_class3)
        w_wc_cc_creator_name.remove(user_id)
    #

    # Add member
    elif user_id in w_cl_am_member_id:
        try:
            _id = int(message.text)
        except ValueError:
            await message.answer('Пожалуйста, пишите айди участника без лишних символов, кроме цифр.\n' + cl_add_member1.text)
            return
        cl_am_member_id[user_id] = _id
        await __answer(cl_add_member2)
        w_cl_am_member_id.remove(user_id)
        w_cl_am_name.append(user_id)
    elif user_id in w_cl_am_name:
        await create_member(cl_am_member_id[user_id], memb['class_id'], message.text)
        await __answer(cl_add_member3)
        del cl_am_member_id[user_id]
        w_cl_am_name.remove(user_id)
    #
    
    # Group create
    elif user_id in w_cl_gc_name:
        cl_gc_name[user_id] = message.text
        await __answer(cl_groups_create2)
        w_cl_gc_name.remove(user_id)
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
        cl_ge_id[user_id] = (await get_group(name=message.text))['id']
        await __answer(cl_groups_edit2, ctx_g=message.text)
        w_cl_ge_name.remove(user_id)
    
    elif user_id in w_cl_ge_n_name:
        await edit_group(cl_ge_id[user_id], message.text)
        await __answer(cl_groups_edit_name2, ctx_g=message.text)
        w_cl_ge_n_name.remove(user_id)
    
    elif user_id in w_cl_ge_m_members:
        members = message.text.splitlines()
        members_ids = [(await get_members(class_id=memb['class_id'], name=i))[0]['id'] for i in members]

        for i in (await get_members(class_id=memb['class_id'])):
            if i['id'] not in members_ids:
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
        sch_set_sc_name[user_id] = message.text
        await __answer(sch_subj_create2)
        w_sch_set_sc_name.remove(user_id)
        w_sch_set_sc_groups.append(user_id)
    elif user_id in w_sch_set_sc_groups:
        sch_set_sc_groups_ids[user_id] = [x['id'] for i in message.text.splitlines() if (x := await get_group(name=i))]
        await __answer(sch_subj_create3)
        w_sch_set_sc_groups.remove(user_id)
        w_sch_set_sc_schedule.append(user_id)
    elif user_id in w_sch_set_sc_schedule:
        await create_subject(memb['class_id'], sch_set_sc_groups_ids[user_id], sch_set_sc_name[user_id], message.text)
        await __answer(sch_subj_create4)
        w_sch_set_sc_schedule.remove(user_id)
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

            await __answer(hw_open2)
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
    elif user_id in w_hw_oe_text:
        hw_oe_text[user_id] = message.text
        await __answer(hw_open_edit2)
        hw_oe_files[user_id] = []
        w_hw_oe_text.remove(user_id)
        w_hw_oe_files.append(user_id)
    elif user_id in w_hw_oe_files:
        if message.photo:
            file_id = message.photo[0].file_id
        elif message.document:
            file_id = message.document.file_id
        print(file_id)
        hw_oe_files[user_id].append(file_id)
    #

async def main() -> None:
    await init_all()
    print('Bot is online')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
