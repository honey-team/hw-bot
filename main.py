import asyncio
import logging
import sys
from os import getenv
from typing import Any, Optional
from typing_extensions import get_args

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import cl_add_member1, cl_add_member2, cl_add_member3, home, tommorrow, wc_create_class1, wc_create_class2, wc_create_class3, wc_join_class, welcome
from db import *

# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("BOT_TOKEN")

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()


def generate_markup(dataclass: type) -> InlineKeyboardMarkup:
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

async def format_text(txt: str, message: Optional[Message | CallbackQuery] = None) -> str:
    memb = await get_member(message.from_user.id)
    if memb and memb.get('class_id'):
        cl_name = (await get_class(memb['class_id']))['name']
    else:
        cl_name = 'ошибка'
    general_info = {
        'user_name': message.from_user.full_name if message else 'аноним',
        'user_id': message.from_user.id if message else 'ошибка',
        'hw_completed': '0',
        'hw_all': '0',
        'current_class': cl_name
    }
    return txt.format_map(general_info)

# Main page
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if await get_member(message.from_user.id):
        await message.answer(await format_text(home.text, message), reply_markup=generate_markup(home))
    else:
        await message.answer(await format_text(welcome.text, message), reply_markup=generate_markup(welcome))

waiting_for_class_name = []
waiting_for_group_name = []
waiting_for_member_id = []
waiting_for_add_member_group_name = []
created_classes_without_groups = {}
add_member_ids = {}

# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    async def __edit(dcls: type):
        await callback_query.message.edit_text(await format_text(dcls.text, callback_query), reply_markup=generate_markup(dcls))

    match callback_query.data:
        case 'home':
            if await get_member(callback_query.from_user.id):
                await __edit(home)
            else:
                await __edit(welcome)
        case 'tommorrow':
            await __edit(tommorrow)
        case 'wc_create_class':
            await __edit(wc_create_class1)
            waiting_for_class_name.append(callback_query.from_user.id)
        case 'wc_join_class':
            await __edit(wc_join_class)
        case 'cl_add_member':
            await __edit(cl_add_member1)
            waiting_for_member_id.append(callback_query.from_user.id)
    

@dp.message()
async def echo_handler(message: Message) -> None:
    if message.from_user.id in waiting_for_class_name:
        created_classes_without_groups[message.from_user.id] = await create_class(message.text)
        await message.answer(wc_create_class2.text)
        waiting_for_class_name.remove(message.from_user.id)
        waiting_for_group_name.append(message.from_user.id)

    elif message.from_user.id in waiting_for_group_name:
        await create_group(created_classes_without_groups[message.from_user.id]['class_id'], message.text, message.from_user.id)
        del created_classes_without_groups[message.from_user.id]
        await message.answer(wc_create_class3.text, reply_markup=generate_markup(wc_create_class3))
        waiting_for_group_name.remove(message.from_user.id)

    elif message.from_user.id in waiting_for_member_id:
        try:
            _id = int(message.text)
        except:
            await message.answer('Пожалуйста, пишите айди участника без лишних символов, кроме цифр.\n' + cl_add_member1.text)
            return
        add_member_ids[message.from_user.id] = _id
        await message.answer(cl_add_member2.text, reply_markup=generate_markup(cl_add_member2))
        waiting_for_member_id.remove(message.from_user.id)
        waiting_for_add_member_group_name.append(message.from_user.id)
    elif message.from_user.id in waiting_for_add_member_group_name:
        memb = await get_member(message.from_user.id)
        gr = await get_group(memb['class_id'], name=message.text)
        
        if gr:
            await create_member(add_member_ids[message.from_user.id], memb['class_id'], gr['group_id'])
            await message.answer(cl_add_member3.text, reply_markup=generate_markup(cl_add_member3))
            waiting_for_add_member_group_name.remove(message.from_user.id)
            del add_member_ids[message.from_user.id]
        else:
            await message.answer('Найти группу с данным именем не удалось, возможно, вы ошиблись с регистром или написали не ту букву. Попробуйте еще раз:\n')


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Initialize database
    await init_all()

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())