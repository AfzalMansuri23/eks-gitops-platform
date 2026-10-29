# Git

## Host key verification failed
Matches: `host key verification failed`, `the authenticity of host`

**Cause.** The server's SSH host key is not in known_hosts, which is normal on a fresh CI runner or container. If it was there and changed, it may be a real security problem.

**Fix.** Add the host's key to known_hosts from a trusted source. Investigate if a key that used to work suddenly changed.

```sh
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

## Permission denied (publickey) from GitHub or GitLab
Matches: `git@github.com: permission denied (publickey)`, `git@gitlab.com: permission denied`, `could not read from remote repository`

**Cause.** No SSH key is loaded, the key is not added to your account, or the key has no access to that repo.

**Fix.** Test the connection, load the key into the agent, and add the public key to your account.

```sh
ssh -T git@github.com
ssh-add -l
ssh-add ~/.ssh/id_ed25519
```

## Push rejected: non-fast-forward
Matches: `non-fast-forward`, `failed to push some refs`, `updates were rejected because the tip`

**Cause.** The remote branch has commits you do not have locally.

**Fix.** Pull with rebase, resolve any conflicts, then push. Do not force-push shared branches.

```sh
git pull --rebase
git push
```

## Merge conflict
Matches: `conflict (content)`, `automatic merge failed`, `fix conflicts and then commit`

**Cause.** The same lines changed on both branches.

**Fix.** Edit the files to keep the right version, mark them resolved, and continue.

```sh
git status
git add <file>
git rebase --continue
```

## File too large for GitHub
Matches: `gh001`, `exceeds github's file size limit`, `large files detected`

**Cause.** A file over 100 MB is in the history, even if a later commit deleted it.

**Fix.** Remove it from history (git filter-repo) and use Git LFS for large binaries.

```sh
git filter-repo --path <file> --invert-paths
git lfs track "*.<ext>"
```

## Password authentication removed
Matches: `support for password authentication was removed`, `authentication failed for`

**Cause.** GitHub no longer accepts account passwords over HTTPS.

**Fix.** Use a personal access token or the GitHub CLI credential helper, or switch the remote to SSH.

```sh
gh auth login
git remote set-url origin git@github.com:<owner>/<repo>.git
```

## Detached HEAD
Matches: `detached head`, `you are in 'detached head' state`

**Cause.** You checked out a commit or tag rather than a branch, so new commits are not on any branch.

**Fix.** Create a branch from where you are to keep the work.

```sh
git switch -c <new-branch>
```

## LF will be replaced by CRLF
Matches: `lf will be replaced by crlf`, `crlf will be replaced by lf`

**Cause.** Git is converting line endings between Windows and Linux. Shell scripts with CRLF break on Linux.

**Fix.** Add a .gitattributes that keeps LF in the repo, then renormalize.

```sh
echo "* text=auto eol=lf" >> .gitattributes
git add --renormalize .
```
