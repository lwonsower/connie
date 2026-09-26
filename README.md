# Speaker

**A context-first language coach for Claude. It works for any language, at any level.**

Most language apps teach words on flashcards: *der Zufall = coincidence*. Words learned that way are hard to remember and easy to misuse. Speaker never shows a word on its own. Every new word comes inside a sentence, and the best sentences come from a story you actually want to keep reading.

- 📖 **An ongoing mystery (or drama, or adventure) in your target language**, with recurring characters and one short episode per session. Everything is pitched at your level.
- 🔁 **Review that doesn't feel like review.** Words that are due come back in the next episode, and you answer questions about the story instead of flipping flashcards.
- 🕵️ **Story games:** earn clues in the target language and solve the season's mystery, or play spot the lie, who said it? or choose your path.
- 🎯 **An adaptive placement test**, from total beginner to advanced, themed around your interests.
- 💬 **Chat and role-play** with gentle corrections.
- 🎵 **Real material:** work through articles, texts from friends and lines from songs you love, as well as proverbs, folk songs and poems.
- 🏅 **Can-do milestones**, like *I can tell what I did last weekend* or *I can argue a position*, earned through real use and celebrated when you get there.
- 📊 **Progress tracking** in a plain file you own, with an at-a-glance dashboard right in the chat.

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
| `milestones` | Your can-do goals: earned, in focus, and what's next |
| `progress` | A text summary of how you're doing |
| `dashboard` | An at-a-glance progress dashboard, shown in the chat |
| `settings` | Correction style, romanization, formality, explanation language |
| `switch <language>` | Switch between the languages you're learning |

---

## How it works

**Context first.** Every word is taught, saved and reviewed along with the sentence you first met it in. Review questions ask what a word means *in that sentence*, have you fill in a quote from a character, or ask you to use the word yourself.

**Stories are the engine.** Each series has a small cast with distinct voices (one speaks in slang, one is very formal, one talks in proverbs), a setting where the language is actually spoken, and a central question for each season. Each episode has a short recap (where due words sneak back in), a scene at your level with 3–8 new words, one real cultural detail and a cliffhanger. At the end, you choose what happens next, in the target language.

**Spaced repetition, quietly.** Words come back after 1, 3, 7, 14, 30, 60 and 120 days. A word you miss comes back tomorrow, and there's no penalty for that. A small script (`scripts/review.py`) works out the dates, so they're always exact:

```bash
python3 scripts/review.py due practice/german-profile.md
python3 scripts/review.py grade practice/german-profile.md --got "gießen" --missed "der Zufall"
```

**Gentle corrections.** By default, you get a short recap of the 1–3 mistakes that matter most at the end of a message, not red ink on everything. You can change this in `settings`.

**Any language.** Speaker adapts to how each language works: gender and articles, cases, tones, measure words, particles, formal vs. informal speech, and different writing systems (with romanization until you don't need it). For total beginners in a new writing system, it teaches the script first, through real words and signs.

**Songs and copyright.** Speaker uses proverbs, folk songs and poems in the public domain freely. For copyrighted songs, paste the lines you're listening to and Speaker will explain them, but it won't reproduce lyrics you haven't pasted.

---

## Can-do milestones

Progress is measured in things you can *do*. Every level from Pre-A1 to C1 has the same six strands (People, Daily life, Getting things done, Telling stories, Opinions, Real material), so the milestones form one continuous path. For example:

| Level | Telling stories |
|---|---|
| Pre-A1 | I can follow a tiny story with support and say who did what. |
| A2 | I can tell what I did last weekend. |
| B1 | I can retell a story or film plot in order, with connectors. |
| C1 | I can write a short scene or story of my own. |

Your placement test credits the levels you already have, and you work on 1–2 **focus milestones** at a time. The story quietly gives you chances to use them: a character asks about your weekend, or something goes wrong at the café. A milestone is **earned with real practice: 3 successful uses on at least 2 different days**. One lucky answer doesn't count. When you earn one, it's celebrated in the story and with a milestone card. Earn all six and you've completed the level.

The full list is in `references/milestones.md`.

## Your files

Everything lives in plain Markdown next to wherever you keep your learning files. You can open, read and edit these files yourself.

| File | What's in it |
|---|---|
| `<language>-profile.md` | Your level, settings, saved words (with sentences and review dates), recurring mistakes, grammar covered and a session log |
| `<language>-story.md` | Your story: cast, running plot threads, clues found and a summary of each episode |
| `<language>-archive.md` | Older material moved out of the profile to keep it short: known words (still reviewed when due), resolved mistakes, earned milestones and older log entries |

---

## The dashboard

Type `dashboard` to see your progress right in the chat:

```
11 words saved · 0 due today · 1-day streak · 1 session this month

VOCABULARY BY STRENGTH
  new        11  ████████████████████████
  learning    0
  familiar    0
  known       0

WORDS ADDED, LAST 12 WEEKS   ▁▁▁▁▁▁▁▁▁▁▁█   (11 total, 11 this week)
```

This is followed by your current story and clues, recently learned words with their sentences, recurring mistakes, grammar you're comfortable or shaky with, and suggested next steps.

A small script (`scripts/dashboard.py`) does the counting, so the numbers are exact. It only needs Python 3, with no extra packages. You can also run it yourself:

```bash
python3 scripts/dashboard.py path/to/german-profile.md --next "Start the mystery series"
```

If Python isn't available, Speaker builds the same view by hand from your profile.

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
│   ├── stories.md                # how episodes, story review and games work
│   └── milestones.md             # the 36 can-do milestones and how they're earned
├── scripts/
│   ├── dashboard.py              # prints the progress dashboard (Python 3, standard library only)
│   ├── review.py                 # spaced repetition: due words, grading, saving words, tidying the profile
│   ├── milestones.py             # can-do milestones: setup, focus, evidence, earning
│   └── profile_md.py             # shared helpers for reading and editing the Markdown files
└── .gitignore                    # keeps personal learning files out of the repo
```

Your own learning files (`*-profile.md`, `*-story.md`, `*-archive.md`) are ignored by git, so you can keep them in a `practice/` folder inside the repo without publishing them.

---

## Sharing and feedback

Feel free to share Speaker with anyone learning a language. If you tweak it (new games, better placement questions, notes for specific languages), the places to edit are `SKILL.md` and `references/stories.md`.

Viel Spaß · Bonne chance · ¡Buena suerte · 頑張って 🎉
