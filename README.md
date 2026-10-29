# 🗣️ Auditory Differentiation & Speech Trainer

A free, offline-friendly, single-file web app for **speech and hearing rehabilitation** — built for people with **aphasia**, apraxia of speech, and other speech/hearing disorders, as well as for speech therapists and caregivers working with them.

🇬🇧 [English](#english) · 🇺🇦 [Українська](#українська)

---

<a name="english"></a>
## 🇬🇧 English

### About

This app helps people recognize and correctly pronounce words by ear. It was designed with rehabilitation in mind: large buttons, high contrast, simple controls, adjustable difficulty, and a "play / rest" timer so a therapy session doesn't turn into overexertion.

The app runs entirely in the browser — no installation, no backend, no account. Open `index.html` and start practicing, or host it as a static page (e.g. GitHub Pages) or install it as a PWA on a phone.

### ✨ Features

- **Auditory differentiation exercises** — the app speaks a word aloud, and the user picks the correct word out of 2, 3, or 4 similar-sounding options (minimal pairs), training the ear to tell real words apart.
- **Word-building / spelling task** — assemble the target word from its syllables, useful for speech and reading practice.
- **ABC mode (first-letter hint)** — for the “it’s on the tip of my tongue” moment: tap the first letter and the app lists matching words from the dictionary; tap a word to hear it and add it to a line that can be read aloud. A second keyboard mode allows free typing, mistakes included, and suggests similar words. Optional online word search (Wiktionary, Datamuse for English) can be switched on in Settings; chosen words are remembered on the device.
- **Text-to-speech (TTS)** — words are read aloud using the device's built-in voices, with adjustable speech speed.
- **Voice selection by gender** — pick a specific male or female voice for each language when the device offers several; voices are grouped and labeled automatically (♀ Female / ♂ Male / Other), with extra reliability fixes for Android, where voices can otherwise fail to load.
- **Speech recognition ("say it and check")** — the user pronounces the word into the microphone, and the app checks it against the target word using the browser's speech recognition.
- **25 thematic word categories** — household items, food, body parts, emotions, family, animals, professions, city & transport, colors, numbers, verbs, adjectives, and more — plus an "all categories" mode.
- **Three interface languages**: English, Ukrainian, and Russian — with a matching dictionary and speech recognition locale for each.
- **Adjustable difficulty**: 2 / 3 / 4 answer options per question (Easy / Medium / Hard).
- **Play / Rest timer** — configurable session and break lengths, with a rest overlay, to support therapy pacing and prevent fatigue.
- **Gentle mode (on by default)** — no red errors: a wrong option simply fades out and the word is spoken again until the user finds the answer; correct answers get short praise and a light vibration on phones.
- **Picture support (emoji)** — a picture next to each answer option and a large one after the answer, for about 45% of the words; can be switched off.
- **Step-by-step hints** — 💡 first syllable → the word by syllables → the highlighted answer.
- **🐢 Speak by syllables** — the word is spoken slowly, syllable by syllable, then as a whole.
- **Auto-speak** the new word (optional) with a slow speech speed by default.
- **Progress stats** — running count of correct answers (and total attempts in classic mode).
- **Light / dark theme**, responsive layout for phones and tablets.
- **Works offline** as an installable PWA (manifest + icons); all settings (language, voice, theme, timer, category, etc.) are saved locally on the device.

### 🚀 Getting started

1. Download or clone this repository.
2. Open `index.html` in a modern browser (Chrome/Edge recommended for the best text-to-speech and speech-recognition support), or deploy the folder to any static host / GitHub Pages.
3. Optional: install it to your home screen as a PWA for offline use on a phone.

No build tools, servers, or dependencies are required — it's a single self-contained HTML file.

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

<a name="українська"></a>
## 🇺🇦 Українська

### Про проєкт

Цей застосунок допомагає розпізнавати слова на слух і правильно їх вимовляти. Він створений спеціально для реабілітації мовлення та слуху — для людей з **афазією**, апраксією мовлення та іншими порушеннями мовлення й слуху, а також для логопедів і рідних, які їм допомагають.

Інтерфейс адаптований під потреби реабілітації: великі кнопки, високий контраст, прості елементи керування, регульована складність та таймер «гра / відпочинок», щоб заняття не перетворювалось на перевтому.

Застосунок повністю працює в браузері — без встановлення, без сервера, без реєстрації. Просто відкрийте `index.html` і починайте тренуватися, або розмістіть його як статичну сторінку (наприклад, на GitHub Pages), або встановіть як PWA на телефон.

### ✨ Можливості

- **Вправи на слухову диференціацію** — застосунок озвучує слово, а користувач обирає правильний варіант з 2, 3 або 4 схожих за звучанням слів (мінімальні пари), тренуючи слух розрізняти реальні слова.
- **Складання слова / завдання на письмо** — зібрати загадане слово зі складів, що корисно для тренування мовлення й читання.
- **Режим «Абетка» (підказка за першою літерою)** — для моменту, коли слово «крутиться на язиці»: натисніть першу літеру, і застосунок покаже відповідні слова зі словника; натисніть слово, щоб почути його й додати до рядка, який можна озвучити. Другий режим клавіатури — вільний набір, навіть з помилками, із підказкою схожих слів. За бажанням у налаштуваннях можна ввімкнути онлайн-пошук слів (Вікісловник, для англійської ще Datamuse); обрані слова запам’ятовуються на пристрої.
- **Синтез мовлення (TTS)** — слова озвучуються вбудованими голосами пристрою, зі змінюваною швидкістю мовлення.
- **Вибір голосу за статтю** — можна обрати чоловічий або жіночий голос для кожної мови, якщо пристрій пропонує декілька варіантів; голоси автоматично групуються та підписуються (♀ Жіночі / ♂ Чоловічі / Інші), а також додано виправлення для надійнішого завантаження голосів на Android, де вони раніше могли не з'являтися.
- **Перевірка вимови мікрофоном** — користувач вимовляє слово вголос, а застосунок звіряє сказане із загаданим словом за допомогою розпізнавання мовлення браузера.
- **25 тематичних категорій слів** — побут, їжа, частини тіла, емоції, родина, тварини, професії, місто й транспорт, кольори, числа, дієслова, прикметники тощо, а також режим «усі категорії».
- **Три мови інтерфейсу**: англійська, українська та російська — з окремим словником і мовою розпізнавання мовлення для кожної.
- **Регульована складність**: 2 / 3 / 4 варіанти відповіді на запитання (Легко / Середньо / Складно).
- **Таймер «Гра / Відпочинок»** — з можливістю налаштувати тривалість заняття та перерви й екраном відпочинку, щоб підтримувати правильний темп занять і запобігати перевтомі.
- **М'який режим (увімкнений за замовчуванням)** — без червоних помилок: неправильний варіант просто гасне, а слово озвучується знову, доки людина не знайде відповідь; за правильну відповідь — коротка похвала й легка вібрація на телефоні.
- **Візуальна опора (емодзі)** — картинка біля кожного варіанту відповіді та велика після відповіді, приблизно для 45% слів; можна вимкнути.
- **Покрокові підказки** — 💡 перший склад → слово по складах → підсвічена відповідь.
- **🐢 Озвучення по складах** — слово вимовляється повільно, склад за складом, а потім цілком.
- **Автоозвучення** нового слова (за бажанням) з повільною швидкістю мовлення за замовчуванням.
- **Статистика прогресу** — лічильник правильних відповідей (і загальної кількості спроб у класичному режимі).
- **Світла / темна тема**, адаптивний вигляд для телефонів і планшетів.
- **Робота офлайн** як встановлюваний PWA-застосунок (маніфест + іконки); усі налаштування (мова, голос, тема, таймер, категорія тощо) зберігаються локально на пристрої.

### 🚀 Як почати

1. Завантажте або клонуйте цей репозиторій.
2. Відкрийте `index.html` у сучасному браузері (рекомендовано Chrome/Edge для найкращої підтримки синтезу й розпізнавання мовлення), або розмістіть папку на будь-якому статичному хостингу чи GitHub Pages.
3. За бажанням: встановіть застосунок на головний екран телефону як PWA для офлайн-використання.

Жодних інструментів збірки, серверів чи залежностей не потрібно — це один самодостатній HTML-файл.

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

## 🇷🇺 Русский

### ✍️ Об авторстве

Весь код этого приложения написан ИИ-ассистентом Claude (Anthropic) по заданию и под руководством автора проекта: идея, требования, проверка на практике и решение о публикации принадлежат автору.

Тексты фраз и справки на русском, украинском и английском тоже подготовлены ИИ-ассистентом. Их не проверяли носители языка и специалисты, поэтому перед использованием с конкретным человеком их стоит просмотреть, особенно медицинские формулировки. Приложение не является медицинским изделием и не заменяет врача или логопеда.

### 📄 Лицензия

Приложение распространяется по лицензии [MIT](LICENSE): его можно свободно использовать, копировать, изменять и распространять, в том числе в своих проектах. Условие одно: сохраняйте в копиях текст лицензии и указание авторства. Будем благодарны, если вы также оставите ссылку на оригинальный репозиторий.

Приложение предоставляется «как есть», без каких-либо гарантий.
