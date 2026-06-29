/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BookApp } from "@odu_book/book/book";

/**
 * The "Admin Guide" client action: the Adminbook.
 * Identical two-pane viewer as the Userbook, but it pulls the administrator
 * guides (`doc/admin_guide.md`) from the admin-only endpoint. The endpoint
 * itself enforces the system-admin group server-side.
 */
export class AdminBookApp extends BookApp {
    static endpoint = "/odu_book/admin";
}

registry.category("actions").add("odu_book.admin", AdminBookApp);
