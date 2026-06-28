# User Book

**Book** is the built-in interactive documentation of your OduSphere.
It is assembled automatically: the system finds every installed module and
shows their documentation sections in a single window, with no separate wiki.

## How it works

Each module keeps its user guide in a `doc/user_guide.md` file next to the
code. The Book finds these files and turns them into easy-to-read pages.

- On the left -- the list of modules that have a guide.
- On the right -- the text of the selected guide.
- The search box at the top filters sections by title.

Documentation and code live together and are updated at the same time: when a
module changes, its section in the Book changes with it. The Book shows only
what is actually installed in your OduSphere.

## How to extend the Book

To give a module a section in the Book, just put a `doc/user_guide.md` file
next to the code and write in it in plain language using Markdown.

The usual markup is supported: headings (`# Section`), lists (`- item`,
`1. item`), emphasis (`**bold**`, `*italic*`), code (`` `inline` `` and code
blocks), links, blockquotes and tables. The first-level heading at the start
of the file is convenient to use as the section title.

> The technical file `doc/tech_spec.md` is not included in the Book -- it is
> meant for developers and AI agents, not for the user.
