# Base — Administration

This page is for administrators. The **Base** module is the OduSphere governance
core; the tasks and settings below require **Settings** (`base.group_system`)
access, and this page is itself visible only to Settings administrators.

## Contact Requests inbox

The starter website ships a public **contact form**. Every submission is stored
and listed in **Settings → Contact Requests**.

- Open **Settings → Contact Requests** to read incoming messages, newest first.
  Each entry shows when it was received, the sender's name and email, and the
  message body.
- Use the **Handled** toggle to mark a request as processed once you have dealt
  with it. The list opens filtered to **Unhandled** requests; clear the filter to
  see everything.
- Submissions arrive through the public `POST /api/contact` endpoint, which is
  open to anyone (no login). Two light spam guards are built in: a hidden honeypot
  field and basic validation. There is **no** captcha or rate limiting — if a
  sphere is publicly exposed, expect occasional spam and triage it with the
  Handled toggle.

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
