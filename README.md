# GraphLens

GraphLens is a hackathon prototype for checking GraphQL object-level (BOLA) and property-level (BOPLA) authorization behavior against explicit policies. The repository currently contains its license and Python `.gitignore`; implementation work is expected to arrive through the feature branches below.

## Team ownership

| Teammate | Responsibility | Branch |
| --- | --- | --- |
| Aniket (`aniketgit-hub101`) | Engine and integration | `feature/engine` |
| Adeel (`adeelad726`) | GraphQL API | `feature/graphql-api` |
| Abhay (`abhyashukla16`) | Security tests | `feature/security-tests` |
| Akash | Test scenarios, QA coordination, documentation, and demo support | — |

## Shared branch workflow

- `main` is the stable integration branch. Keep it ready to run and demo.
- Each laptop uses its owner's feature branch. Do not commit feature work directly to `main`.
- Open a pull request from the feature branch into `main`; review and merge it before treating the work as integrated.
- Each person should clone the repository on their own laptop. Do not share a working directory between laptops.

## First setup on each laptop

Clone the same repository, then check out your assigned branch. The three feature branches are published in this repository.

```powershell
git clone https://github.com/aniketgit-hub101/GraphLens.git
cd GraphLens
```

Run the one command under your name only:

**Aniket:**

```powershell
git switch --track origin/feature/engine
```

**Adeel:**

```powershell
git switch --track origin/feature/graphql-api
```

**Abhay:**

```powershell
git switch --track origin/feature/security-tests
```

If you cloned before your branch was published, create it from `main` and publish it once. For example, Aniket runs:

```powershell
git switch --create feature/engine origin/main
git push --set-upstream origin feature/engine
```

Use your assigned branch name in place of `feature/engine`. Run the checkout command once per clone.

## Daily work

Before editing, switch to your branch and pull its latest commits:

```powershell
git switch feature/graphql-api
git pull --ff-only
```

Replace the branch name with your assignment. To bring in changes already merged to `main`:

```powershell
git fetch origin
git merge origin/main
```

Resolve any conflicts, then save and publish your work:

```powershell
git status --short
git add <files-you-changed>
git commit -m "Describe the change"
git push
```

Use `git status` before committing so you do not include another teammate's work by mistake.

## Pull requests and merging

Create a pull request with GitHub CLI (`gh`):

```powershell
gh pr create --base main --head feature/graphql-api --fill
```

Replace the head branch with your assignment. If `gh` is not installed, open the repository on GitHub, choose **Compare & pull request** for your branch, and set the base branch to `main`.

After review, the integrator can merge the pull request with:

```powershell
gh pr merge <PR_NUMBER> --squash
```

Or use **Merge pull request** on GitHub. After the merge, sync your clone:

```powershell
git switch main
git pull --ff-only origin main
git switch feature/graphql-api
git merge main
git push
```

Replace `feature/graphql-api` with your assignment. Keep the Python `.gitignore` in place; it already excludes bytecode, virtual environments, test caches, coverage output, and `.env` files.
