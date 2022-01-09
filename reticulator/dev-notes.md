# How to Release

 - Create all your changes
 - Create + Run Tests
 <!-- - Run `generator.py`  -->
 - Set version in `setup.py`
 - Commit and push everything
 - Tag the repository: `git tag -a v0.0.9-beta`
 - Push git tags: `git push --tags`
 - Make new release on github, using the website
 - Create distribution `python setup.py sdist`
 - Push distribution: `twine upload .\dist\reticulator-v0.0.9-beta.tar.gz`
 