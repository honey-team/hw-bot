import asyncio
from os import getenv
from re import U
from typing import Any, Optional

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton
)

from config import *
from db import *

TOKEN = getenv("BOT_TOKEN")
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def generate_markup(dataclass: TextAndButtonsDataclass) -> InlineKeyboardMarkup:
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

async def format_text(txt: str, message: Optional[Message | CallbackQuery] = None, ctx_g: Optional[str] = None) -> str:
    memb = x[0] if (x := await get_members(message.from_user.id)) else None
    cl = await get_class(memb['class_id']) if memb else None
    if memb:
        user_name = memb['name']
        cl_name = cl['name']
        # gr_name = ', '.join([(await get_group(memb['class_id'], i))['name'] for i in get_groups_from_dict(memb) if i])
        gr_name = ', '.join([i['name'] for i in (await get_groups_by_ids(memb['groups_ids']))])
    else:
        user_name = message.from_user.full_name if message else 'аноним'
        cl_name = 'ошибка'
        gr_name = ''
    groups_text = ''
    members_text = ''
    members_count = 0
    groups_list = []
    
    if memb:
        # for gr in (await get_all_groups(memb['class_id'], general=False)):
        for gr in (await get_groups_by_ids(cl['groups_ids'])):
            if (x := gr.get('name')):
                groups_text += html.bold(f'{x}:\n')
                groups_list.append(x)
            # for mb in (await get_all_members(class_id=memb['class_id'])):
            for mb in (await get_members(class_id=cl['id'])):
                if gr['id'] in mb['groups_ids']:
                    groups_text += mb['name'] + html.code(f' ({mb['id']})\n')
            groups_text += '\n'
        for mb in (await get_members(class_id=cl['id'])):
            members_count += 1
            members_text += mb['name'] + html.code(f' ({mb['id']})\n')
    
    general_info = {
        'user_name': user_name,
        'user_id': message.from_user.id if message else 'ошибка',
        'hw_completed': '0',
        'hw_all': '0',
        'current_class': cl_name,
        'current_group': gr_name,
        'cl_members_text': members_text,
        'cl_groups_members_text': groups_text,
        'cl_members_num': members_count,
        'cl_groups_list': ', '.join(groups_list) if groups_list else 'нет',
        'ctx.g': ctx_g or 'ошибка'
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


# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    async def __edit(dcls: TextAndButtonsDataclass):
        await callback_query.message.edit_text(await format_text(dcls.text, callback_query), reply_markup=generate_markup(dcls))

    user_id = callback_query.from_user.id
    match callback_query.data:
        case 'home':
            if await get_members(user_id):
                await __edit(home)
            else:
                await __edit(welcome)
        case 'hw':
            await __edit(hw)
        case 'schedule':
            await __edit(schedule)
        case 'wc_create_class':
            await __edit(wc_create_class1)
            w_wc_cc_class_name.append(user_id)
        case 'wc_join_class':
            await __edit(wc_join_class)
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
            ]))
            w_cl_ge_name.append(user_id)
        case 'cl_groups_edit_name':
            await __edit(cl_groups_edit_name1)
            w_cl_ge_n_name.append(user_id)

@dp.message()
async def echo_handler(message: Message) -> None:
    
    async def __answer(dcls: TextAndButtonsDataclass, **additional_data):
        await message.answer(await format_text(dcls.text, message, **additional_data), reply_markup=generate_markup(dcls))
    
    user_id = message.from_user.id
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
        except:
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
        members_ids = [(await get_members(class_id=memb['class_id'], name=i))[0]['id'] for i in members]
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
        m = await message.answer('...', reply_markup=ReplyKeyboardRemove())
        await m.delete()
        await __answer(cl_groups_edit2, ctx_g=message.text)
        w_cl_ge_name.remove(user_id)
    
    elif user_id in w_cl_ge_n_name:
        await edit_group(cl_ge_id[user_id], message.text)
        await __answer(cl_groups_edit_name2, ctx_g=message.text)
    #

async def main() -> None:
    await init_all()
    print('Initilizated database!')
    
    print('Bot is online')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
