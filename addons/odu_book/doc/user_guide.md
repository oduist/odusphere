# User Book

**Book** is the built-in interactive documentation of your OduSphere.
It is assembled automatically: the system finds every installed module and
shows their documentation sections in a single window, with no separate wiki.

The **Book** app has two menus:

- **Documentation** -- the current state of every module's guide.
- **Changes** -- a day-by-day archive of what was changed in the documentation.

## How it works

Each module keeps its user guide in a `doc/user_guide.md` file next to the
code. The Book finds these files and turns them into easy-to-read pages.

- On the left -- the list of modules that have a guide.
- On the right -- the text of the selected guide.
- The search box at the top filters sections by title.

Documentation and code live together and are updated at the same time: when a
module changes, its section in the Book changes with it. The Book shows only
what is actually installed in your OduSphere.

## How to read the change archive

The **Changes** menu is a timeline, like a blog archive. Whenever the
documentation of a module is updated, a short note for that day is recorded
next to the module. The archive collects every such note and lets you browse
the history day by day.

- On the left -- the days on which something changed, grouped by month. The
  newest day is on top; the small badge shows how many modules changed that day.
- On the right -- for the selected day, what each module added, changed or
  removed in its documentation. Added lines are shown in green, removed lines
  in red.

So the **Documentation** menu always answers "what is true now", while the
**Changes** menu answers "what changed, and when".

## How to extend the Book

To give a module a section in the Book, just put a `doc/user_guide.md` file
next to the code and write in it in plain language using Markdown.

The usual markup is supported: headings (`# Section`), lists (`- item`,
`1. item`), emphasis (`**bold**`, `*italic*`), code (`` `inline` `` and code
blocks), links, blockquotes and tables. The first-level heading at the start
of the file is convenient to use as the section title.

> The technical file `doc/tech_spec.md` is not included in the Book -- it is
> meant for developers and AI agents, not for the user.
