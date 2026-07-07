Editorial v1.2.2
================

Simple Change Notes
-------------------
- Replaced the direct literal cliché phrase matcher with a spaCy-based lemmatizer Matcher to allow variations of cliché idioms.
- Supports grammatical inflections and verb tenses (e.g. matching *avoided*, *avoiding*, *avoids* for the cliché *avoid like the plague*).
- Allows intermediate words, pronouns, and names between the key parts of the cliché phrase (e.g. matching *avoided John like the plague* or *avoiding him completely like the plague* with up to 3 optional words).
- Created a new unit test suite to verify cliché variations matching robustness.

User-Facing Changes
-------------------
- Cliches mode highlights are now significantly more useful and pick up natural sentence structures (e.g. *threw him under the bus* instead of only matching *throw under the bus*).

Fixes
-----
- Replaced rigid regex checks with spaCy's lemmatized matching, eliminating missed warnings when inflected verbs or pronouns are used inside common idioms.
- Restored redundancies regex dictionary compilation on startup.
