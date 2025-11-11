alias s := setup
alias t := test
alias p := pre_commit

# Install python dependencies
install:
  uv sync --all-groups --all-extras

# Install pre-commit hooks
pre_commit_setup:
  uv run pre-commit install

# Install python dependencies and pre-commit hooks
setup: install pre_commit_setup

# Run pre-commit
pre_commit:
 uv run pre-commit run -a

# Run pytest
test:
  uv run pytest tests
