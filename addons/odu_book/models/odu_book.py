# -*- coding: utf-8 -*-
import logging
import os
import re

from odoo import api, models
from odoo.modules.module import get_module_path

from .markdown import md_to_html

_logger = logging.getLogger(__name__)

#: Folder inside a module that holds the user documentation.
DOC_DIRNAME = "doc"
#: File name of the user guide (see CLAUDE.md, two-layer documentation).
GUIDE_FILENAME = "user_guide.md"
#: Folder inside ``doc`` that holds the per-day documentation-change timeline.
CHANGES_DIRNAME = "changes"
#: A change file is named after its day: ``YYYY-MM-DD.md``.
CHANGE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
#: Prefix of the OduSphere modules that are included in the Book.
MODULE_PREFIX = "odu_"


class OduBook(models.AbstractModel):
    """User documentation collector.

    The model stores nothing (no table): it reads the installed ``odu_*``
    modules and assembles their ``doc/user_guide.md`` user guides from disk
    into a single book. The technical layer (``doc/tech_spec.md``) is
    deliberately ignored -- it is meant for agents, not for the user.
    """

    _name = "odu.book"
    _description = "User Book"

    @api.model
    def get_book(self):
        """Assemble the book from the guides of every installed ``odu_*`` module.

        :return: ``{"pages": [{"id", "module", "title", "html"}, ...]}`` --
            one page per module (its ``doc/user_guide.md``).
        """
        modules = self.env["ir.module.module"].sudo().search(
            [
                ("state", "=", "installed"),
                ("name", "=like", MODULE_PREFIX + "%"),
            ],
            order="name",
        )
        pages = []
        for module in modules:
            html = self._read_module_guide(module.name)
            if html is None:
                continue
            pages.append(
                {
                    "id": module.name,
                    "module": module.name,
                    "title": module.shortdesc or module.name,
                    "html": html,
                }
            )
        return {"pages": pages}

    def _read_module_guide(self, module_name):
        """Read and render the module's ``doc/user_guide.md`` (or None)."""
        module_path = get_module_path(module_name)
        if not module_path:
            return None
        filepath = os.path.join(module_path, DOC_DIRNAME, GUIDE_FILENAME)
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as handle:
                raw = handle.read()
        except (OSError, UnicodeDecodeError):
            _logger.warning("odu_book: failed to read %s", filepath)
            return None
        return md_to_html(raw)

    @api.model
    def get_changes(self):
        """Assemble the day-by-day documentation-change archive.

        Every installed ``odu_*`` module may keep an append-only timeline of
        its documentation changes under ``doc/changes/``: one Markdown file per
        calendar day, named ``YYYY-MM-DD.md``. This collects them all and
        groups them by day so the UI can render a blog-like archive.

        :return: ``{"days": [{"date": "YYYY-MM-DD", "entries": [{"module",
            "title", "html"}, ...]}, ...]}`` -- days ordered most-recent first,
            entries within a day ordered by module name.
        """
        modules = self.env["ir.module.module"].sudo().search(
            [
                ("state", "=", "installed"),
                ("name", "=like", MODULE_PREFIX + "%"),
            ],
            order="name",
        )
        days = {}
        for module in modules:
            title = module.shortdesc or module.name
            for date_str, html in self._read_module_changes(module.name):
                days.setdefault(date_str, []).append(
                    {
                        "module": module.name,
                        "title": title,
                        "html": html,
                    }
                )
        return {
            "days": [
                {"date": date_str, "entries": days[date_str]}
                for date_str in sorted(days, reverse=True)
            ]
        }

    def _read_module_changes(self, module_name):
        """Yield ``(date_str, html)`` for the module's ``doc/changes/*.md``.

        Only files named ``YYYY-MM-DD.md`` are considered; anything else is
        ignored. Unreadable / non-UTF-8 files are skipped with a warning.
        """
        module_path = get_module_path(module_name)
        if not module_path:
            return []
        changes_dir = os.path.join(module_path, DOC_DIRNAME, CHANGES_DIRNAME)
        if not os.path.isdir(changes_dir):
            return []
        result = []
        for filename in sorted(os.listdir(changes_dir)):
            match = CHANGE_FILE_RE.match(filename)
            if not match:
                continue
            filepath = os.path.join(changes_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    raw = handle.read()
            except (OSError, UnicodeDecodeError):
                _logger.warning("odu_book: failed to read %s", filepath)
                continue
            result.append((match.group(1), md_to_html(raw)))
        return result
