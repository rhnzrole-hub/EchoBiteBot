# v3 test natijalari

2026-10-30. `python -m unittest discover -s tests -v`: **26 test muvaffaqiyatli**.

Avvalgi 18 test: admin huquqlari, qo‘shish/kesish, inline voice, qidiruv, /delete va /clear tasdiqlari, eskirgan tugmalar, bazani migratsiya qilish va MP3/M4A/OGG/FLAC kirishlari.

Qo‘shimcha 8 test: local konfiguratsiya, cloud 20 MB limiti, local 2 GB limiti, 2 GB+1 baytni rad etish, metadata bo‘lmaganda disk hajmini tekshirish, fayl papkasi chegaralari, getFile uchun uzaytirilgan timeout va 2 GB fayl yo‘li bilan ishlash.

Haqiqiy FFmpeg sinovi: diskdagi mantiqiy hajmi 2,000,000,000 bayt bo‘lgan **sparse PCM WAV** yaratildi. U valid WAV va davomiyligi 1 soatdan ko‘p; OS nol bloklarni fizik yozmasdan saqlaydi. Local getFile javobi mock qilindi; bot faylni nusxalamasdan va read_bytes chaqirmasdan oldi. FFmpeg undan 1.125 soniyali voice parcha yaratdi. Bu 2 GB internet uzatish tezligi sinovi emas.

Real Telegram bilan 2 GB yuklash, Windows’da rasmiy C++ API serverini build qilish va ishga tushirish bu muhitda bajarilmadi: token, API ID/hash va foydalanuvchi kompyuteriga kirish mavjud emas. LOCAL_API_WINDOWS.md shu bosqichlarni foydalanuvchi uchun tushuntiradi.
