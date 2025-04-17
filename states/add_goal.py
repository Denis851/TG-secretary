from aiogram.fsm.state import State, StatesGroup

class AddGoal(StatesGroup):
    waiting_for_goal_text = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()
