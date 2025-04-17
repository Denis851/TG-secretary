from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def generate_goals_keyboard(data):
    buttons = []
    for i, item in enumerate(data):
        status = "✅" if item.get("completed") else "🔲"
        icon = {
            "высокий": "🔥",
            "средний": "⚖️",
            "низкий": "💤"
        }.get(item.get("priority", "средний"), "⚖️")
        buttons.append([
            InlineKeyboardButton(text=f"{status} {icon} {item['text']}", callback_data=f"toggle_goal:{i}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"delete_goal:{i}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
