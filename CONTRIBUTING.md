# Setup

1. In order to contribute you will need to clone/fork the repo and install the requirements locally.

```
pip install .
```

2. Install [pre-commit](https://pre-commit.com/).

```
pip install pre-commit
pre-commit install
```

# Workflow
1. Create and checkout new feature branch for your work.

2. Make changes and add awesome code!

3. Run code-style requirement checks using pre-commit and fix all documentation and typing issues shown in the output.

```
pre-commit run --all-files -v
```

5. Run tests locally.

5. Re-stage the files after fixing the errors and commit. When you commit, `pre-commit` will run once again but only on the changed files

6. Push to remote. Create a PR if your feature is complete.


## Code Styling

We use `flake8` and `black` for code formatting.
