from aiogram.fsm.state import State, StatesGroup

class ScheduleStates(StatesGroup):
    editing = State()

class ScheduleEdit(StatesGroup):
    waiting_for_new_text = State()
    waiting_for_new_time = State()
    waiting_for_edit_choice = State()
    waiting_for_new_entry = State()  # Для добавления нового пункта расписания