# -*- coding: utf-8 -*-
import logging
import os
import re

from odoo import api, models
from odoo.exceptions import AccessError
from odoo.modules.module import get_module_path

from .markdown import md_to_html

_logger = logging.getLogger(__name__)

#: Folder inside a module that holds the user documentation.
DOC_DIRNAME = "doc"
#: File name of the end-user guide (the Userbook).
GUIDE_FILENAME = "user_guide.md"
#: File name of the administrator guide (the Adminbook) -- admin tasks & settings.
ADMIN_GUIDE_FILENAME = "admin_guide.md"
#: Folder inside ``doc`` that holds the per-day documentation-change timeline.
CHANGES_DIRNAME = "changes"
#: A change file is named after its day: ``YYYY-MM-DD.md``.
CHANGE_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
#: Folder inside ``doc`` holding translated mirrors: ``doc/i18n/<lang>/<file>``.
I18N_DIRNAME = "i18n"
#: Leading provenance marker a translated file carries; stripped before render.
I18N_MARKER_RE = re.compile(r"\A<!--\s*i18n\b[^>]*-->[ \t]*\r?\n?")
#: Prefix of the OduSphere modules that are included in the Book.
MODULE_PREFIX = "odu_"
#: Group required to read the administrator documentation.
ADMIN_GROUP = "base.group_system"


class OduBook(models.AbstractModel):
    """Documentation collector for the installed ``odu_*`` modules.

    The model stores nothing (no table): it reads the modules from disk and
    assembles their human-facing guides into books. Two audiences, two books:
    the **Userbook** (``doc/user_guide.md``, for end users) and the
    **Adminbook** (``doc/admin_guide.md``, for administrators -- settings and
    privileged tasks, gated behind the system-admin group). The technical
    layer (``doc/tech_spec.md``) is deliberately ignored -- it is meant for
    agents, not for humans.

    Both books are served in the reader's documentation language: a translated
    mirror under ``doc/i18n/<lang>/`` is preferred, falling back to the source
    file. The change timeline is not translated.
    """

    _name = "odu.book"
    _description = "User Book"

    @api.model
    def get_book(self):
        """Assemble the Userbook from every installed ``odu_*`` module.

        Served in the reader's documentation language (see :meth:`_doc_lang`),
        falling back to the source file per module.

        :return: ``{"pages": [{"id", "module", "title", "html"}, ...]}`` --
            one page per module (its ``doc/user_guide.md``).
        """
        return {"pages": self._collect_pages(GUIDE_FILENAME, self._doc_lang())}

    @api.model
    def get_admin_book(self):
        """Assemble the Adminbook (administrator guides). Admin-only.

        Same shape as :meth:`get_book` but reads ``doc/admin_guide.md`` and is
        restricted to members of the system-admin group, because admin guides
        describe privileged settings and tasks.

        :raise AccessError: when the caller is not a system administrator.
        :return: ``{"pages": [{"id", "module", "title", "html"}, ...]}``.
        """
        if not self.env.user.has_group(ADMIN_GROUP):
            raise AccessError(
                self.env._("Administrator access is required to read the Admin Book.")
            )
        return {"pages": self._collect_pages(ADMIN_GUIDE_FILENAME, self._doc_lang())}

    def _doc_lang(self):
        """Short documentation-language code for the current request.

        Derived from the context/user language (``en_US`` -> ``en``).
        Translations live under ``doc/i18n/<lang>/``; a missing one falls back
        to the source file. No dependency on ``LANG.md`` at runtime -- the read
        path is purely "translated-if-present, else source".
        """
        lang = self.env.context.get("lang") or self.env.user.lang or "en"
        return lang.split("_")[0]

    def _collect_pages(self, filename, lang):
        """Render ``doc/<filename>`` of every installed ``odu_*`` module.

        :param filename: the documentation file to read in each module's ``doc``.
        :param lang: the short documentation-language code to prefer.
        :return: ``[{"id", "module", "title", "html"}, ...]`` -- one entry per
            module that ships a readable ``filename``, ordered by module name.
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
            html = self._read_module_doc(module.name, filename, lang)
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
        return pages

    def _read_module_doc(self, module_name, filename, lang):
        """Read and render ``doc/<filename>`` of a module in ``lang`` (or None).

        Looks for a translation under ``doc/i18n/<lang>/<filename>`` first and
        falls back to the source file ``doc/<filename>``. The leading i18n
        provenance marker (if any) is stripped before rendering.
        """
        module_path = get_module_path(module_name)
        if not module_path:
            return None
        candidates = [
            os.path.join(module_path, DOC_DIRNAME, I18N_DIRNAME, lang, filename),
            os.path.join(module_path, DOC_DIRNAME, filename),
        ]
        for filepath in candidates:
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    raw = handle.read()
            except (OSError, UnicodeDecodeError):
                _logger.warning("odu_book: failed to read %s", filepath)
                return None
            return md_to_html(I18N_MARKER_RE.sub("", raw, count=1))
        return None

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
