# Docker

## Docker: no space left on device
Matches: `/var/lib/docker`, `failed to register layer`, `docker system df`

**Cause.** Old images, stopped containers, build cache and volumes have filled the disk that holds /var/lib/docker.

**Fix.** See what uses the space, then prune what you no longer need. Prune with -a removes all unused images, so it is slower to rebuild afterwards.

```sh
docker system df
df -h /var/lib/docker
docker system prune -a
```

## Port is already allocated
Matches: `port is already allocated`, `bind: address already in use`, `ports are not available`

**Cause.** Another container or process on the host already listens on that port.

**Fix.** Find what holds the port, stop it, or map the container to a different host port.

```sh
docker ps --filter publish=<port>
ss -ltnp | grep :<port>
```

## Permission denied on the Docker socket
Matches: `permission denied while trying to connect to the docker daemon socket`, `/var/run/docker.sock`

**Cause.** Your user is not in the docker group, so it cannot talk to the daemon.

**Fix.** Add the user to the docker group and start a new login session. Membership in this group is equivalent to root on the host.

```sh
sudo usermod -aG docker $USER
newgrp docker
```

## Cannot connect to the Docker daemon
Matches: `cannot connect to the docker daemon`, `is the docker daemon running`

**Cause.** The Docker service is stopped, crashed, or DOCKER_HOST points somewhere else. On Windows and macOS, Docker Desktop is not running.

**Fix.** Start the daemon and check its logs if it does not stay up.

```sh
sudo systemctl status docker
sudo systemctl start docker
journalctl -u docker --since "10 min ago" --no-pager
```

## exec format error (wrong CPU architecture)
Matches: `exec format error`, `no matching manifest for linux/`, `does not match the detected host platform`

**Cause.** The image was built for a different CPU architecture, for example arm64 on an Apple Silicon laptop running on amd64 servers.

**Fix.** Build multi-platform images with buildx, or build for the platform you deploy to.

```sh
docker image inspect <image> --format '{{.Os}}/{{.Architecture}}'
docker buildx build --platform linux/amd64,linux/arm64 -t <image> --push .
```

## Build fails: COPY failed or file not found in context
Matches: `copy failed`, `failed to compute cache key`, `not found: not found`, `failed to calculate checksum`

**Cause.** The file is outside the build context, excluded by .dockerignore, or the path is wrong relative to the context directory.

**Fix.** Check the context path you pass to docker build and the .dockerignore rules. Paths in COPY are relative to the context, not to the Dockerfile.

```sh
cat .dockerignore
docker build -f <path/to/Dockerfile> <context-dir>
```

## Docker Hub rate limit (toomanyrequests)
Matches: `toomanyrequests`, `you have reached your pull rate limit`

**Cause.** Anonymous pulls from Docker Hub are rate limited per IP, which shared CI runners and NAT gateways hit quickly.

**Fix.** Log in to Docker Hub, use a pull-through cache or mirror (for example ECR pull-through cache), or copy base images into your own registry.

```sh
docker login
```

## Container exits right after starting
Matches: `exited (0)`, `exited (1)`, `exited (2)`, `container exited with code`

**Cause.** The main process finished or crashed. Exit 0 means the command ran to completion (common when a service runs in the background instead of the foreground). Exit 1 or 2 is an application error.

**Fix.** Read the container logs and exit code, and make sure the main process runs in the foreground as PID 1.

```sh
docker logs <container>
docker inspect <container> --format '{{.State.ExitCode}} {{.State.Error}}'
```

## Container killed with exit code 137
Matches: `exited (137)`, `exit code 137`, `oomkilled`

**Cause.** The process was killed with SIGKILL, usually because it hit the container's memory limit (OOM), or docker stop timed out and forced it.

**Fix.** Check whether OOMKilled is true, then raise the memory limit or reduce the app's memory use.

```sh
docker inspect <container> --format '{{.State.OOMKilled}} {{.State.ExitCode}}'
docker stats --no-stream
```

## OCI runtime create failed: entrypoint not found
Matches: `oci runtime create failed`, `starting container process caused`

**Cause.** The entrypoint script is missing, not executable, or has Windows CRLF line endings, so its #!/bin/sh line cannot be found.

**Fix.** Make the script executable and convert it to LF line endings, then rebuild.

```sh
file entrypoint.sh
sed -i 's/\r$//' entrypoint.sh
chmod +x entrypoint.sh
```

## DNS fails inside containers or during docker build
Matches: `temporary failure resolving`, `could not resolve`

**Cause.** The container inherits a DNS server it cannot reach, often a corporate VPN resolver or a localhost resolver from the host.

**Fix.** Test DNS from a container, then set explicit DNS servers in /etc/docker/daemon.json and restart Docker.

```sh
docker run --rm busybox nslookup google.com
sudo systemctl restart docker
```

## Docker Compose: dependency failed to start
Matches: `dependency failed to start`, `is unhealthy`, `depends_on`

**Cause.** A service listed in depends_on with condition service_healthy never passed its healthcheck.

**Fix.** Check the unhealthy service's logs and its healthcheck command.

```sh
docker compose ps
docker compose logs <service>
```
