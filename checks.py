

__all__ = (

)

from typing import Any

from aiogram.types import Message

from config import *
from db import get_members
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
