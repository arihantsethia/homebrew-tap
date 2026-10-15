# Homebrew Tap

Homebrew formulae for tools maintained by Arihant Sethia.

## Clipport

Install the latest tested stable release:

```sh
brew install arihantsethia/tap/clipport
clipctl onboard
```

Onboarding starts Clipport. Open a new SSH session after onboarding. Run
`clipctl doctor` in a separate local Mac pane if you need to check the install.

Update an existing Homebrew install:

```sh
brew update
brew upgrade arihantsethia/tap/clipport
clipctl restart
```

Use Homebrew for updates; `clipctl update` is for manual/source installs.

To opt in to unreleased development changes:

```sh
brew install --HEAD arihantsethia/tap/clipport
# Refresh an existing HEAD install:
brew upgrade --fetch-HEAD arihantsethia/tap/clipport
clipctl restart
```

## Automatic stable updates

[Update Clipport](https://github.com/arihantsethia/homebrew-tap/actions/workflows/update-clipport.yml)
checks the latest published Clipport release hourly, at minute 17, and can also
be run manually. It ignores drafts/prereleases and never downgrades or replaces
an existing version's checksum. Stable installs keep a versioned URL and SHA-256.

Before updating the formula, the workflow verifies that the release commit is
on Clipport's `main`, runs source tests and vet on macOS, then builds and tests
the candidate formula with Homebrew. An isolated writer rechecks the release
and original formula before committing only the URL and checksum. No upstream
release code runs with a write-enabled token. Each repository uses its own
built-in `GITHUB_TOKEN`; no cross-repository secret is required.

GitHub may delay scheduled runs and disables public-repository schedules after
60 days without repository activity. Check Actions, re-enable the workflow if
needed, and use **Run workflow** to recover or get an update sooner. A changed
formula, moved release tag, failed test or protected-branch push fails safely;
resolve it and rerun. The updater never force-pushes or bypasses branch rules.

Clipport and release instructions: <https://github.com/arihantsethia/clipport>
