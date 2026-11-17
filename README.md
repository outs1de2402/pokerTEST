# Техаський Холдем онлайн (FastAPI + WebSocket)

Сервер веде всю гру (тасування, роздача, торги, сайд-поти, боти). У браузер надходять лише власні карти гравця,
карти суперників відкриваються тільки на вскритті.

## Запуск локально
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000
Відкрийте http://localhost:8000, зареєструйтесь, створіть стіл і передайте друзям 4-символьний код.
У домашній Wi-Fi друзі заходять на http://<IP-вашого-ПК>:8000.

## Доступ друзям з інтернету
- Швидкий тест: `cloudflared tunnel --url http://localhost:8000` або `ngrok http 8000` дає публічне https-посилання.
- Постійно: Render / Railway / Fly.io (є `Procfile`). SQLite-файл (`POKER_DB`, за замовчуванням `poker.db`) має лежати на постійному диску.

## Структура
- `cards.py` — колода, шу Fisher–Yates (SystemRandom), башмак на 6 колод, оцінка комбінацій
- `engine.py` — правила No-Limit Hold'em: торги, мінімальні рейзи, сайд-поти, нічиї
- `blackjack.py` — рушій Blackjack (6 колод, S17, 3:2, Double/DAS, Split до 4 рук)
- `bots.py` — ШІ ботів (стилі cautious / balanced / aggressive), окремо від рушія
- `server.py` — акаунти (PBKDF2 + токени), столи, WebSocket
- `static/index.html` — сторінка (вхід, головне меню, меню покеру, лобі, стіл)
- `static/css/app.css` — стилі та адаптивність
- `static/js/cardui.js` — спільні карти, `js/blackjack.js` — стіл Blackjack
- `static/js/fx.js` — анімації та звук (окремо від логіки), `js/poker.js` — малювання столу, `js/main.js` — навігація, зʼєднання, керування
- Тести: `python test_cards.py`, `python test_poker.py`, `python test_blackjack.py`, `python test_engine.py` (симуляція), `python smoke.py`, `python smoke_bj.py` (сервер)

## Що варто додати далі
обмеження спроб входу, термін дії токенів, чат за столом, відновлення гри після перезапуску сервера.
