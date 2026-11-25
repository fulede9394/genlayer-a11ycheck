# A11yCheck — Web Accessibility Criteria Audit Primitive

A standalone Intelligent Contract that attests whether a live
web page meets stated accessibility criteria, instead of
trusting a badge or a screenshot.

## Deployed

- Network: StudioNet (GenLayer Studio)
- Contract: TBD
- Deploy tx: TBD
- Explorer: TBD
- Studio: TBD

## Why this exists

Accessibility rules are written as checklists — every image
needs alt text, every form input needs a label, text needs
enough contrast — but checking a page against its checklist
is manual, slow, and easy to fake with a screenshot of a
different page. Someone has to actually read the live page
and judge it against the criteria. A11yCheck turns "this page
is accessible" into a reusable primitive with a visible audit
trail.

1. `submit_audit(page_url, criteria)` — the page URL and the
   accessibility criteria are fixed at submission time.
2. `resolve_audit(audit_id)` — validators read the live page
   and judge it against the criteria. The LLM judges; it does
   not extract a field for code to compare.
3. The verdict is `PASS`, `FAIL` or `INCONCLUSIVE`, with a
   one-sentence reason stored on-chain for audit.

## Judgment, not extraction

The LLM judges; it does not extract a field for code to
compare. Two calls, both proven in earlier contracts: the
verdict word is judged under strict_eq (the function
normalises its own output to one canonical word), and the
one-sentence reason is judged under prompt_comparative with
the principle that two reasons are equivalent when they
explain the same verdict for the same reason. Deterministic
code then only stores what the validators agreed on — it
never second-guesses the judgment. A page that violates even
one stated criterion is `FAIL`, not a mismatch; a page that
cannot be read is `INCONCLUSIVE`, not unknown.

## State design

One-way state machine per audit:
`PENDING -> PASS | FAIL | INCONCLUSIVE`

- `PASS`: the page meets all of the stated accessibility
  criteria.
- `FAIL`: the page violates at least one of the stated
  criteria. A missing feature the criteria require is a
  failure, not a pass.
- `INCONCLUSIVE`: the page could not be read, or it carries
  too little evidence to judge either way.

Because the reason is stored, anyone can see *why* the
verdict came out that way, instead of getting a single
opaque word.

## Try it in GenLayer Studio

1. Paste `contracts/a11y_check.py` into Studio and deploy (no args).
2. `submit_audit` with, for example:
   - page_url: `https://example.com`
   - criteria: `The page has no image without alt text and no form input without a label`
3. `resolve_audit(0)`, then `get_audit(0)` — expect `PASS`
   with a reason noting the page has no images or inputs to
   violate the criteria.

## Tests

See `tests/test_cases.md` (9 cases): input validation, unknown /
double resolution, and all three terminal states.
