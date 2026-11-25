# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class A11yCheck(gl.Contract):
    """
    A11yCheck - does this page meet the stated accessibility criteria?

    Accessibility rules are written as checklists - every image
    needs alt text, every form input needs a label, text needs
    enough contrast - but checking a page against its checklist
    is manual, slow, and easy to fake with a screenshot of a
    different page. Someone has to actually read the live page
    and judge it against the criteria, and that judgment is
    subjective: it needs eyes on the page, not a string
    comparison.

    This contract turns "this page is accessible" into a
    checkable on-chain record. The submitter fixes two things
    at submission time: the page URL and the accessibility
    criteria the page is supposed to meet. Validators then read
    the live page and judge it against those criteria.

    Consensus follows the judgment pattern, not the extraction
    pattern. The LLM does not extract a field for code to
    compare; it judges. Two calls, both proven in earlier
    contracts: the verdict word is judged under strict_eq (the
    function normalises its own output to one canonical word,
    so exact agreement is meaningful), and the one-sentence
    reason is judged under prompt_comparative with the principle
    that two reasons are equivalent when they explain the same
    verdict for the same reason. Deterministic code then only
    stores what the validators agreed on - it never second-
    guesses the judgment.

    That is the whole point, and what makes this contract a
    different shape from a status oracle: the verdict is a
    judgment against submitter-defined criteria, the evidence
    is a live page read as a human would read it, and there is
    no field for deterministic code to compare. A page that
    violates even one stated criterion is FAIL, not MISMATCH;
    a page that cannot be read is INCONCLUSIVE, not UNKNOWN.
    """

    audit_count: u256
    page_urls: TreeMap[u256, str]
    criteria_texts: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    reasons: TreeMap[u256, str]

    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"

    def __init__(self):
        self.audit_count = u256(0)

    @gl.public.write
    def submit_audit(
        self,
        page_url: str,
        criteria: str,
    ) -> int:
        page_url = page_url.strip()
        criteria = criteria.strip()

        assert page_url.startswith("https://"), "page URL must be https"
        assert len(page_url) <= 300, "page URL too long"
        assert len(criteria) >= 10, "criteria too short"
        assert len(criteria) <= 1000, "criteria too long"

        aid = self.audit_count
        self.page_urls[aid] = page_url
        self.criteria_texts[aid] = criteria
        self.statuses[aid] = self.PENDING
        self.reasons[aid] = ""
        self.audit_count = aid + u256(1)
        return int(aid)

    @gl.public.write
    def resolve_audit(self, audit_id: int) -> str:
        aid = u256(audit_id)
        assert aid in self.statuses, "unknown audit"
        assert self.statuses[aid] == self.PENDING, "audit already resolved"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        page_url = self.page_urls[aid]
        criteria = self.criteria_texts[aid]

        def judge_verdict() -> str:
            page = gl.nondet.web.render(page_url, mode="text")
            prompt = f"""Judge whether a live web page meets the stated accessibility criteria, using only the page below.

Accessibility criteria: {criteria}

Page content:
{page[:4000]}

Reply with exactly one word, nothing else:
PASS - the page meets all of the stated accessibility criteria
FAIL - the page violates at least one of the stated criteria
INCONCLUSIVE - the page could not be read, or it carries too little evidence to judge either way

Judge what the page actually shows: a criterion about images can only pass if the page shows images that meet it, and a missing feature the criteria require is a failure, not a pass."""
            raw = gl.nondet.exec_prompt(prompt).strip().upper()
            if "PASS" in raw:
                return "PASS"
            if "FAIL" in raw:
                return "FAIL"
            return "INCONCLUSIVE"

        verdict_word = gl.eq_principle.strict_eq(judge_verdict)

        def judge_reason() -> str:
            page = gl.nondet.web.render(page_url, mode="text")
            prompt = f"""Explain in one short sentence why the page received the verdict below, using only the page content.

Accessibility criteria: {criteria}
Verdict: {verdict_word}

Page content:
{page[:4000]}

Reply with one short sentence, nothing else."""
            return gl.nondet.exec_prompt(prompt).strip()

        reason = gl.eq_principle.prompt_comparative(
            judge_reason,
            principle="Two reasons are equivalent when they explain the same verdict for the same reason. Different wording does not make them different.",
        )

        self.reasons[aid] = reason

        if verdict_word == "PASS":
            final = self.PASS
        elif verdict_word == "FAIL":
            final = self.FAIL
        else:
            final = self.INCONCLUSIVE

        self.statuses[aid] = final
        return final

    @gl.public.view
    def get_audit(self, audit_id: int) -> typing.Any:
        aid = u256(audit_id)
        assert aid in self.statuses, "unknown audit"
        return {
            "id": audit_id,
            "page_url": self.page_urls[aid],
            "criteria": self.criteria_texts[aid],
            "status": self.statuses[aid],
            "reason": self.reasons[aid],
        }

    @gl.public.view
    def get_status(self, audit_id: int) -> str:
        aid = u256(audit_id)
        assert aid in self.statuses, "unknown audit"
        return self.statuses[aid]

    @gl.public.view
    def is_pass(self, audit_id: int) -> bool:
        aid = u256(audit_id)
        assert aid in self.statuses, "unknown audit"
        return self.statuses[aid] == self.PASS

    @gl.public.view
    def get_audit_count(self) -> int:
        return int(self.audit_count)
