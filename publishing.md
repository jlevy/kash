## Publishing Releases

This is how to publish a Python package to [**PyPI**](https://pypi.org/) from GitHub
Actions, when using the
[**simple-modern-uv**](https://github.com/jlevy/simple-modern-uv) template.

Thanks to
[the dynamic versioning plugin](https://github.com/ninoseki/uv-dynamic-versioning/) and
the
[`publish.yml` workflow](https://github.com/jlevy/simple-modern-uv/blob/main/template/.github/workflows/publish.yml),
you can simply create tagged releases (using standard format for the tag name, e.g.
`v0.1.0`) on GitHub and the tag will trigger a release build, which then uploads it to
PyPI.

### How to Publish the First Time

This part is a little confusing the first time.
Here is the simplest way to do it.
For the purposes of this example replace OWNER and PROJECT with the right values.

1. **Get a PyPI account** at [pypi.org](https://pypi.org/) and sign in.

2. **Pick a name for the project** that isn’t already taken.

   - Go to `https://pypi.org/project/PROJECT` to see if another project with that name
     already exits.

   - If needed, update your `pyproject.yml` with the correct name.

3. **Authorize** your repository to publish to PyPI:

   - Go to [the publishing settings page](https://pypi.org/manage/account/publishing/).

   - Find “Trusted Publisher Management” and register your GitHub repo as a new
     “pending” trusted publisher

   - Enter the project name, repo owner, repo name, and `publish.yml` as the workflow
     name. (You can leave the “environment name” field blank.)

4. **Create a release** on GitHub:

   - Commit code and make sure it’s running correctly.

   - Go to your GitHub project page, then click on Actions tab.

   - Confirm all tests are passing in the last CI workflow.
     (If you want, you can even publish this template when it’s empty as just a stub
     project, to try all this out.)

   - Go to your GitHub project page, click on Releases.

   - Fill in the tag and the release name.
     Select to create a new tag, and pick a version.
     A good option is `v0.1.0`. (It’s wise to have it start with a `v`.)

   - Submit to create the release.

5. **Confirm it publishes to PyPI**

   - Watch for the release workflow in the GitHub Actions tab.

   - If it succeeds, you should see it appear at `https://pypi.org/project/PROJECT`.

### How to Publish Subsequent Releases

Just create a new release.
You can do this via the GitHub CLI or the web UI.

#### Using GitHub CLI (Recommended for Agents)

Follow these steps in order:

**Step 1: Check the latest release to determine the next version**

```shell
gh release list --limit 5
```

Determine the next version using [semantic versioning](https://semver.org/):
- Patch (0.2.0 → 0.2.1): Bug fixes, minor changes
- Minor (0.2.1 → 0.3.0): New features, backward compatible
- Major (0.3.0 → 1.0.0): Breaking changes

**Step 2: Ensure CI is passing on the main branch**

```shell
gh run list --branch main --limit 3
```

Do not proceed if CI is failing.

**Step 3: Review commits since the last release**

```shell
gh api repos/:owner/:repo/compare/LAST_VERSION...HEAD --jq '.commits[].commit.message'
```

Replace `LAST_VERSION` with the tag from step 1 (e.g., `v0.2.0`).

**Step 4: Write release notes**

Run `tbd guidelines release-notes-guidelines` to load the guidelines.
Then write notes that:
- Describe the aggregate delta from the previous release
- Consolidate related changes under logical headings
- Explain impact from the user’s perspective
- Omit internal-only changes

**Step 5: Create the release**

```shell
gh release create vX.Y.Z --title "vX.Y.Z" --notes "RELEASE_NOTES_HERE"
```

For multi-line notes, use `--notes-file` with a temp file instead.

**Step 6: Confirm the publish workflow succeeds**

```shell
gh run list --workflow=publish.yml --limit 1
gh run watch
```

Wait for the workflow to complete successfully before reporting done.

#### Using GitHub Web UI

1. Go to your GitHub project page, click on Releases.
2. Click “Draft a new release”.
3. Select “Create a new tag”, enter the version (e.g., `v0.2.0`).
4. Fill in the release title and notes.
5. Click “Publish release”.

#### After Creating a Release

1. Watch for the publish workflow in GitHub Actions.
2. Confirm the new version appears at `https://pypi.org/project/PROJECT`.

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
