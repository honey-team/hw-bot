import asyncio
from os import getenv
from re import U
from typing import Any, Optional

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

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

async def format_text(txt: str, message: Optional[Message | CallbackQuery] = None, ctx_gc_grn: Optional[str] = None) -> str:
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
        'ctx.gc.grn': ctx_gc_grn or 'ошибка'
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

waiting_for_class_name = []
waiting_for_name_of_class_creator = []
create_class_names = {}

waiting_for_member_id = []
waiting_for_name = []
add_member_ids = {}

waiting_for_group_name = []
waiting_for_group_members = []
add_group_names = {}


# Homework
@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery) -> Any:
    async def __edit(dcls: TextAndButtonsDataclass):
        await callback_query.message.edit_text(await format_text(dcls.text, callback_query), reply_markup=generate_markup(dcls))

    match callback_query.data:
        case 'home':
            if await get_members(callback_query.from_user.id):
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
        case 'cl_groups_create':
            await __edit(cl_groups_create1)
            waiting_for_group_name.append(callback_query.from_user.id)

@dp.message()
async def echo_handler(message: Message) -> None:
    async def __answer(dcls: TextAndButtonsDataclass, **additional_data):
        await message.answer(await format_text(dcls.text, message, **additional_data), reply_markup=generate_markup(dcls))
    
    user_id = message.from_user.id

    # Create class
    if user_id in waiting_for_class_name:
        create_class_names[user_id] = message.text
        await __answer(wc_create_class2)
        waiting_for_class_name.remove(user_id)
        waiting_for_name_of_class_creator.append(user_id)
    elif user_id in waiting_for_name_of_class_creator:
        cl = await create_class(create_class_names[user_id])
        await create_member(user_id, cl['id'], message.text)
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
        memb = (await get_members(user_id))[0]
        await create_member(add_member_ids[user_id], memb['class_id'], message.text)
        await __answer(cl_add_member3)
        del add_member_ids[user_id]
        waiting_for_name.remove(user_id)
    #
    
    # Group create
    elif user_id in waiting_for_group_name:
        add_group_names[user_id] = message.text
        await __answer(cl_groups_create2)
        waiting_for_group_name.remove(user_id)
        waiting_for_group_members.append(user_id)
    elif user_id in waiting_for_group_members:
        memb = (await get_members(user_id))[0]
        members = message.text.splitlines()
        members_ids = [(await get_members(class_id=memb['class_id'], name=i))[0]['id'] for i in members]
        gr = await create_group(memb['class_id'], add_group_names[user_id])
        for i in members_ids:
            await assign_to_group(i, int(gr['id']))
        await __answer(cl_groups_create3, ctx_gc_grn=add_group_names[user_id])
        del add_group_names[user_id]
        waiting_for_group_members.remove(user_id)
    #

async def main() -> None:
    await init_all()
    print('Initilizated database!')
    
    print('Bot is online')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
