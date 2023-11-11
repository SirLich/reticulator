# Explanation of Structure

Reticulator has gone through multiple iterations, as I push myself to learn new and terrible python programming patterns.
In it's current state, it comes in two parts:
 - 1) The core.py/reticulator.py parts, which are essentially a hellish stack of Decorators to generator the class reference
 - 2) The reticulator.pyi (generated with stubby.py) which hacks together type completion.

If you're editing Reticulator to adjust or create new classes, there is a 99% chance that all you need to do is gently edit the decorators
inside of reticulator.py

If you need to edit the decorators... sorry!

# TODO

Stubby generation is idiotic, but works. Mostly. It's missing support for ImplementSubResource and ImplementIdentifier.


# How to Release

 - Create all your changes
 - Run stubby.py
 - Create + Run Tests
 - Set version in `pyproject.toml`
 - Commit and push everything
 - Tag the repository: `git tag v0.0.13-beta`
 - Push git tags: `git push --tags`
 - Make new release on github, using the website
 - Create distribution `python -m build`
 - Push distribution: `twine upload .\dist\reticulator-v0.0.9-beta.tar.gz`