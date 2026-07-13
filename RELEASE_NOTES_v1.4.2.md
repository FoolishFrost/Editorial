# Release Notes v1.4.2

## Bug Fixes
* **Test Isolation (User Config Protection)**: Fixed an issue in `tests/test_settings_dialog.py` where executing the test suite would inadvertently delete the user's active `settings.json` file. The test suite now mocks and isolates the settings path to a secure temporary directory, ensuring local settings persist safely across builds.
