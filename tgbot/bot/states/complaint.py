from aiogram.fsm.state import State, StatesGroup


class ComplaintStates(StatesGroup):
    language = State()
    anonymity = State()
    full_name = State()
    phone_number = State()
    region = State()
    district = State()
    mahalla = State()
    target_full_name = State()
    target_position = State()
    target_organization = State()
    complaint_text = State()
    media_files = State()
    confirmation = State()


class AdminStates(StatesGroup):
    broadcast_text = State()
