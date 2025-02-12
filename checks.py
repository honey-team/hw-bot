__all__ = (
    'check_add_member_id',
    'check_member_name',
    'check_group_name',
)

from typing import Any

from aiogram.types import Message

from config import *
from db import get_members, get_group, get_class, get_groups_by_ids
from utils import generate_markup


async def check_add_member_id(message: Message, member: dict[str, Any]) -> int | None:
    try:
        _id = int(message.text)
    except ValueError:
        await message.answer(
            'Пожалуйста, пишите айди участника без лишних символов, кроме цифр.\n' + cl_add_member1.text,
            reply_markup=generate_markup(cl_add_member1)
        )
        return

    if await get_members(_id):
        await message.answer(
            'Данный пользователь уже состоит в классе, вы не можете его добавить. Попробуйте ещё раз.\n' +\
            cl_add_member1.text, reply_markup=generate_markup(cl_add_member1)
        )
        return

    # if
    if not (10**9 <= _id < 10**10):
        await message.answer('Айди находится в неправильном диапазоне значений.\n',
                             reply_markup=generate_markup(cl_add_member1))
        return

    return _id

async def check_member_name(message: Message, member: dict[str, Any]) -> str | None:
    if len(_name := message.text) > 10:
        await message.answer("Имя слишком длинное. Попробуйте написать меньше 11 символов.")
        return
    _name = _name.replace('\n', '')
    if await get_members(class_id=member['class_id'], name=_name):
        await message.answer('Участник класса с таким именем уже существует. Попробуйте другое имя.')
        return
    return _name

async def check_group_name(message: Message, member: dict[str, Any]) -> str | None:
    if len(_name := message.text) > 10:
        await message.answer("Название группы слишком длинное. Попробуйте написать меньше 11 символов.")
        return
    _name = _name.replace('\n', '')
    _class = await get_class(member['class_id'])
    _groups = await get_groups_by_ids(_class['groups_ids'])
    if _name in [i['name'] for i in _groups]:
        await message.answer('Группа с данным названием уже существует.')
        return

    return _name
