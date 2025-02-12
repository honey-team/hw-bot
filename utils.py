from typing import Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TextDataclass, TextAndButtonsDataclass

def generate_markup(dataclass: TextDataclass | TextAndButtonsDataclass = None,
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
    except (AttributeError,  TypeError):
        return None
