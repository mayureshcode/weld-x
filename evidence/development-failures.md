# Observed development failures

1. Initial browser launch used `/usr/bin/chromium`, which did not exist. Read-only inspection found `/usr/local/bin/chromium`. Browser tests now accept `WELDX_CHROMIUM` rather than assuming a distro-specific path.
2. First browser workflow attempted revalidation directly from MAP, where that operation is intentionally disabled. Corrected the test to run detection again on the current configuration before revalidation. No execution gate or UI restriction was relaxed to make the test pass.

3. GitHub batch publication including the CI workflow was rejected with HTTP 403. Isolating workflow configuration was decisive: the same code/evidence batch without it succeeded. The workflow remains local/archive only; docs now explicitly distinguish this from published source and from a verified CI run.
