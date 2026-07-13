# Release Notes v1.4.5

## Bug Fixes
* **Participle Adjective Check Refinement (`its_participle`)**: Refined the regex pattern for catchable `its` typos preceding `-ing` participles. The pattern now checks context so that it does not flag possessive adjectives modifying nouns (such as *"its growling maw"*, *"its glowing eyes"*, or *"its shining armor"*). It selectively flags `its` only when followed by a participle ending a clause/sentence, or when followed by prepositions, pronouns, or common verbal adverbs.
