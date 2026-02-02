module.exports = {
  "**/*.py": ["uv run ruff check --fix", "uv run mypy"],
  "tests/**/*.py": ["uv run pytest -q --disable-warnings --maxfail=1"],
  "website/client/**/*.{ts,tsx}": [
    "npm run lint:file --prefix website/client -- --fix",
    "npm run test --prefix website/client -- --run --related",
  ],
  "website/client/**/*.{ts,tsx,js,jsx}": () =>
    "npm run typecheck --prefix website/client",
};