from aiogram.fsm.state import State, StatesGroup

class BuyProduct(StatesGroup):
    enter_target_username = State()  # Stars/Premium yuborilishi kerak bo'lgan username
    upload_receipt = State()         # To'lov cheki rasmi
