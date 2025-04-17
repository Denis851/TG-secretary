from aiogram.fsm.state import State, StatesGroup

class AddTask(StatesGroup):
    waiting_for_task_text = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()
