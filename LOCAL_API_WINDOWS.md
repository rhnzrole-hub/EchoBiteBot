# 2 GB kiruvchi fayllar — Windows, Docker’siz

Bu versiya **2,000,000,000 baytgacha (2 GB)** faylni Local Bot API orqali qabul qiladi. Oddiy `api.telegram.org` rejimi 20 MB bilan qoladi. `.env` ga raqam yozishning o‘zi Telegram cheklovini olib tashlamaydi.

## Kerak bo‘ladiganlar

Sizdagi Python 3.11 va FFmpeg/ffprobe yetarli. Qo‘shimcha **rasmiy Telegram Bot API serveri** o‘rnatiladi. U alohida dastur, ZIP ichida tayyor `.exe` yo‘q. Docker talab qilinmaydi.

### 1. Eski botni to‘xtating va loyihani yangilang

- Bot terminalida Ctrl+C bosing.
- `.env` va `data` papkasini saqlang; `data` zaxirasini oling.
- ZIP’dagi `echobite` papkasini eskisi o‘rniga qo‘ying.
- API serverini o‘rnatish davomida ishlayotgan cloud botni qayta yoqish mumkin; cloud’dan chiqish bosqichiga kelganda yana to‘xtating.

### 2. Rasmiy serverni Windows uchun yig‘ing

Rasmiy ko‘rsatmalar generatorini oching:

https://tdlib.github.io/telegram-bot-api/build.html

**Windows → PowerShell → 64-bit → Release** variantlarini tanlang. Sahifa ko‘rsatgan C++ qurish vositalari, CMake va Git’ni o‘rnating, so‘ng aynan o‘sha sahifadagi build buyruqlarini bajaring. Bu Python paketini `pip install` qilish emas: C++ server dasturi yig‘iladi. Birinchi qurish vaqt va disk joyi talab qiladi.

Hosil bo‘lgan `telegram-bot-api.exe` ning to‘liq manzilini toping. Yonidagi DLL fayllarni ham o‘z papkasida saqlang. Misol manzil: `C:/telegram-bot-api/bin/telegram-bot-api.exe`; sizda boshqacha bo‘lishi mumkin.

WSL’ni tanlasangiz, generatorning **Linux** ko‘rsatmasidan foydalaning va bot, FFmpeg, API serverning barchasini WSL ichida ishlating. Ushbu versiyada Windows bot + WSL server o‘rtasida fayl manzillarini avtomatik tarjima qilish yo‘q.

### 3. Telegram ilova ma’lumotlarini oling

https://my.telegram.org → **API development tools** orqali o‘zingizning `api_id` va `api_hash` qiymatlaringizni oling.

Bular BotFather bergan bot tokenidan boshqa qiymatlar. `.env` ichida saqlanadi. Bot admini avvalgidek `ADMIN_ID` orqali aniqlanadi.

### 4. VS Code’da `.env` ni yangilang

Avvalgi `BOT_TOKEN`, `ADMIN_ID`, `DATA_DIR` ni saqlab, quyidagilarni qo‘shing:

```ini
BOT_API_MODE=local
BOT_API_URL=http://127.0.0.1:8081
LOCAL_FILES_DIR=C:/EchoBiteBot/telegram-api-data
TELEGRAM_BOT_API_EXE=C:/telegram-bot-api/bin/telegram-bot-api.exe
TELEGRAM_API_ID=OZINGIZNING_RAQAMLI_API_ID
TELEGRAM_API_HASH=OZINGIZNING_API_HASH
DOWNLOAD_TIMEOUT_SECONDS=3600
FFMPEG_TIMEOUT_SECONDS=1800
```

`LOCAL_FILES_DIR` — API serverining yuklangan fayllar va sessiya uchun alohida papkasi. Keng disk joyi bo‘lgan joyni tanlang; ishga tushiruvchi uni yaratadi. Bu SQLite katalog saqlanadigan `data` papkasi emas. Server keshini bot ishlayotgan paytda o‘chirmang. Bu loyiha server keshini avtomatik tozalamaydi.

`TELEGRAM_BOT_API_EXE` ni haqiqiy `.exe` manziliga almashtiring. To‘liq namuna `.env.local.example` ichida, lekin uni ko‘r-ko‘rona mavjud `.env` ustiga yozmang.

### 5. Cloud’dan local rejimga bir marta o‘ting

