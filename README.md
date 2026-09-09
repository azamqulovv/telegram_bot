# Telegram Bot

Bu loyiha Telegram Stars, Premium va Gift buyurtmalarini qabul qiluvchi aiogram botidir.

## Xavfsizlik

GitHub'ga quyidagilar yuklanmaydi:

- `.env` - bot tokeni va maxfiy sozlamalar
- `bot_database.db` - foydalanuvchilar va buyurtmalar bazasi
- `admin_orders_log.csv` - buyurtmalar logi
- `__pycache__/` va Python cache fayllari

`.env.example` faqat namuna. Serverda undan nusxa olib `.env` yarating va haqiqiy qiymatlarni kiriting.

## O'rnatish

Python 3.10 yoki yangiroq versiya kerak.

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/VPS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` faylini to'ldiring:

- `BOT_TOKEN` - BotFather bergan yangi token
- `CHANNEL_ID` - asosiy majburiy kanal
- `CHECKS_CHANNEL_ID` - chek yuboriladigan kanal
- `ADMIN_ID` va `ADMIN_ID_2` - admin Telegram ID'lari
- `CARD_NUMBER` va `CARD_HOLDER` - to'lov ma'lumotlari

## Ishga tushirish

```bash
python main.py
```

Bot ishlashi uchun u asosiy kanal va chek kanalida admin bo'lishi kerak. Keyin admin panel orqali qo'shilgan kanallarda ham botga kerakli huquqlarni bering.

## GitHub'ga yuklash

Git va GitHub CLI ushbu kompyuterda topilmadi. Git o'rnatilgandan keyin loyiha papkasida:

```bash
git init
git add .
git commit -m "Initial secure bot project"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

`USERNAME` va `REPOSITORY` o'rniga GitHub username va repository nomini yozing.
