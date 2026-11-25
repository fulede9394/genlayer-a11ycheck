# A11yCheck — test cases

Run manually in GenLayer Studio after deploying
`contracts/a11y_check.py` (no constructor args).

## Deterministic validation

1. `submit_audit` with a non-https page URL — expect rejection
   ("page URL must be https").
2. `submit_audit` with criteria shorter than 10 characters —
   expect rejection ("criteria too short").
3. `submit_audit("https://example.com", "The page has no image without alt text and no form input without a label")` — expect
   audit id `0`, and `get_audit_count()` returns `1`.
4. `get_status(99)` on an unknown audit — expect rejection
   ("unknown audit").
5. `resolve_audit(99)` on an unknown audit — expect rejection
   ("unknown audit").

## Non-deterministic verdict paths

6. Resolve the example.com audit from case 3 — the page is
   text only, with no images and no form inputs, so nothing
   on it can violate the criteria. Expect `PASS`, and
   `is_pass(0)` returns `true`.
7. Submit example.com again with criteria the page cannot meet
   — criteria `The page contains at least one image with
   descriptive alt text` — and resolve it. The page has no
   images at all, so a required feature is missing: expect
   `FAIL`.
8. Submit a page URL that does not exist — for example
   `https://example.com/this-page-does-not-exist-12345` with
   criteria `The page has no image without alt text` — and
   resolve it. The page carries no usable evidence, so expect
   `INCONCLUSIVE`.
9. Resolve an already-resolved audit a second time — expect
   rejection ("audit already resolved"). A PASS that is later
   broken by a redesign stays PASS in its own record; submit
   a new audit for a fresh check.
