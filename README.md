# EchoBiteBot — v3 (Local API / 2 GB)

Telegram uchun inline mem audio bot. Python 3.10+ va FFmpeg ishlatiladi. Python paketlarini o‘rnatish talab qilinmaydi. Interfeys o‘zbek tilida.


## 2 GB fayllar

**2 GB kiruvchi fayl uchun Local Bot API kerak.** Windows va Docker’siz sozlash: [LOCAL_API_WINDOWS.md](LOCAL_API_WINDOWS.md). Yangi `.env.local.example` namunasi va `python -m echobite.local_server` ishga tushiruvchisi qo‘shildi. Rasmiy `telegram-bot-api.exe` alohida o‘rnatiladi; ZIP ichiga kiritilmagan.

Cloud rejimi eski `.env` bilan 20 MB bo‘lib qoladi. Local rejimdagi 2 GB — 2,000,000,000 bayt. Yakuniy voice chiqish chegarasi 49 MB; katta fayldan qisqa mem parcha tanlang.

## Oldingi versiyadan yangilash (Windows / VS Code, Docker shart emas)

1. Ishlayotgan bot terminalida **Ctrl+C** bosing.
2. Eski loyiha papkasidagi **`.env` va `data` papkasini saqlang**. Bot to‘xtagan paytda `data` papkasining zaxira nusxasini oling.
3. Yangi ZIP’dagi `echobite` papkasini eski loyiha ichidagi shu nomli papka bilan almashtiring. README, tests va boshqa loyiha fayllarini ham yangilash mumkin. ZIP’da haqiqiy `.env` yoki `data` yo‘q, faqat `.env.example` bor.
4. Eski `.env` va `data` joyida turgan loyiha ildizidan ishga tushiring:

```powershell
python -m echobite
```

Birinchi ishga tushishda eski MP3 katalog yozuvlari avtomatik OGG/Opus voice’ga o‘tkaziladi. Har bir o‘tkazilgan voice admin chatiga yuboriladi; nom va katalog ID saqlanadi. Bu tugagach polling boshlanadi. Keyingi restartda muvaffaqiyatli o‘tkazilganlar qayta yuborilmaydi.

Yuklab olish yoki konvertatsiya xatosida eski yozuv bazada saqlanadi, inline ro‘yxatda vaqtincha yashiriladi va adminga xabar beriladi. Restart qayta urinadi. Cloud rejimida 20 MB dan katta eski MP3 yuklanmasligi mumkin; local rejim 2 GB gacha yuklaydi. Cloud’da qolsangiz, uni `/delete` qilib, kichikroq asl faylni `/add` bilan qayta kiriting. Tugallanmagan migratsiya paytida to‘xtatilsa, navbatdagi restartda davom etadi; Telegram upload javobi yo‘qolsa admin chatida nusxa qolishi mumkin.

## /delete va /clear (faqat admin)

- `/delete` — dastlabki 20 ta audio **ID — nom** ro‘yxatini ko‘rsatadi. Nom yuborib qidiring yoki raqamli ID yuboring. So‘ng **Ha, o‘chirish** tugmasi bilan tasdiqlang.
- `/delete 12` — ID 12 audioni o‘chirish uchun tasdiq so‘raydi.
- `/delete kulgi` — nom bo‘yicha qidirishni darhol boshlaydi. Bir xil nomlarda ID orqali farqlang.
- `/clear` — katalogdagi jami sonni ko‘rsatib, barcha audioni o‘chirishni tasdiqlashni so‘raydi.
- **Bekor qilish** yoki `/cancel` — hech narsani o‘chirmaydi. Eskirgan va qayta bosilgan tugmalar ishlamaydi.

Har ikkala buyruq faqat adminning **shaxsiy chatida** bajariladi. Katalogdan o‘chirish avval boshqa chatlarga yuborilgan voice xabarlarini o‘chirmaydi. Telegram’da allaqachon ochilgan eski inline natijalar darhol bekor bo‘lishi kafolatlanmaydi; yangi so‘rov natijasidan o‘chirilgan audio chiqarib tashlanadi.

