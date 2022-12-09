

# How to Release

 - Create all your changes
 - Create + Run Tests
 - Set version in `pyproject.toml`
 - Commit and push everything
 - Tag the repository: `git tag v0.0.13-beta`
 - Push git tags: `git push --tags`
 - Make new release on github, using the website
 - Create distribution `python -m build`
 - Push distribution: `twine upload .\dist\reticulator-v0.0.9-beta.tar.gz`