Eski bot to‘xtagan va local server tayyor bo‘lgach, loyiha papkasidagi PowerShell’da:

```powershell
python -m echobite.local_server --logout-cloud
```

Bu buyruq rasmiy cloud API’ga `logOut` yuboradi. Har ishga tushirishda takrorlamang. Telegram qoidasi bo‘yicha undan keyin cloud API’ga qaytish uchun kamida 10 daqiqa kutish kerak; local serverni esa darhol boshlash mumkin.

### 6. Ikki terminalda ishga tushiring

Birinchi terminal, loyiha papkasida:

```powershell
python -m echobite.local_server
```

U serverni `--local` bilan faqat `127.0.0.1:8081` da ishga tushiradi. `.env` qiymatlari child process muhitiga beriladi; API hash buyruq argumentiga yozilmaydi. Terminal ochiq qolsin.

Ikkinchi terminal, xuddi shu loyiha papkasida:

```powershell
python -m echobite
```

Log’da **input limit: 2 GB** chiqishi kerak. Botda `/add` xabari ham **2 GB** ko‘rsatadi. Endi avval 20 MB dan kattaroq faylda, keyin kerakli hajmda sinang. Noutbuk uxlamasin, ikkala dastur ham ishlab tursin.

## Katta fayllar bilan ishlash

- Admin tekshiruvi o‘zgarmagan: audio/voice/hujjat faqat egasidan qabul qilinadi.
- Local server faylni diskka yuklaydi; bot shu faylni nusxalamasdan FFmpeg’ga uzatadi. 2 GB fayl `read_bytes()` orqali RAM’ga yuklanmaydi.
- Kutiladigan maksimal yuklab olish vaqti 3600 soniya, FFmpeg ishlov berishi 1800 soniya. Zaruratda yuqoridagi qiymatlarni oshiring. Yuklash yoki kodlash ketayotganida adminning keyingi buyruqlari navbatda turadi; inline so‘rovlar alohida ishlaydi.
- Eski 1 soatlik **kirish davomiyligi** cheklovi olib tashlangan. FFmpeg qo‘llaydigan va davomiyligi aniqlanadigan audio kerak.
- 2 GB — **kiruvchi fayl chegarasi**. Yakuniy inline voice uchun ushbu loyiha **49 MB chiqish chegarasini** saqlaydi. Juda uzun audioni butunlay yuborish o‘rniga kerakli mem qismini kesing. Chiqish sig‘masa yarimta voice katalogga saqlanmaydi.
- Katta faylning oxiridan parcha olish sekinroq bo‘lishi mumkin: aniqlik uchun dekodlash va `atrim` qo‘llanadi, `-c copy` yo‘q.
- `/delete` va `/clear` katalog yozuvlarini o‘chiradi, Telegram/API serverining keshini yoki oldin yuborilgan xabarlarni o‘chirmaydi.
- Oldingi MP3 yozuvlarni migratsiya qilish ham tanlangan API rejimidan foydalanadi.

## Xatolar

- **Connection / API error 0:** birinchi terminaldagi server ishlayaptimi, port 8081 band emasmi tekshiring.
- **Local server --local bilan ishga tushirilmagan:** serverni yuqoridagi launcher bilan ishga tushiring.
- **Fayl LOCAL_FILES_DIR tashqarisida:** server ishlatayotgan `--dir` va bot `.env` papkasi mos emas. Ikkalasini bir xil `.env` bilan qayta ishga tushiring.
- **Fayl ko‘rinmayapti:** bot va API server bir operatsion tizim hamda bir disk manzillarini ko‘rishi kerak. Windows/WSL aralashtirmang.
- **20 MB chiqmoqda:** eski `.env` da cloud rejimi qolgan yoki eski bot nusxasi ishlayapti. Rejimni o‘zgartirgach botni qayta boshlang.
- **401 / 409:** token yoki parallel ishlayotgan bot jarayonlarini tekshiring.

Serverga ko‘chirganda ham local API va botni bir xostda, bir xil fayl tizimini ko‘radigan qilib joylashtiring. Hozirgi `compose.yaml` cloud rejimi uchun qolgan; local rejimni shu compose bilan avtomatik ishga tushirish ko‘zda tutilmagan.

Rasmiy manbalar:
- https://core.telegram.org/bots/api#using-a-local-bot-api-server
- https://github.com/tdlib/telegram-bot-api
- https://tdlib.github.io/telegram-bot-api/build.html
