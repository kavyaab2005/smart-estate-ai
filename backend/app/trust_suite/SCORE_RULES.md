# Trust Score Rules (Admin-Reviewed Document Trust)
Status: ACCEPTED by Kavya on 2026-10-20. Do not change a rule without her approval.
These rules must be written down before any scoring code. Code must follow this file.
## Rule 1 - Two separate numbers, never merged
- Automated part: of the cross-document consistency checks (owner name, survey number, area, registration details), how many passed.
- Admin-verified part: of the checklist items that apply to this property, how many the admin marked verified.
- The two parts are never averaged into one score. No label such as "safe" or "trusted" is attached.
## Rule 2 - A check that could not run counts as not passed
- If a document is missing, the checks that need it are counted in the total but not in "passed".
- Reason: a seller must not raise their score by leaving out the document that would show a problem.
- The seller sees these as "missing documents", not as failures.
## Rule 3 - Not-applicable items are removed from both sides
- If the admin marks an item not applicable, it leaves the total and the passed count.
- The admin must write a note when marking an item not applicable.
## Rule 4 - Integrity indicators do not change the score
- "Possible indicators - manual review recommended" (for example a missing page) go to the admin as findings only.
- They never raise or lower any number.
## Rule 5 - Approval does not require every item to be verified
- The admin must decide every applicable item: verified, or not verified with a note.
- Every critical finding must be acknowledged with a note.
- A listing may be approved with some items unverified, as long as the buyer clearly sees the actual count (for example "5 of 6 verified", never rounded up) and all required notes are recorded.
## Rule 6 - The score exists only for approved listings
- Buyers see it only after approval.
- Sellers see the review status and plain-language mismatches, not the score formula.
## Rule 7 - The disclaimer appears wherever a score or status appears
"This is a consistency and verification summary, not legal advice or proof of title. Consult an advocate before paying or registering."
## Other rules this feature must follow
- The system never approves or rejects by itself. Only an admin decides.
- The approving admin must not be the owner of the listing.
- Aadhaar and PAN are masked before storage, logging, and any LLM call.
- Wording: integrity checks are "possible indicators - manual review recommended", never "forged" or "fraud".
