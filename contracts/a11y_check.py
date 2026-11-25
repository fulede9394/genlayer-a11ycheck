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
    compare; it judges, and returns one line:

      VERDICT|REASON

    VERDICT is PASS, FAIL or INCONCLUSIVE, and REASON is one
    short sentence. The line is judged under
    prompt_non_comparative: two judgments are equivalent when
    they reach the same verdict word, whatever the reason says.
    Deterministic code then only parses the verdict word and
    stores the reason for the audit trail - it never second-
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

        def judge_audit() -> str:
            page = gl.nondet.web.render(page_url, mode="text")
            prompt = f"""Judge whether a live web page meets the stated accessibility criteria, using only the page below.

Accessibility criteria: {criteria}

Page content:
{page[:4000]}

Reply with exactly one line, nothing else, in this format:
VERDICT|REASON

VERDICT is one of:
PASS - the page meets all of the stated accessibility criteria
FAIL - the page violates at least one of the stated criteria
INCONCLUSIVE - the page could not be read, or it carries too little evidence to judge either way

REASON is one short sentence explaining the verdict. Judge what the page actually shows: a criterion about images can only pass if the page shows images that meet it, and a missing feature the criteria require is a failure, not a pass."""
            return gl.nondet.exec_prompt(prompt).strip()

        line = gl.eq_principle.prompt_non_comparative(
            judge_audit,
            principle="Two judgments are equivalent when they give the same verdict word: PASS, FAIL, or INCONCLUSIVE. The reason text does not matter.",
        )

        # Deterministic parsing only: the verdict word is taken
        # from the agreed line, the reason is stored for audit.
        first_sep = line.find("|")
        if first_sep == -1:
            verdict_word = line.strip().upper()
            reason = ""
        else:
            verdict_word = line[:first_sep].strip().upper()
            rest = line[first_sep + 1:]
            reason = rest.strip()
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
