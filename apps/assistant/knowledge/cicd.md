# CI/CD

## Step failed: Process completed with exit code
Matches: `process completed with exit code`, `error: process completed`
Tool: GitHub Actions

**Cause.** A command in the step returned a non-zero exit code. This line is only the summary, the real error is a few lines above it.

**Fix.** Scroll up to the first error in the step's log. Re-run the job with debug logging if the output is unclear.

```sh
gh run view <run-id> --log-failed
gh run rerun <run-id> --debug
```

## Resource not accessible by integration
Matches: `resource not accessible by integration`
Tool: GitHub Actions

**Cause.** The workflow's GITHUB_TOKEN does not have the permission it needs (for example to comment on a PR or push a package).

**Fix.** Add the needed scope under permissions in the workflow, for example pull-requests: write or packages: write.

```sh
gh api repos/<owner>/<repo>/actions/permissions
```

## Secrets are empty in pull requests from forks
Matches: `pull request from a fork`, `secrets are not passed`, `pull_request_target`
Tool: GitHub Actions

**Cause.** For security, GitHub does not pass secrets to workflows triggered by pull requests from forks.

**Fix.** Skip the steps that need secrets on fork PRs. Do not switch to pull_request_target with a checkout of the PR code, which lets the PR read your secrets.

```sh
gh secret list
```

## GitHub API rate limit exceeded
Matches: `api rate limit exceeded`, `secondary rate limit`
Tool: GitHub Actions

**Cause.** Too many API calls, often from unauthenticated tool downloads or many parallel jobs.

**Fix.** Authenticate calls with GITHUB_TOKEN, cache downloads, and reduce parallel polling.

```sh
gh api rate_limit
```

## Runner out of disk space
Matches: `system.io.ioexception: no space left on device`, `you are running out of disk space`
Tool: GitHub Actions

**Cause.** Hosted runners have limited free disk, and large Docker builds or caches fill it.

**Fix.** Remove unused preinstalled toolchains early in the job, prune Docker, or use a larger runner.

```sh
df -h
docker system prune -af
```

## Cache not found for input keys
Matches: `cache not found for input keys`
Tool: GitHub Actions

**Cause.** No cache matches the key, which is normal on the first run or after the lock file changed.

**Fix.** Nothing is broken. Add restore-keys so partial matches are used, and make sure the key hashes the right lock file.

```sh
gh cache list
```

## GitLab: job stuck, no runners online
Matches: `this job is stuck because`, `no active runners`, `don't have any active runners online`
Tool: GitLab CI

**Cause.** No runner is online with tags that match the job, or the project has no runners enabled.

**Fix.** Check the job's tags against your runners, or enable shared runners for the project.

```sh
gitlab-runner list
gitlab-runner verify
```

## GitLab: cannot connect to Docker in docker
Matches: `tcp://docker:2375`, `tcp://docker:2376`, `docker:dind`
Tool: GitLab CI

**Cause.** The job uses docker commands without the docker:dind service, or the TLS settings between the job and the service do not match.

**Fix.** Add the docker:dind service and set DOCKER_HOST and DOCKER_TLS_CERTDIR consistently (TLS on 2376, or TLS off on 2375).

```sh
docker info
```

## GitLab: Job failed with exit code
Matches: `error: job failed: exit code`, `job failed: exit status`
Tool: GitLab CI

**Cause.** A script line returned non-zero. The real error is above this summary line.

**Fix.** Read the job log from the first error. Run the same commands locally in the job's image to reproduce.

```sh
docker run --rm -it <job-image> sh
```

## Jenkins: waiting for next available executor
Matches: `waiting for next available executor`, `all nodes of label`, `agent is offline`
Tool: Jenkins

**Cause.** No agent with the required label is online or free: the agent disconnected, its disk is full, or the cloud plugin cannot launch new agents.

**Fix.** Check the agent's status and log in Manage Jenkins, Nodes, then reconnect it or fix its launch settings.

```sh
java -jar jenkins-cli.jar -s <jenkins-url> -auth <user>:<token> list-jobs
```

## Jenkins: Java heap space
Matches: `java.lang.outofmemoryerror: java heap space`, `gc overhead limit exceeded`
Tool: Jenkins

**Cause.** The Jenkins controller or a build ran out of JVM heap, often from large logs, many builds kept, or heavy plugins.

**Fix.** Raise -Xmx for the controller, discard old builds, and move heavy work to agents.

```sh
jcmd <pid> GC.heap_info
```

## Jenkins: scripts not permitted
Matches: `scripts not permitted to use`, `rejectedaccessexception`, `scriptapproval`
Tool: Jenkins

**Cause.** The Groovy sandbox blocked a method call in the pipeline.

**Fix.** Use a pipeline step that already exists, or have an admin approve the signature in In-process Script Approval.


## Jenkins: credentials not found
Matches: `could not find credentials entry with id`, `credentialsnotfound`
Tool: Jenkins

**Cause.** The credentials ID in the pipeline does not exist, or it lives in a folder the job cannot see.

**Fix.** Create the credential with that exact ID in the right scope (global or the job's folder).

