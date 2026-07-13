# Release Notes v1.4.1

## Overview
This release integrates **Word Confusion (Homophone / Contextual Typo) checking** directly into the Spelling Checker mode, using a distinct blue underline style and helper context menu actions.

## Key Changes
* **Contextual Typo Scanning**: Integrated a rule matching engine into `SpellcheckSubsystem` to identify common homophone confusion errors (like *its/it's*, *your/you're*, *their/there/they're*, *then/than*, *lose/loose*, *passed/past*).
* **Distinct Highlights**: Added a Catppuccin Blue underline (`word_confusion` tag) to visually segregate homophones from standard red spelling typos.
* **Context Menu Replacement**: Right-clicking a word confusion underline displays a replacement suggestion command, the grammatical rule explanation, and a session-level ignore action.
* **Settings Toggle**: Added a checkbox in the **Spelling Checker** tab of the settings panel to allow toggling word confusion scanning.
* **Rule Portability**: Stored homophone patterns in a local `word_confusions.json` database that is fully compiled, packaged, and customizable by the user.
