# Reticulator Tests

Reticulator has comprehensive, if messy test coverage. In general, the `content` folder contains test-cases, and the `out` directory is used as the save location, to avoid dirtying test assets.

## Running Tests

Reticulator tests must be run from within the `tests` directory. So, to run tests:
 - `cd tests`
 - `python ./tests.py`

All tests should pass.

## Adding Tests

To add a new test, create a new class, following the style of Pythons `unittest` library. Every test should be defined in it's own function, with a descriptive name.

Two helpful methods:
 - `get_packs` will return a project-linked RP and BP, with the contents of `contents`.
 - `save_and_return_packs` will save the packs into `out`, then re-read them from that location, allowing you to test the results of `save()` calls non-destructively.