## Tayyor imkoniyatlar

- Barcha foydalanuvchilar uchun `/start`, `/help`, `/id`.
- Istalgan qo‘llab-quvvatlanadigan Telegram chatida `@EchoBiteBot so‘z` orqali audio qidirish va yuborish. Botni guruhga qo‘shish shart emas. Kanalga yozish yoki guruhda audio yuborish uchun foydalanuvchida tegishli huquq bo‘lishi kerak.
- Bo‘sh so‘rovda eng yangi audiolar; 20 tadan sahifalash. Nomdagi bir nechta so‘z bo‘yicha, registrga bog‘liq bo‘lmagan qidiruv. O‘zbek apostroflari normallashtiriladi.
- Audio qo‘shishga faqat `.env` dagi bitta raqamli `ADMIN_ID` vakolatli. Username orqali admin aniqlanmaydi. Har bir xabar va callback egasi tekshiriladi.
- `/add` faqat adminning bot bilan shaxsiy chatida ishlaydi.
- Audio, Telegram voice va audio fayl sifatida yuborilgan hujjatlar qabul qilinadi: MP3, M4A/AAC, OGG/Opus, WAV, FLAC va o‘rnatilgan FFmpeg dekoderlari qo‘llaydigan boshqa formatlar. Kengaytma yoki MIME o‘rniga faylning haqiqiy audio oqimi tekshiriladi.
- “Audioni kesish kerakmi?” → **Ha / Yo‘q** → vaqt (Ha bo‘lsa) → nom → katalogga saqlash.
- `/cancel` bilan bekor qilish, qayta `/add` bilan yangidan boshlash. Eski tugmalar ishlamaydi. Tugallanmagan ish 30 daqiqa harakatsizlikdan keyin o‘chiriladi.
- Tayyor katalog SQLite bazasida saqlanadi va qayta ishga tushganda qoladi. Audio Telegram’da `file_id` orqali qayta ishlatiladi.
- Audio qayta ishlash alohida ishchi oqimda; bu paytda inline qidiruv davom etadi.

## 1. Telegram sozlamalari

1. Telegram’dagi rasmiy **@BotFather** orqali `/newbot` yarating. `EchoBiteBot` username bo‘sh bo‘lsa tanlang; band bo‘lsa boshqa username kerak. Kod botning haqiqiy username’ini avtomatik oladi.
2. Tokenni `.env` fayliga yozing. Uni Git’ga qo‘shmang va boshqalarga yubormang.
3. **@BotFather → `/setinline` → botni tanlang → `Mem audio qidirish…`**. Bu majburiy qadam.
4. Geolokatsiya va inline feedback bu loyiha uchun kerak emas. Guruh privacy mode’ini o‘chirish shart emas.

## 2. Tez boshlash — Docker

ZIP’ni oching, terminalda `EchoBiteBot` papkasiga kiring. Docker Engine/Desktop va Compose o‘rnatilgan bo‘lsin.

Linux/macOS:

