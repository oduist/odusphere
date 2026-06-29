{
    "name": "Book",
    "summary": "Interactive user documentation assembled from the odu_* modules",
    "description": """
Book
====

The OduSphere technical module responsible for the built-in user
documentation. It scans every installed module with the ``odu_`` prefix,
collects the Markdown files from their ``doc`` folders and dynamically
assembles them into a single interactive "user book" right inside the UI.

No separate wiki -- the documentation lives next to the module code and is
shown to the user in a single click.
""",
    "version": "19.0.1.2.0",
    "category": "Tools",
    "author": "OduSphere",
    "license": "LGPL-3",
    "depends": ["odu_base", "web"],
    "data": [
        "views/odu_book_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odu_book/static/src/book/book.scss",
            "odu_book/static/src/book/book.js",
            "odu_book/static/src/book/book.xml",
            "odu_book/static/src/changes/changes.js",
            "odu_book/static/src/changes/changes.xml",
        ],
    },
    "application": True,
    "installable": True,
}
