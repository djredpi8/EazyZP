from aiogram.fsm.state import State, StatesGroup


class PayrollStates(StatesGroup):
    salary = State()
    year = State()
    year_manual = State()
    month = State()