```sh
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

`.env` ichida `BOT_TOKEN` va o‘zingizning raqamli `ADMIN_ID` qiymatlaringizni kiriting. `@username` yoki telefon raqami yozilmaydi.

ID noma’lum bo‘lsa, tokenni kiritib, xavfsiz sozlash rejimini ishga tushiring:

```sh
docker compose run --rm bot python -m echobite.identity
```

Botga shaxsiy chatda `/id` yuboring. Javobdagi raqamni `.env` dagi `ADMIN_ID` ga yozing. Sozlash rejimini **Ctrl+C** bilan to‘xtating; u audio qo‘shishga ruxsat bermaydi. So‘ng:

```sh
docker compose up -d --build
docker compose logs -f
```

To‘xtatish:

```sh
docker compose down
```

`docker compose down -v` ishlatmang: `-v` katalog saqlanadigan volume’ni o‘chiradi. Docker doimiy volume ichida `library.sqlite3` saqlanadi. Zaxira olishda botni to‘xtatib, volume’ning barcha tarkibini ko‘chiring.

## 3. Docker’siz ishga tushirish

Python 3.10+ va `ffmpeg`, `ffprobe` PATH’da bo‘lsin.

Ubuntu/Debian:

```sh
sudo apt-get update
sudo apt-get install python3 ffmpeg
cp .env.example .env
```

Windows’da Python va FFmpeg’ni o‘rnating, FFmpeg `bin` papkasini PATH’ga qo‘shing. Tekshirish: `python --version`, `ffmpeg -version`, `ffprobe -version`.

`.env` ni to‘ldiring. ID olish kerak bo‘lsa:

```sh
python -m echobite.identity
```

Botga `/id` yuboring, Ctrl+C bilan to‘xtating va ID’ni `.env` ga kiriting.

```sh
python -m echobite
```

Linux tizimida `python` o‘rniga `python3` kerak bo‘lishi mumkin. Buyruqlarni loyiha ildizidan ishlating. Server/kompyuter va jarayon ishlayotgan paytdagina bot javob beradi. Bir token uchun faqat **bitta** bot nusxasini ishlating.

## 4. Audio qo‘shish

1. Bot bilan shaxsiy chatda `/add` yuboring.
2. Audio/voice yoki audio fayl yuboring.
3. Bot uzunlikni ko‘rsatadi va “Audioni kesish kerakmi?” deb so‘raydi.
4. **Ha** tanlansa, qoldiriladigan oraliqni yuboring:
   - `00:05.250 - 00:12.800` — 5.250-soniyadan 12.800-soniyagacha;
   - `5.25 - 12.8` — xuddi shu oraliq;
   - `10` — dastlabki 10 soniya;
   - `00:02:03.500 - 00:02:05.000` — HH:MM:SS formati ham qabul qilinadi.
5. Audio kesilgach nomini yuboring. **Yo‘q** tanlansa, darhol nom so‘raladi.
6. Bot tayyor voice’ni yuboradi, bazaga qo‘shadi va “Saqlandi!” deb xabar beradi.
7. Istalgan chatda `@EchoBiteBot nom` yozib audio tanlang. Agar username boshqacha bo‘lsa, o‘shani ishlating. Inline javoblarda cache_time=0 qo‘yilgan. Oldin ochilgan natijalar ro‘yxatini yangilash uchun so‘rovni qayta yozing.

Nom 1–100 belgidan iborat bir qator matn. Takroriy nomlar mumkin. Nom inline `InlineQueryResultCachedVoice.title` maydoniga beriladi; shu sababli inline ro‘yxat ham nom bilan chiqadi.

## 5. Kesish aniqligi

FFmpeg audio oqimini **dekodlaydi**, boshlang‘ich vaqt belgilarini nolga keltiradi, `atrim=start=...:end=...` va `asetpts` orqali namunalar asosida kesadi, keyin `libopus` yordamida OGG/Opus’ga **qayta kodlaydi**. `-c copy` yoki tezkor stream-copy ishlatilmaydi. Bu audio uchun sample-level aniqlik beradi; kirish namuna chastotasiga yaxlitlash tabiiy ravishda mumkin.

Chiqish: mono, 48 kHz, 64 kbit/s OGG/Opus. Telegram’ga `sendVoice` orqali yuklanadi, olingan voice `file_id` inline natijada `InlineQueryResultCachedVoice` bilan yuboriladi. Bu Telegram voice pufakchasi ko‘rinishida chiqadi. Audio nomi inline qidiruv natijasining `title` maydonida ko‘rsatiladi.

**Yo‘q** tanlansa ham butun audio OGG/Opus’ga aylantiriladi. Opus encoder delay/granule metadata mavjud; uni hisobga oladigan dekoderda namuna uzunligi saqlanadi. Telegram interfeysidagi yaxlit soniya ko‘rsatkichi kesish aniqligi emas.

## 6. Chegaralar va nosozliklar

- Cloud API’da kirish **20,000,000 baytgacha**, Local API’da **2,000,000,000 baytgacha**. Local sozlash uchun LOCAL_API_WINDOWS.md ni o‘qing.
- Barcha mavjud formatlarni mutlaq kafolatlash mumkin emas: fayl FFmpeg build’i qo‘llaydigan audio bo‘lishi kerak. DRM, buzilgan fayl va audio oqimisiz hujjat rad etiladi.
- Kirish audiosiga 1 soatlik limit yo‘q. FFmpeg timeout standart **1800 soniya**, chiqish maksimum **49 MB**. Katta audiodan qisqa mem parchasini tanlang. Sig‘magan chiqish kesilgan holda yashirincha saqlanmaydi.
- Qidiruv uchun SQLite va Telegram `file_id` saqlanadi. Asl fayllar yakunlanganda o‘chiriladi; mustaqil zaxira kerak bo‘lsa asl audio nusxalarini o‘zingiz saqlang. Boshqa bot tokeniga o‘tganda `file_id` ishlamasligi mumkin — qayta yuklash kerak.
- Restart bo‘lsa tugallanmagan `/add` bekor bo‘ladi. Avval saqlangan katalog qoladi. Yuqori yuklama uchun bu bir nusxali MVP; tarqatilgan navbat yoki replikatsiya yo‘q.
- Telegram’ga yuborishda tarmoq uzilsa, `/cancel` va `/add` bilan qayta boshlash mumkin. Javobi yo‘qolgan upload qayta urinishda admin chatida takroriy audio qoldirishi mumkin; u muvaffaqiyatli saqlanmaguncha inline katalogga kirmaydi.
- Bot 409 xato bilan to‘xtasa, shu token bilan boshqa jarayonni to‘xtating. Faol webhook aniqlansa bot uni yashirincha o‘chirmaydi. Polling’ga o‘tishni istasangiz, `.env` to‘ldirilgan loyiha papkasida quyidagini bir marta bajaring:

```sh
python -c "from echobite.__main__ import load_env; from echobite.api import API; import os; load_env(); API(os.environ['BOT_TOKEN']).call('deleteWebhook', {'drop_pending_updates': False})"
```

- Audio tahrirlash, teglar, ko‘p admin va boshqaruv paneli hozircha kiritilmagan.

## 7. Tekshiruv

Loyiha ildizida:

```sh
python -m unittest discover -s tests -v
```

Testlar haqiqiy FFmpeg’da MP3/M4A/OGG-Opus/FLAC fayllarini kesadi va dekodlangan natijaning sample sonini tekshiradi. Shuningdek admin huquqi, eskirgan tugmalar, noto‘g‘ri vaqtlar, `/cancel`, muddat tugashi, xatodan keyingi qayta urinish, qidiruv va sahifalash tekshiriladi. Testlar Telegram tarmog‘i o‘rniga soxta API javoblarini ishlatadi.

Real Telegram bilan yakuniy tekshirish:

1. Egasi sifatida `/start`, `/add` → voice → Ha → vaqt → nom.
2. Yana `/add` → M4A hujjat → Yo‘q → nom.
3. Boshqa hisobdan `/add` → rad xabari kelishi kerak.
4. Shaxsiy chat, guruh va yozish huquqi mavjud kanalda inline qidirib yuborish.
5. Botni qayta ishga tushirib, avvalgi audio qidiruvda qolishini tekshirish.

Bot tokeni berilmagani sabab tayyorlash vaqtida real Telegram hisobida sinov va serverga joylash bajarilmagan. Lokal testlar natijasi `TEST_REPORT.md` ichida.

## Tuzilishi

- `echobite/bot.py` — dialog, avtorizatsiya, inline va polling.
- `echobite/api.py` — HTTPS Bot API va fayl yuklash.
- `echobite/media.py` — FFprobe tekshiruvi, vaqt parseri va FFmpeg.
- `echobite/store.py` — SQLite katalogi va qidiruv.
- `echobite/identity.py` — faqat ID aniqlash uchun sozlash rejimi.
- `.env.example`, `Dockerfile`, `compose.yaml` — konfiguratsiya va ishga tushirish.

Rasmiy hujjatlar: https://core.telegram.org/bots/inline , https://core.telegram.org/bots/api , https://ffmpeg.org/ffmpeg-filters.html#atrim .
