# Linux

## Disk full
Matches: `no space left on device`, `disk full`, `filesystem is full`, `write error`

**Cause.** A filesystem is at 100%, usually from logs, core dumps, old artifacts or a deleted file still held open by a process.

**Fix.** Find the largest directories and clean up. If df shows full but du does not, a process holds a deleted file open: restart it.

```sh
df -h
sudo du -xh / --max-depth=2 2>/dev/null | sort -h | tail -20
sudo lsof +L1
```

## Out of inodes (disk shows free space)
Matches: `inode`, `inodes`, `df -i`

**Cause.** The filesystem ran out of inodes because of millions of small files, for example session files, cache or mail queues.

**Fix.** Find the directory with the most files and remove them.

```sh
df -i
sudo find / -xdev -type d -size +1M 2>/dev/null | head
```

## Too many open files
Matches: `too many open files`, `emfile`, `accept4: too many open files`

**Cause.** The process hit its file descriptor limit (often 1024 by default), or it leaks connections.

**Fix.** Check the process's real limit and raise it (for systemd services with LimitNOFILE). If usage keeps growing, look for a leak.

```sh
ulimit -n
cat /proc/<pid>/limits | grep "open files"
ls /proc/<pid>/fd | wc -l
```

## Process killed by the OOM killer
Matches: `out of memory: killed process`, `oom-killer`, `oom_reaper`

**Cause.** The machine (or a cgroup) ran out of memory and the kernel killed the process it scored highest.

**Fix.** Confirm in the kernel log which process died, then add memory, set limits, or fix the memory leak.

```sh
dmesg -T | grep -i -E "killed process|out of memory"
free -h
```

## systemd service fails to start
Matches: `failed with result`, `main process exited`, `start request repeated too quickly`, `failed to start`

**Cause.** The service's process exits with an error: a bad config file, a missing binary, wrong permissions or a port already in use.

**Fix.** Read the service status and journal, fix the config, then reload units and start it again.

```sh
systemctl status <unit>
journalctl -u <unit> -n 100 --no-pager
sudo systemctl daemon-reload
sudo systemctl restart <unit>
```

## SSH: Permission denied (publickey)
Matches: `permission denied (publickey)`, `no supported authentication methods available`

**Cause.** The server did not accept any key you offered: wrong private key, wrong username (ec2-user, ubuntu, azureuser), or bad permissions on ~/.ssh on the server.

**Fix.** Run SSH verbose to see which keys are tried, use the right user and key, and fix the permissions on the server.

```sh
ssh -v -i <key.pem> <user>@<host>
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## SSH: connection timed out or refused on port 22
Matches: `port 22: connection timed out`, `port 22: connection refused`, `ssh: connect to host`

**Cause.** Timed out means something drops the traffic (firewall, security group, routing, no public IP). Refused means the host answered but nothing listens on 22.

**Fix.** For timeouts, check firewall rules and routes from your IP. For refused, check that sshd is running on the host.

```sh
nc -zv -w 5 <host> 22
sudo systemctl status sshd
```

## Permission denied running a script
Matches: `bash: ./`, `noexec`

**Cause.** The file is not executable, or it lives on a filesystem mounted with noexec (common for /tmp).

**Fix.** Make it executable, or run it through the interpreter.

```sh
chmod +x <script>
mount | grep noexec
bash <script>
```

## High load or CPU usage
Matches: `load average`, `high cpu`, `cpu steal`

**Cause.** Processes are using all CPU, or waiting on disk (high iowait), or the VM is starved by its host (high steal).

**Fix.** Identify the busy processes and whether the wait is CPU, disk or steal, then scale up, tune or stop the offender.

```sh
top
ps aux --sort=-%cpu | head
vmstat 1 5
```

## Clock is out of sync
Matches: `clock skew`, `time is out of sync`, `certificate is not yet valid`, `signature expired`

**Cause.** The system clock drifted. TLS certificates, cloud API signatures and tokens all fail when time is off by minutes.

**Fix.** Check the time service and resync.

```sh
timedatectl
chronyc tracking
sudo systemctl restart chronyd
```

## SELinux denies access
Matches: `avc: denied`, `selinux`

**Cause.** SELinux blocks the process even though file permissions allow it, often after files were moved instead of copied and kept the wrong label.

**Fix.** Read the AVC denial and restore the correct labels. Avoid disabling SELinux.

```sh
sudo ausearch -m avc -ts recent
sudo restorecon -Rv <path>
```

## apt or dpkg lock held
Matches: `could not get lock /var/lib/dpkg/lock`, `unable to acquire the dpkg frontend lock`

**Cause.** Another apt process (often unattended-upgrades on boot) is running, or an earlier one was interrupted.

**Fix.** Wait for the other process to finish. If none is running, repair dpkg.

```sh
ps aux | grep -E "apt|dpkg"
sudo dpkg --configure -a
```

## Read-only file system
Matches: `read-only file system`, `remounting filesystem read-only`

**Cause.** The kernel remounted the filesystem read-only after disk errors, or the volume is mounted read-only on purpose (container root filesystems often are).

**Fix.** Check the kernel log for disk errors. For containers, write to a mounted volume instead.

```sh
dmesg -T | tail -50
mount | grep " ro,"
```

## Address already in use
Matches: `address already in use`, `eaddrinuse`, `bind failed`

**Cause.** Another process already listens on that port, or the old process has not fully exited.

**Fix.** Find the process using the port and stop it, or change the port.

```sh
sudo ss -ltnp | grep :<port>
sudo lsof -i :<port>
```

## Command not found
Matches: `command not found`

**Cause.** The tool is not installed, or its directory is not on PATH for this shell (common in cron jobs and CI, which use a minimal PATH).

**Fix.** Install it or call it by its full path.

```sh
which <command>
echo $PATH
```
