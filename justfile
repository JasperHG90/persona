alias s := setup
alias t := test
alias p := prek

# Install python dependencies
install:
  uv sync --all-groups --all-extras

# Install pre-commit hooks
prek_setup:
  uv run prek install

# Install python dependencies and pre-commit hooks
setup: install prek_setup

# Run pre-commit
prek:
 uv run prek run -a

# Run pytest
test:
  uv run pytest tests
