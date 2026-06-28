# -*- coding: utf-8 -*-
import logging
import os

from odoo import api, models
from odoo.modules.module import get_module_path

from .markdown import md_to_html

_logger = logging.getLogger(__name__)

#: Folder inside a module that holds the user documentation.
DOC_DIRNAME = "doc"
#: File name of the user guide (see CLAUDE.md, two-layer documentation).
GUIDE_FILENAME = "user_guide.md"
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
