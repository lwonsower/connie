# Speaker

**A context-first language coach for Claude. It works for any language, at any level.**

Most language apps teach words on flashcards: *der Zufall = coincidence*. Words learned that way are hard to remember and easy to misuse. Speaker never shows a word on its own. Every new word comes inside a sentence, and the best sentences come from a story you actually want to keep reading.

- 📖 **An ongoing mystery (or drama, or adventure) in your target language**, with recurring characters and one short episode per session. Everything is pitched at your level.
- 🔁 **Review that doesn't feel like review.** Words that are due come back in the next episode, and you answer questions about the story instead of flipping flashcards.
- 🕵️ **Story games:** earn clues in the target language and solve the season's mystery, or play spot the lie, who said it? or choose your path.
- 🎯 **An adaptive placement test**, from total beginner to advanced, themed around your interests.
- 💬 **Chat and role-play** with gentle corrections.
- 🎵 **Real material:** work through articles, texts from friends and lines from songs you love, as well as proverbs, folk songs and poems.
- 📊 **Progress tracking** in a plain file you own, with a visual dashboard.

---

## Getting started

1. Install the skill (see [Installing](#installing) below).
2. Start a conversation with Claude and say something like *"I want to learn Italian"* or *"let's practice my Japanese"*, or type `/speaker-skill`.
3. Speaker asks a few quick questions (your level, why you're learning, what you're into), offers a ~10-minute placement test, and then pitches you three story ideas.

That's it. Each time after that, type `story` to continue, or `menu` to see everything.

> **Tip:** to keep your progress between conversations, give Claude access to a folder (in Cowork or Claude Code), and Speaker will save your profile there. In a plain chat with no folder, Speaker prints your profile at the end of each session for you to save and paste back next time.

---

## Commands

Type a command on its own (`story`), after the skill name (`/speaker-skill story`), or just say what you want in your own words ("next episode please" works too).

| Command | What it does |
|---|---|
| `menu` / `help` | Home screen with what's due and suggested next steps |
| `setup` | First-time setup, or add a new language |
| `test` | Placement test, or a retest (about 10 minutes) |
| `story` | The next episode of your series, or start a new one |
| `review` | Words due for review, practiced through questions about the story |
| `game` | Story games: solve the mystery, spot the lie, who said it?, rewind |
| `chat [topic]` | Free conversation or role-play, e.g. `chat ordering at a bakery` |
| `learn [topic]` | Words for a specific need, e.g. `learn doctor's appointment` |
| `read` | Paste an article, a message or song lines, and work through them together |
| `quick` | A 5-minute snack for busy days |
| `words [filter]` | Browse your saved words with their sentences (`words new`, `words story`, `words this week`) |
| `progress` | A text summary of how you're doing |
| `dashboard` | A visual progress dashboard (HTML) |
| `settings` | Correction style, romanization, formality, explanation language |
| `switch <language>` | Switch between the languages you're learning |

---

## How it works

**Context first.** Every word is taught, saved and reviewed along with the sentence you first met it in. Review questions ask what a word means *in that sentence*, have you fill in a quote from a character, or ask you to use the word yourself.

**Stories are the engine.** Each series has a small cast with distinct voices (one speaks in slang, one is very formal, one talks in proverbs), a setting where the language is actually spoken, and a central question for each season. Each episode has a short recap (where due words sneak back in), a scene at your level with 3–8 new words, one real cultural detail and a cliffhanger. At the end, you choose what happens next, in the target language.

**Spaced repetition, quietly.** Words come back after 1, 3, 7, 14, 30, 60 and 120 days. A word you miss comes back tomorrow, and there's no penalty for that.

**Gentle corrections.** By default, you get a short recap of the 1–3 mistakes that matter most at the end of a message, not red ink on everything. You can change this in `settings`.

**Any language.** Speaker adapts to how each language works: gender and articles, cases, tones, measure words, particles, formal vs. informal speech, and different writing systems (with romanization until you don't need it). For total beginners in a new writing system, it teaches the script first, through real words and signs.

**Songs and copyright.** Speaker uses proverbs, folk songs and poems in the public domain freely. For copyrighted songs, paste the lines you're listening to and Speaker will explain them, but it won't reproduce lyrics you haven't pasted.

---

## Your files

Everything lives in plain Markdown next to wherever you keep your learning files. You can open, read and edit these files yourself.

| File | What's in it |
|---|---|
| `<language>-profile.md` | Your level, settings, saved words (with sentences and review dates), recurring mistakes, grammar covered and a session log |
| `<language>-story.md` | Your story: cast, running plot threads, clues found and a summary of each episode |
| `<language>-dashboard.html` | The visual dashboard, rebuilt every time you ask for it |

---

## The dashboard

Type `dashboard` to get a single-page view of your progress: your level, words saved, reviews due, streak, vocabulary by strength, words added per week, upcoming reviews, your current story and clues, recently learned words in context, recurring mistakes, grammar covered and suggested next steps. It works offline and in light or dark mode.

It's built by a small script (`scripts/build_dashboard.py`) that only needs Python 3, with no extra packages. You can also run it yourself:

```bash
python3 scripts/build_dashboard.py path/to/german-profile.md \
  --next "Start the mystery series" --next "Practice als ob clauses"
```

If Python isn't available, Speaker shows a text version of the dashboard in the chat instead.

---

## Installing

**Claude Code:** clone the repo straight into your personal skills directory:

```bash
git clone https://github.com/lwonsower/contextual-dialogue-coach.git ~/.claude/skills/speaker-skill
```

**Claude apps (Claude.ai, desktop, Cowork):** download the repo as a zip (or use a packaged `.skill` file if you were given one) and upload it as a custom skill in the skills section of your settings. Custom skills may need to be enabled for your account or organization first.

---

## What's in the repo

```
contextual-dialogue-coach/
├── SKILL.md                      # the coach's instructions (what Claude reads)
├── README.md                     # this file
├── references/
│   └── stories.md                # how episodes, story review and games work
├── scripts/
│   └── build_dashboard.py        # builds the progress dashboard (Python 3, standard library only)
├── assets/
│   └── dashboard_template.html   # dashboard layout and styling
└── .gitignore                    # keeps personal learning files out of the repo
```

Your own learning files (`*-profile.md`, `*-story.md`, `*-dashboard.html`) are ignored by git, so you can keep them in a `practice/` folder inside the repo without publishing them.

---

## Sharing and feedback

Feel free to share Speaker with anyone learning a language. If you tweak it (new games, better placement questions, notes for specific languages), the places to edit are `SKILL.md` and `references/stories.md`.

Viel Spaß · Bonne chance · ¡Buena suerte · 頑張って 🎉
