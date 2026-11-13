# Audiobook

A library of audiobooks, with a web player.

**Player:** https://ted72782.github.io/Audiobook/player/

## Layout

```
books/
  art-of-small-talk/     one folder per book
    book.json            optional: { "title": "...", "subtitle": "...", "author": "..." }
    mp3/                 the tracks, numbered in listening order
    script/              the text of each track
    synth.py             the script that built the audio
player/
  index.html             the player (one file)
```

## Adding a book

Create a folder under `books/` and put the audio files in it, numbered so they
sort in listening order (`01_...mp3`, `02_...mp3`). The player picks it up on
its next Refresh. Without a `book.json` the folder name is used as the title.
Folders inside a book (for example `part-1/`, `part-2/`) appear as headings.

## Books

### The Art of Small Talk: A Master Class

Thirteen tracks, about 67 minutes, narrated with Kokoro text-to-speech.

| # | Track |
|---|---|
| 0 | Welcome |
| 1 | Why Small Talk Is Not Small |
| 2 | The Inner Game |
| 3 | The First Ten Seconds |
| 4 | Questions That Open Doors |
| 5 | The Art of Listening |
| 6 | Giving Something Back |
| 7 | Keeping It Moving |
| 8 | From Small Talk to Real Talk |
| 9 | Working the Room |
| 10 | The Graceful Exit |
| 11 | The Hard Cases |
| 12 | Thirty Days of Practice |

### Speak Like a Leader: A Master Class in Leadership Communication

Thirteen tracks, about 70 minutes, narrated with Kokoro text-to-speech.

| # | Track |
|---|---|
| 0 | Welcome |
| 1 | What Your Words Are For |
| 2 | Presence: Calm Before Words |
| 3 | Clarity: Say the Point First |
| 4 | Listening Like a Leader |
| 5 | Telling the Story |
| 6 | Feedback That Helps |
| 7 | Hard Conversations |
| 8 | Meetings, and Speaking to a Room |
| 9 | Leading Through Change and Uncertainty |
| 10 | Influence Without Authority |
| 11 | Writing Like a Leader |
| 12 | Thirty Days of Practice |

## Player

The player opens to a library of books; choose one to see its tracks. It
remembers your place in each track, shows how much of each book you have
played, keeps downloaded tracks for replay, and has skip, speed and a sleep
timer. It reads this repository by default; Settings points it at another one
(a private repository needs a read-only access token).
