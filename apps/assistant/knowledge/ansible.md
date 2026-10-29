# Ansible

## Host UNREACHABLE
Matches: `unreachable!`, `failed to connect to the host via ssh`

**Cause.** Ansible cannot SSH to the host: wrong IP or user in the inventory, the key is not offered, or a firewall blocks port 22.

**Fix.** Ping the host with verbose output to see the SSH error, then fix the inventory, key or network.

```sh
ansible <host> -i <inventory> -m ping -vvv
```

## Missing sudo password
Matches: `missing sudo password`, `sudo: a password is required`

**Cause.** A task uses become, but no sudo password was provided and the user does not have passwordless sudo.

**Fix.** Pass the password at runtime, or give the user NOPASSWD sudo for automation.

```sh
ansible-playbook <playbook.yml> -i <inventory> --ask-become-pass
```

## Python interpreter not found
Matches: `/usr/bin/python: not found`, `interpreter discovery`, `the module failed to execute correctly, you probably need to set the interpreter`

**Cause.** The target host has no Python at the path Ansible tried, common on minimal images.

**Fix.** Install Python 3 on the host or set ansible_python_interpreter.

```sh
ansible <host> -i <inventory> -m raw -a "which python3"
ansible-playbook <playbook.yml> -i <inventory> -e ansible_python_interpreter=/usr/bin/python3
```

## Undefined variable
Matches: `is undefined`, `'dict object' has no attribute`, `undefinederror`

**Cause.** The variable is not defined for that host or group, has a typo, or comes from a fact that was not gathered.

**Fix.** Print the host's variables to see what is set, then define it in the right group_vars or use a default.

```sh
ansible-inventory -i <inventory> --host <host>
ansible <host> -i <inventory> -m debug -a "var=<variable>"
```

## YAML syntax error in a playbook
Matches: `syntax error while loading yaml`, `we were unable to read either as json nor yaml`

**Cause.** Bad indentation, a tab character, or an unquoted value that starts with {{.

**Fix.** Run the syntax check and ansible-lint. Quote values that begin with a Jinja expression.

```sh
ansible-playbook <playbook.yml> --syntax-check
ansible-lint <playbook.yml>
```

## Module or collection not found
Matches: `couldn't resolve module/action`, `was not found in configured module paths`

**Cause.** The module lives in a collection that is not installed, or the playbook uses the short name without the collection.

**Fix.** Install the collection and use the fully qualified name, for example community.general.ufw.

```sh
ansible-galaxy collection install <namespace.collection>
ansible-galaxy collection list
```

## Host key checking fails
Matches: `host key checking is enabled`, `ansible_host_key_checking`

**Cause.** The target's SSH host key is not in known_hosts, normal for newly created machines.

**Fix.** Add the host keys first. Only turn off host key checking in throwaway lab environments.

```sh
ssh-keyscan <host> >> ~/.ssh/known_hosts
export ANSIBLE_HOST_KEY_CHECKING=False
```
