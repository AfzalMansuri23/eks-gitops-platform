# Databases

## PostgreSQL: too many clients
Matches: `sorry, too many clients already`, `remaining connection slots are reserved`
Tool: PostgreSQL

**Cause.** Connections reached max_connections, usually from many app replicas each holding a pool, or connections leaking.

**Fix.** See who holds connections, put a pooler (PgBouncer, RDS Proxy) in front, and size app pools to fit.

```sh
psql -c "select usename, application_name, state, count(*) from pg_stat_activity group by 1,2,3 order by 4 desc;"
psql -c "show max_connections;"
```

## PostgreSQL: connection refused
Matches: `could not connect to server: connection refused`, `is the server running on host`, `connection to server at`
Tool: PostgreSQL

**Cause.** Postgres is down, listens only on localhost (listen_addresses), or a firewall blocks 5432.

**Fix.** Check it accepts connections from the client's host and that listen_addresses includes the right interface.

```sh
pg_isready -h <host> -p 5432
psql -c "show listen_addresses;"
```

## PostgreSQL: no pg_hba.conf entry
Matches: `no pg_hba.conf entry for host`
Tool: PostgreSQL

**Cause.** pg_hba.conf has no rule allowing that user, database and client IP (or requires SSL the client did not use).

**Fix.** Add a rule for the client's network with the right auth method, then reload.

```sh
psql -c "show hba_file;"
psql -c "select pg_reload_conf();"
```

## PostgreSQL: password authentication failed
Matches: `password authentication failed for user`
Tool: PostgreSQL

**Cause.** Wrong password, the user does not exist, or the password hash method (md5 vs scram-sha-256) does not match pg_hba.conf.

**Fix.** Reset the password and check the auth method in pg_hba.conf.

```sh
psql -c "alter user <user> with password '<new-password>';"
```

## PostgreSQL: deadlock detected
Matches: `deadlock detected`
Tool: PostgreSQL

**Cause.** Two transactions lock the same rows in opposite order. Postgres kills one of them.

**Fix.** Make transactions lock rows in a consistent order and keep them short. Retry the failed transaction in the app.

```sh
psql -c "select pid, wait_event_type, wait_event, query from pg_stat_activity where wait_event_type = 'Lock';"
```

## PostgreSQL: disk full or WAL growing
Matches: `could not extend file`, `pg_wal`, `could not write to file`
Tool: PostgreSQL

**Cause.** The data disk is full, often because an inactive replication slot keeps WAL files from being removed.

**Fix.** Check WAL size and replication slots. Drop slots nobody uses, then add disk if needed.

```sh
psql -c "select slot_name, active, restart_lsn from pg_replication_slots;"
du -sh $PGDATA/pg_wal
```

## PostgreSQL: replica lag
Matches: `replication lag`, `canceling statement due to conflict with recovery`
Tool: PostgreSQL

**Cause.** The replica cannot keep up (slow disk, heavy writes), or long queries on the replica conflict with replay.

**Fix.** Measure the lag, find long queries on the replica, and size the replica like the primary.

```sh
psql -c "select now() - pg_last_xact_replay_timestamp() as lag;"
```

## MySQL: too many connections
Matches: `error 1040`, `too many connections`
Tool: MySQL

**Cause.** Connections reached max_connections.

**Fix.** Find the clients holding connections, fix leaks, and use pooling. Raise max_connections only if memory allows it.

```sh
mysql -e "show processlist;"
mysql -e "show variables like 'max_connections';"
```

## MySQL: access denied for user
Matches: `error 1045`, `access denied for user`
Tool: MySQL

**Cause.** Wrong password, or the user exists only for a different host ('user'@'localhost' is not 'user'@'%').

**Fix.** Check which host entries exist for the user and grant from the right host.

```sh
mysql -e "select user, host from mysql.user where user = '<user>';"
```

## MySQL: lock wait timeout exceeded
Matches: `error 1205`, `lock wait timeout exceeded`
Tool: MySQL

**Cause.** A transaction waited too long for a row lock held by another (often an open transaction that never committed).

**Fix.** Find the blocking transaction, commit or kill it, and keep transactions short.

```sh
mysql -e "show engine innodb status\G"
mysql -e "select * from information_schema.innodb_trx\G"
```

## MySQL server has gone away
Matches: `mysql server has gone away`, `error 2006`, `error 2013`, `lost connection to mysql server`

**Cause.** The connection idled past wait_timeout, a query sent more than max_allowed_packet, or the server restarted.

**Fix.** Enable reconnect or pool health checks in the app, and raise max_allowed_packet for large rows.

```sh
mysql -e "show variables where variable_name in ('wait_timeout','max_allowed_packet');"
```
Tool: MySQL

## Redis: OOM command not allowed
Matches: `oom command not allowed when used memory`, `maxmemory`
Tool: Redis

**Cause.** Redis hit maxmemory and its eviction policy is noeviction, so writes fail.

**Fix.** Pick an eviction policy that fits (allkeys-lru for caches), set TTLs, or add memory.

```sh
redis-cli info memory
redis-cli config get maxmemory-policy
```

## Redis: MISCONF cannot persist on disk
Matches: `misconf redis is configured to save rdb snapshots`, `not able to persist on disk`
Tool: Redis

**Cause.** The background save failed, usually from a full disk or wrong permissions, so Redis stops accepting writes.

**Fix.** Free disk or fix permissions on the data directory, then check that saves succeed.

```sh
redis-cli info persistence
df -h
```

## Redis: could not connect
Matches: `could not connect to redis`, `redis connection refused`, `denied redis is running in protected mode`
Tool: Redis

**Cause.** Redis is down, bound to 127.0.0.1, or protected mode blocks remote clients without a password.

**Fix.** Ping it from the client host and check bind and protected-mode settings.

```sh
redis-cli -h <host> -p 6379 ping
```

## MongoDB: server selection timed out
Matches: `mongoserverselectionerror`, `server selection timed out`
Tool: MongoDB

**Cause.** The driver cannot reach any suitable member: wrong connection string, IP not allowed (Atlas access list), or the replica set has no primary.

**Fix.** Test the connection string from the client host and check the network access list.

```sh
mongosh "<connection-string>" --eval "db.runCommand({ ping: 1 })"
```
