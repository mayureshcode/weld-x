# Observed development failures

1. Initial browser launch used `/usr/bin/chromium`, which did not exist. Read-only inspection found `/usr/local/bin/chromium`. Browser tests now accept `WELDX_CHROMIUM` rather than assuming a distro-specific path.
2. First browser workflow attempted revalidation directly from MAP, where that operation is intentionally disabled. Corrected the test to run detection again on the current configuration before revalidation. No execution gate or UI restriction was relaxed to make the test pass.
