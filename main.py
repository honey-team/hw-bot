import asyncio
import logging
import sys
from os import getenv
from typing import Any, Optional

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Chat
from aiogram.exceptions import TelegramBadRequest

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

async def format_text(txt: str, message: Optional[Message | CallbackQuery] = None, message_chat: Optional[Chat] = None) -> str:
    memb = await get_member(message.from_user.id)
    if memb:
        name = memb['name']
        cl_name = (await get_class(memb['class_id']))['name']
        gr_name = ', '.join([(await get_group(memb['class_id'], i))['name'] for i in get_groups_from_dict(memb) if i])
    else:
        name = message.from_user.full_name if message else 'аноним'
        cl_name = 'ошибка'
        gr_name = ''
    groups_text = ''
    members_text = ''
    members_count = 0
    groups_list = []
    
    if memb:
        for gr in (await get_all_groups(memb['class_id'], general=False)):
            groups_text += html.bold(f'{gr['name']}:\n')
            groups_list.append(gr['name'])
            for mb in (await get_all_members(class_id=memb['class_id'])):
                if gr['group_id'] in get_groups_from_dict(mb):
                    groups_text += f'{mb['name']}' + html.code(f' ({mb['user_id']})\n')
            groups_text += '\n'
        for mb in (await get_all_members(class_id=memb['class_id'])):
            members_count += 1
            members_text += f'{mb['name']}' + html.code(f' ({mb['user_id']})\n')
    
    general_info = {
        'user_name': name,
        'user_id': message.from_user.id if message else 'ошибка',
        'chat_id': message_chat.id if message_chat else 'ошибка',
        'hw_completed': '0',
        'hw_all': '0',
        'current_class': cl_name,
        'current_group': gr_name,
        'cl_members_text': members_text,
        'cl_groups_members_text': groups_text,
        'cl_members_num': members_count,
        'cl_groups_list': ', '.join(groups_list)
    }
    
    for k, v in general_info.items():
        txt = txt.replace('{' + k + '}', str(v))    
    return txt

# Main page
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if await get_member(message.from_user.id):
        await message.answer(await format_text(home.text, message, message.chat), reply_markup=generate_markup(home))
    else:
        await message.answer(await format_text(welcome.text, message, message.chat), reply_markup=generate_markup(welcome))

waiting_for_class_name = []
waiting_for_name_of_class_creator = []
create_class_names = {}

waiting_for_member_id = []
waiting_for_name = []
add_member_ids = {}


# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    async def __edit(dcls: TextAndButtonsDataclass):
        await callback_query.message.edit_text(await format_text(dcls.text, callback_query, callback_query.message.chat), reply_markup=generate_markup(dcls))

    match callback_query.data:
        case 'home':
            if await get_member(callback_query.from_user.id):
                await __edit(home)
            else:
                await __edit(welcome)
        case 'hw':
            await __edit(hw)
        case 'schedule':
            await __edit(schedule)
        case 'wc_create_class':
            await __edit(wc_create_class1)
            waiting_for_class_name.append(callback_query.from_user.id)
        case 'wc_join_class':
            await __edit(wc_join_class)
        case 'cl_settings':
            await __edit(cl_settings)
        case 'cl_members':
            await __edit(cl_members)
        case 'cl_add_member':
            await __edit(cl_add_member1)
            waiting_for_member_id.append(callback_query.from_user.id)
        case 'cl_groups':
            await __edit(cl_groups)
    

@dp.message()
async def echo_handler(message: Message) -> None:
    async def __answer(dcls: TextAndButtonsDataclass):
        await message.answer(await format_text(dcls.text, message, message.chat), reply_markup=generate_markup(dcls))
    
    user_id = message.from_user.id

    # Create class
    if user_id in waiting_for_class_name:
        create_class_names[user_id] = message.text
        await __answer(wc_create_class2)
        waiting_for_class_name.remove(user_id)
        waiting_for_name_of_class_creator.append(user_id)
    elif user_id in waiting_for_name_of_class_creator:
        await create_class(create_class_names[user_id], user_id, message.text)
        await __answer(wc_create_class3)
        waiting_for_name_of_class_creator.remove(user_id)
    #

    # Add member
    elif user_id in waiting_for_member_id:
        try:
            _id = int(message.text)
        except:
            await message.answer('Пожалуйста, пишите айди участника без лишних символов, кроме цифр.\n' + cl_add_member1.text)
            return
        add_member_ids[user_id] = _id
        await __answer(cl_add_member2)
        waiting_for_member_id.remove(user_id)
        waiting_for_name.append(user_id)
    elif user_id in waiting_for_name:
        memb = await get_member(user_id)
        await create_member(add_member_ids[user_id], memb['class_id'], message.text)
        await __answer(cl_add_member3)
        waiting_for_name.remove(user_id)
    #

async def main() -> None:
    await init_all()
    print('Initilizated database!')
    
    print('Bot is online')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
