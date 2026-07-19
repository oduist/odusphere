# Base — Administration

This page is for administrators. The **Base** module is the OduSphere governance
core; the tasks and settings below require **Settings** (`base.group_system`)
access, and this page is itself visible only to Settings administrators.

## Contact Requests inbox

The starter website ships a public **contact form**. Every submission is stored
and listed in **Settings → Contact Requests**.

- Open **Settings → Contact Requests** to read incoming messages, newest first.
  Each entry shows when it was received, the sender's name and email, the source
  **IP address**, and the message body.
- Use the **Handled** toggle to mark a request as processed once you have dealt
  with it. The list opens filtered to **Unhandled** requests; clear the filter to
  see everything.
- Submissions arrive through the public `POST /api/contact` endpoint, which is
  open to anyone (no login). It has three built-in abuse guards: a hidden honeypot
  field, a request-size cap (oversized bodies are rejected outright), and a
  **per-IP rate limit** (see below). There is no captcha — if a sphere is publicly
  exposed, expect occasional spam and triage it with the Handled toggle.

## Contact-form rate limit

The endpoint throttles repeated submissions from the same IP address. By default
it accepts at most **10 submissions per 10 minutes per IP**; further attempts get
an HTTP 429 and are not stored. Two system parameters tune it (developer mode →
**Settings → Technical → System Parameters**):

| Parameter | Default | Meaning |
|---|---|---|
| `odu_base.contact_rate_limit_max` | `10` | Max stored submissions per IP within the window. Set to `0` to **disable** the limit. |
| `odu_base.contact_rate_limit_window_minutes` | `10` | Length of the rolling window, in minutes. |

**Important — put Odoo behind the gateway in `proxy_mode`.** The limit keys on the
caller's IP, taken from the request's remote address. When Odoo runs behind the
Caddy gateway (the standard OduSphere layout), enable `proxy_mode = True` in
`odoo.conf` so Odoo reads the real visitor's IP from the proxy headers. Without
it, every request appears to come from the gateway's single IP, so the limit
becomes **global** rather than per-visitor (all visitors share one quota). If you
cannot enable `proxy_mode`, raise the limit or set the max to `0` to disable it,
and rely on the gateway and honeypot instead.

The source IP is stored on each request (visible on the form, administrators
only) so you can identify and, if needed, block abusive sources at the gateway.

## Allowing an extra framework module

By default only `odu_`-prefixed modules plus the framework essentials (`base`,
`web`, `mail`) may be installed. In rare cases a legitimate technical framework
module is needed as a building block. An administrator can extend the allowed list
without changing any code:

1. Enable developer mode.
2. Go to **Settings → Technical → System Parameters**.
3. Create (or edit) the parameter **`odu_base.allowed_non_odu_modules`**.
4. Set its value to a comma-separated list of the extra module names to allow, for
   example: `web, base, your_extra_module`.

The built-in framework modules (`base`, `web`, `mail`) are always allowed, even if
they are not listed in the parameter. **You only ever list a module you allow
directly — its own dependencies are allowed automatically.** For example allowing
`mail` also permits the `bus` and `base_setup` modules it is built on, so you never
have to hunt down and list transitive framework dependencies yourself. This
auto-allow applies only to the modules you explicitly allow; it never opens the
door to business apps.
