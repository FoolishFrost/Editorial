Editorial v1.2.3
================

Simple Change Notes
-------------------
- Fixed cliché variation matching for inserts inside latter parts of a phrase (e.g. matching *I avoided the subject like the proverbial plague* where *proverbial* is inserted between *the* and *plague*).
- Allows up to 2 optional words between any consecutive pair of lemmas inside a cliché phrase, while restricting them to prevent sentence boundary crossing.

User-Facing Changes
-------------------
- Cliches mode highlights are now fully capable of matching insertions in the middle of standard phrase segments (e.g. *like the proverbial plague* or *skating on very thin ice*).

Fixes
-----
- Refactored `_get_cliches_matcher_patterns` to insert optional wildcard check blocks between all consecutive tokens in a phrase, rather than only after the first token.
