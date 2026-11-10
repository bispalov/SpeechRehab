# 🗣️ Знову слова · Words Again

🇺🇦 [Українська](#українська) · 🇬🇧 [English](#english) · 🇷🇺 [Русский](#русский-авторство-и-лицензия)

---

<a name="українська"></a>
## 🇺🇦 Українська

### Про проєкт

**«Знову слова»** (англ. *Words Again*, рос. «Снова слова»; раніше — «Чуємо слова» / *Hear Words*, ще раніше — *Auditory Differentiation & Speech Trainer*) — безкоштовний застосунок для реабілітації мовлення, слуху й письма.

Цей застосунок допомагає розпізнавати слова на слух, правильно їх вимовляти й писати. Він створений спеціально для реабілітації мовлення та слуху — для людей з **афазією**, апраксією мовлення та іншими порушеннями мовлення й слуху, а також для логопедів і рідних, які їм допомагають.

Інтерфейс адаптований під потреби реабілітації: великі кнопки, високий контраст, прості елементи керування, регульована складність та таймер «гра / відпочинок», щоб заняття не перетворювалось на перевтому.

Застосунок повністю працює в браузері — без встановлення, без сервера, без реєстрації. Просто відкрийте `index.html` і починайте тренуватися, або розмістіть його як статичну сторінку (наприклад, на GitHub Pages), або встановіть як PWA на телефон.

### 🧭 Режими тренування

- **🧩 Повний тренажер** — усі блоки: вибір слова на слух, перевірка вимови, складання зі складів і літер, підказки.
- **🔢 Перелічення** — називання рядів по порядку, уперед і назад: дні тижня, місяці, пори року, частини доби, кольори веселки, числа 1–10, 1–20, десятки до 100 та власні ряди. Завдання «Весь ряд» і «Продовжити»; застосунок показує й голосом каже, що правильно, що пропущено й що зайве. Напрямок (уперед, назад або «туди й назад» одразу), рівень показу слів (завжди / після помилок / приховано — для поступового ускладнення), спосіб перевірки (після всього ряду або по одному слову: «Говорити» натискається перед кожним словом, слово одразу позначається ✅ або ❌) і голосова оцінка налаштовуються.
- **👂 Тренування на слух** — одне слово у два кроки: послухати й повторити вголос, скласти з літер (неправильні літери підсвічуються червоним і виправляються на місці); підсумок із картинкою наприкінці.
- **✍️ Письмо** — тренування правильного написання: слово за картинкою, диктант слова або диктант власної фрази. На всіх рівнях перші літери підказуються (кількість 0–3 — у налаштуваннях). Слово набирається на клавіатурі «Абетки»; після перевірки правильні літери зелені, помилкові підсвічено; натиснута літера одразу виправляє першу позначену, наступна — наступну; є підказки «ще літера» й «показати слово». Панель з літерами можна згорнути, зокрема автоматично після кожної літери (налаштування). Кнопки з літерами можна зменшити («🔡 Дрібніше»), щоб на екрані вміщалося більше; картинка й кнопка 🔊 стоять поруч із полем введення, а дотик до поля розгортає літери.
- **📝 Тест на слух** — 10–30 випадкових слів поспіль; кожне слово звучить один раз, а користувач вимовляє його; наприкінці — результат.
- **🔤 Абетка** — підказка за першою літерою, коли слово «крутиться на язиці».
- **🎤 Підказка за сказаним** — перенесено із застосунку «Говоримо разом» (вкладка «Говорить людина»): скажіть фразу, застосунок розбере її на слова, позначить сумнівні знаком «?», запропонує варіанти й запам’ятає ваші виправлення (автоматично слово замінюється лише після двох однакових виборів). Зібрану фразу можна потренувати вголос: застосунок озвучить її, ви повторите, а голос скаже, чи правильно; готову фразу можна зберегти в «Мої фрази». Необов’язково: файли `lex/uk.txt`, `lex/ru.txt`, `lex/en.txt` (частотні списки слів) роблять підказки точнішими.
- **🗣 Мої фрази** — тренування власних фраз. Нову фразу можна просто сказати: застосунок розбере її на слова, позначить сумнівні знаком «?», запропонує варіанти, озвучить виправлену фразу, а ви повторите її вголос і почуєте голосову оцінку; потім фразу можна додати до списку. Власні фрази також можна вписувати, тренувати з порівнянням за словами та виправленням. Список фраз можна зберегти у файл і завантажити; записи голосу не зберігаються, оцінка умовна (розпізнавання мовлення браузера недосконале).

### ✨ Можливості

- **Вправи на слухову диференціацію** — застосунок озвучує слово, а користувач обирає правильний варіант з 2, 3 або 4 схожих за звучанням слів (мінімальні пари), тренуючи слух розрізняти реальні слова.
- **Складання слова / завдання на письмо** — зібрати загадане слово зі складів, що корисно для тренування мовлення й читання.
- **Режим «Абетка» (підказка за першою літерою)** — для моменту, коли слово «крутиться на язиці»: натисніть першу літеру, і застосунок покаже відповідні слова зі словника; натисніть слово, щоб почути його й додати до рядка, який можна озвучити. Другий режим клавіатури — вільний набір, навіть з помилками, із підказкою схожих слів. За бажанням у налаштуваннях можна ввімкнути онлайн-пошук слів (Вікісловник, для англійської ще Datamuse); обрані слова запам’ятовуються на пристрої. Панель з літерами можна налаштувати так, щоб вона згорталася після кожного натискання. Короткі слова (я, ти, в, на, не…) додаються окремою кнопкою, слово у фразі прибирається натисканням, а зібрану фразу можна потренувати вголос і зберегти в «Мої фрази».
- **Синтез мовлення (TTS)** — слова озвучуються вбудованими голосами пристрою, зі змінюваною швидкістю мовлення.
- **Вибір голосу за статтю** — можна обрати чоловічий або жіночий голос для кожної мови, якщо пристрій пропонує декілька варіантів; голоси автоматично групуються та підписуються (♀ Жіночі / ♂ Чоловічі / Інші), а також додано виправлення для надійнішого завантаження голосів на Android, де вони раніше могли не з'являтися.
- **Перевірка вимови мікрофоном** — користувач вимовляє слово вголос, а застосунок звіряє сказане із загаданим словом за допомогою розпізнавання мовлення браузера. Слово зараховується, якщо воно є серед варіантів розпізнавання; після помилки звучить правильне слово (у м’якому режимі — без слова «Неправильно»). Поки мікрофон слухає, застосунок нічого не озвучує, а помилки мікрофона чи мережі пояснюються простими словами.
- **25 тематичних категорій слів** — побут, їжа, частини тіла, емоції, родина, тварини, професії, місто й транспорт, кольори, числа, дієслова, прикметники тощо, а також режим «усі категорії».
- **Три мови інтерфейсу**: англійська, українська та російська — з окремим словником і мовою розпізнавання мовлення для кожної.
- **Регульована складність**: 2 / 3 / 4 варіанти відповіді на запитання (Легко / Середньо / Складно).
- **Таймер «Гра / Відпочинок»** — з можливістю налаштувати тривалість заняття та перерви й екраном відпочинку, щоб підтримувати правильний темп занять і запобігати перевтомі. Час рахується лише в режимах тренування; в «Абетці» й «Підказці за сказаним» перерва починається після озвучення фрази або виходу з режиму.
- **М'який режим (увімкнений за замовчуванням)** — без червоних помилок: неправильний варіант просто гасне, а слово озвучується знову, доки людина не знайде відповідь; за правильну відповідь — коротка похвала й легка вібрація на телефоні.
- **Візуальна опора (емодзі)** — картинка біля кожного варіанту відповіді та велика після відповіді, приблизно для 45% слів; можна вимкнути.
- **Покрокові підказки** — 💡 перший склад → слово по складах → підсвічена відповідь.
- **🐢 Озвучення по складах** — слово вимовляється повільно, склад за складом, а потім цілком.
- **Автоозвучення** нового слова (за бажанням) з повільною швидкістю мовлення за замовчуванням.
- **Статистика прогресу** — за режимами («Повний тренажер», «Перелічення», «Тренування слуху», «Письмо» та всі разом): спроби й правильні відповіді сьогодні й по днях, важкі слова, часті плутанини, результати за рядами; експорт у CSV.
- **Світла / темна тема**, адаптивний вигляд для телефонів і планшетів.
- **Зручна навігація** — системна кнопка «Назад» на Android повертає на крок назад, а не закриває застосунок; налаштування згруповано за режимами; залишок часу таймера видно в шапці.
- **Голосова оцінка** — одне налаштування для всіх режимів; після помилки звучить правильне слово. У «Тесті на слух» можна дозволити один повтор слова.
- **Робота офлайн** як встановлюваний PWA-застосунок (маніфест + іконки); усі налаштування (мова, голос, тема, таймер, категорія тощо) зберігаються локально на пристрої.
- **Резервна копія даних** — у налаштуваннях (група «💾 Дані») можна зберегти всі налаштування, свої слова й фрази та статистику в один файл і завантажити їх на іншому телефоні або після перевстановлення.
- **Підказка для вбудованого браузера** — якщо посилання відкрито всередині Facebook, Instagram, Messenger тощо, згори з’являється жовта плашка: там застосунок не бачить ваших даних, тож його варто відкрити в Chrome (кнопка «Відкрити в Chrome» на Android або «Копіювати посилання»).

### 🚀 Як почати

1. Завантажте або клонуйте цей репозиторій.
2. Відкрийте `index.html` у сучасному браузері (рекомендовано Chrome/Edge для найкращої підтримки синтезу й розпізнавання мовлення), або розмістіть папку на будь-якому статичному хостингу чи GitHub Pages.
3. За бажанням: встановіть застосунок на головний екран телефону як PWA для офлайн-використання (у Chrome на Android: меню ⋮ → «Установити застосунок» / «Додати на головний екран»).

Жодних інструментів збірки, серверів чи залежностей не потрібно — це набір статичних файлів.

**Мова.** Під час першого запуску мова інтерфейсу відповідає мові пристрою (українська, російська чи англійська; в інших випадках — англійська). Змінити її можна в «Налаштуваннях», вибір запам'ятовується. Маніфест застосунку українською: після встановлення під іконкою відображається назва «Знову слова». Адреса й назва репозиторію (`SpeechRehab`) не змінювалися, тому встановлені копії оновлюються як раніше.

### 📁 Файли репозиторію

Для роботи застосунку потрібні:

- `index.html` — сам застосунок;
- `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png` — встановлення як PWA та робота офлайн;
- `accents.js` — таблиця наголосів;
- `dict-uk.js`, `dict-ru.js`, `dict-en.js` — словники.

Необов'язково: `extra-dict.json` — додатковий словник, який підвантажується за наявності інтернету. Файли `README.md` і `LICENSE` застосунку не потрібні, але потрібні для опису й ліцензії проєкту.

Шляхи в `manifest.json` і `sw.js` вказані як `/SpeechRehab/…`, тому репозиторій (або папка на хостингу) має називатися `SpeechRehab`. Після будь-яких змін у файлах збільшуйте номер версії кешу в `sw.js` (`CACHE`), інакше встановлені застосунки не оновляться.

### 🎯 Для кого цей застосунок

- Для людей, які відновлюються після інсульту, ЧМТ чи інших станів, що спричиняють афазію або порушення мовлення й слуху.
- Для логопедів, яким потрібен безкоштовний інструмент для вправ на слухову диференціацію.
- Для родичів і доглядальників, які підтримують домашні заняття.

### ⚠️ Застереження

Це тренувальний інструмент, а не медичний виріб. Він не діагностує й не лікує жодних станів і не замінює консультацію кваліфікованого логопеда чи лікаря.

### 🤝 Участь у розвитку проєкту

Будемо раді issue та pull request'ам — нові мови, слова для словника, покращення доступності та повідомлення про помилки допоможуть проєкту.

### ✍️ Авторство

Увесь код цього застосунку написано ШІ-асистентом Claude (Anthropic) за завданням і під керівництвом автора проєкту: ідея, вимоги, перевірка на практиці та рішення про публікацію належать авторові.

Тексти фраз і довідки російською, українською та англійською також підготовлено ШІ-асистентом. Їх не перевіряли носії мови та фахівці, тому перед використанням із конкретною людиною їх варто переглянути, особливо медичні формулювання. Застосунок не є медичним виробом і не замінює лікаря чи логопеда.

### 📄 Ліцензія

Застосунок поширюється за ліцензією [MIT](LICENSE): його можна вільно використовувати, копіювати, змінювати й поширювати, зокрема у власних проєктах. Умова одна: зберігайте в копіях текст ліцензії та зазначення авторства. Будемо вдячні, якщо ви також залишите посилання на оригінальний репозиторій.

Застосунок надається «як є», без жодних гарантій.

---

<a name="english"></a>
## 🇬🇧 English

### About

**Words Again** (Ukrainian «Знову слова», Russian «Снова слова»; formerly «Чуємо слова» / *Hear Words*, and before that *Auditory Differentiation & Speech Trainer*) is a free app for speech, hearing and writing rehabilitation.

This app helps people recognize words by ear, pronounce them correctly and write them. It was designed with rehabilitation in mind: large buttons, high contrast, simple controls, adjustable difficulty, and a "play / rest" timer so a therapy session doesn't turn into overexertion.

The app runs entirely in the browser — no installation, no backend, no account. Open `index.html` and start practicing, or host it as a static page (e.g. GitHub Pages) or install it as a PWA on a phone.

### 🧭 Training modes

- **🧩 Full trainer** — all blocks: choose the word by ear, pronunciation check, assembling from syllables and letters, hints.
- **🔢 Sequences** — saying series in order, forwards and backwards: days of the week, months, seasons, parts of the day, colours of the rainbow, numbers 1–10, 1–20, tens up to 100, and your own series. Tasks “Whole series” and “Continue”; the app shows and says by voice what was right, missing or extra. Direction (forwards, backwards or “there and back” in one go), the level of word display (always / after mistakes / hidden — to make the task harder gradually), the checking method (after the whole series, or one word at a time: tap “Speak” before each word and it is marked ✅ or ❌ right away) and the spoken verdict are configurable.
- **👂 Listening practice** — one word in two steps: listen and repeat aloud, assemble from letters (wrong letters turn red and are fixed in place); a summary with a picture at the end.
- **✍️ Writing** — practice spelling: a word from a picture, dictation of a word, or dictation of your own phrase. On every level the first letters are given as a hint (0–3, set in Settings). The word is typed on the ABC keyboard; after checking, correct letters are green and wrong ones are highlighted; the tapped letter fixes the first marked one, the next tap the next one; hints “one more letter” and “show the word” are available. The letter panel can be collapsed, also automatically after each letter (a setting). The letter buttons can be made smaller (“🔡 Smaller”) so more fits on the screen; the picture and a 🔊 button sit next to the input field, and tapping the field opens the letters.
- **📝 Hearing test** — 10 to 30 random words in a row; each word is played once and the user says it; a result at the end.
- **🔤 ABC** — first-letter help for when a word is on the tip of your tongue.
- **🎤 Suggestions from what was said** — ported from the “Let’s talk together” app (the “The person speaks” tab): say a phrase, the app splits it into words, marks doubtful ones with “?”, offers options and remembers your corrections (a word is replaced automatically only after the same choice twice). The assembled phrase can be practised aloud: the app speaks it, you repeat it, and a voice tells you whether it was right; the finished phrase can be saved to “My phrases”. Optional: `lex/uk.txt`, `lex/ru.txt`, `lex/en.txt` (word-frequency lists) make the suggestions more precise.
- **🗣 My phrases** — practice with your own phrases. Just say a new phrase: the app splits it into words, marks doubtful ones with “?”, offers options, speaks the corrected phrase, you repeat it aloud and hear a spoken verdict; then the phrase can be added to the list. Own phrases can also be typed in and practised with a word-by-word comparison and fixing. The phrase list can be saved to and loaded from a file; voice recordings are not saved, and the score is approximate (browser speech recognition is imperfect).

### ✨ Features

- **Auditory differentiation exercises** — the app speaks a word aloud, and the user picks the correct word out of 2, 3, or 4 similar-sounding options (minimal pairs), training the ear to tell real words apart.
- **Word-building / spelling task** — assemble the target word from its syllables, useful for speech and reading practice.
- **ABC mode (first-letter hint)** — for the “it’s on the tip of my tongue” moment: tap the first letter and the app lists matching words from the dictionary; tap a word to hear it and add it to a line that can be read aloud. A second keyboard mode allows free typing, mistakes included, and suggests similar words. Optional online word search (Wiktionary, Datamuse for English) can be switched on in Settings; chosen words are remembered on the device. The letter panel can be set to collapse automatically after each tap. Short words (I, you, to, in, not…) are added with a separate button, a word in the phrase is removed with a tap, and the assembled phrase can be practised aloud and saved to “My phrases”.
- **Text-to-speech (TTS)** — words are read aloud using the device's built-in voices, with adjustable speech speed.
- **Voice selection by gender** — pick a specific male or female voice for each language when the device offers several; voices are grouped and labeled automatically (♀ Female / ♂ Male / Other), with extra reliability fixes for Android, where voices can otherwise fail to load.
- **Speech recognition ("say it and check")** — the user pronounces the word into the microphone, and the app checks it against the target word using the browser's speech recognition. The word counts if it is among the recognition variants; after a mistake the right word is spoken (in gentle mode without the word “Incorrect”). While the microphone is listening, the app does not speak, and microphone or network problems are explained in plain words.
- **25 thematic word categories** — household items, food, body parts, emotions, family, animals, professions, city & transport, colors, numbers, verbs, adjectives, and more — plus an "all categories" mode.
- **Three interface languages**: English, Ukrainian, and Russian — with a matching dictionary and speech recognition locale for each.
- **Adjustable difficulty**: 2 / 3 / 4 answer options per question (Easy / Medium / Hard).
- **Play / Rest timer** — configurable session and break lengths, with a rest overlay, to support therapy pacing and prevent fatigue. Time is counted only inside training modes; in ABC and “Suggestions from what was said” the break starts after a phrase is spoken or when leaving the mode.
- **Gentle mode (on by default)** — no red errors: a wrong option simply fades out and the word is spoken again until the user finds the answer; correct answers get short praise and a light vibration on phones.
- **Picture support (emoji)** — a picture next to each answer option and a large one after the answer, for about 45% of the words; can be switched off.
- **Step-by-step hints** — 💡 first syllable → the word by syllables → the highlighted answer.
- **🐢 Speak by syllables** — the word is spoken slowly, syllable by syllable, then as a whole.
- **Auto-speak** the new word (optional) with a slow speech speed by default.
- **Progress stats** — by mode (Full trainer, Sequences, Listening practice, Writing, and all together): tries and correct answers today and by day, difficult words, frequent confusions, results by series; CSV export.
- **Light / dark theme**, responsive layout for phones and tablets.
- **Easy navigation** — the Android “Back” button goes one step back instead of closing the app; settings are grouped by mode; the timer's time left is shown in the header.
- **Spoken verdict** — one setting for all modes; after a mistake the right word is spoken. The hearing test can allow one replay of each word.
- **Works offline** as an installable PWA (manifest + icons); all settings (language, voice, theme, timer, category, etc.) are saved locally on the device.
- **Data backup** — in Settings (the “💾 Data” group) all settings, your own words and phrases, and statistics can be saved to one file and loaded on another phone or after reinstalling.
- **In-app browser hint** — if the link is opened inside Facebook, Instagram, Messenger, etc., a yellow bar appears at the top: the app cannot see your data there, so it is better to open it in Chrome (“Open in Chrome” on Android, or “Copy link”).

### 🚀 Getting started

1. Download or clone this repository.
2. Open `index.html` in a modern browser (Chrome/Edge recommended for the best text-to-speech and speech-recognition support), or deploy the folder to any static host / GitHub Pages.
3. Optional: install it to your home screen as a PWA for offline use on a phone (Chrome on Android: menu ⋮ → “Install app” / “Add to Home screen”).

No build tools, servers, or dependencies are required — it is a set of static files.

**Language.** On first launch the interface language follows the device language (Ukrainian, Russian or English; English otherwise). It can be changed in Settings and the choice is remembered. The app manifest is in Ukrainian, so after installation the name under the icon is «Знову слова». The address and the repository name (`SpeechRehab`) have not changed, so installed copies keep updating.

### 📁 Repository files

The app needs:

- `index.html` — the app itself;
- `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png` — PWA installation and offline use;
- `accents.js` — the stress table;
- `dict-uk.js`, `dict-ru.js`, `dict-en.js` — the dictionaries.

Optional: `extra-dict.json` — an additional dictionary loaded when the internet is available. `README.md` and `LICENSE` are not used by the app but belong to the project.

Paths in `manifest.json` and `sw.js` are set to `/SpeechRehab/…`, so the repository (or hosting folder) must be named `SpeechRehab`. After changing any file, increase the cache version (`CACHE`) in `sw.js`, otherwise installed copies will not update.

### 🎯 Who is it for

- People recovering from stroke, TBI, or other conditions causing aphasia or speech/hearing difficulties.
- Speech and language therapists (SLPs) looking for a free auditory-discrimination drill tool.
- Family members and caregivers supporting at-home practice.

### ⚠️ Disclaimer

This is a practice tool, not a medical device. It does not diagnose or treat any condition and is not a substitute for guidance from a qualified speech-language pathologist or physician.

### 🤝 Contributing

Issues and pull requests are welcome — additional languages, dictionary words, accessibility improvements, and bug reports all help.

### ✍️ Authorship

All of the code of this app was written by the AI assistant Claude (Anthropic) on the assignment and under the direction of the project's author: the idea, the requirements, practical testing and the decision to publish belong to the author.

The phrases and help texts in Russian, Ukrainian and English were also prepared by the AI assistant. They have not been reviewed by native speakers or specialists, so before using the app with a specific person they should be read through, especially the medical wording. The app is not a medical device and does not replace a doctor or a speech-language pathologist.

### 📄 License

The app is distributed under the [MIT License](LICENSE): you may freely use, copy, modify and distribute it, including in your own projects. There is one condition: keep the license text and the copyright notice in your copies. We would also be grateful if you left a link to the original repository.

The app is provided "as is", without warranty of any kind.

---

<a name="русский-авторство-и-лицензия"></a>
## 🇷🇺 Русский (авторство и лицензия)

### ✍️ Об авторстве

Весь код этого приложения написан ИИ-ассистентом Claude (Anthropic) по заданию и под руководством автора проекта: идея, требования, проверка на практике и решение о публикации принадлежат автору.

Тексты фраз и справки на русском, украинском и английском тоже подготовлены ИИ-ассистентом. Их не проверяли носители языка и специалисты, поэтому перед использованием с конкретным человеком их стоит просмотреть, особенно медицинские формулировки. Приложение не является медицинским изделием и не заменяет врача или логопеда.

### 📄 Лицензия

Приложение распространяется по лицензии [MIT](LICENSE): его можно свободно использовать, копировать, изменять и распространять, в том числе в своих проектах. Условие одно: сохраняйте в копиях текст лицензии и указание авторства. Будем благодарны, если вы также оставите ссылку на оригинальный репозиторий.

Приложение предоставляется «как есть», без каких-либо гарантий.
