#!/usr/bin/env python
# SSH Key Distribution
#
# (c) 2013 Alexander Schremmer <alex AT alexanderweb DOT de>

import sys
import os
import subprocess
import collections


VERSION = 1
FILENAMES = [os.path.expanduser("~/.ssh/config"), "/etc/ssh/ssh_config"]
KEYS_BASE = os.path.expanduser("~/.ssh/keys")

if not getattr(collections, "OrderedDict"):
    print >>sys.stderr, "Runs only with Python 2.7"
    raise SystemExit


def ask_yesno(text):
    answer = raw_input(text + " [y/N] ")
    if answer.lower() == "y":
        return True
    return False


def parse_ssh_config(filename):
    if not os.path.exists(filename):
        print >>sys.stderr, "Could not find file", filename
        return {}
    data = collections.OrderedDict()
    cur_host = None
    with file(filename) as f:
        default = []
        for line in f:
            lineparts = line.strip().split(" ", 1)
            if lineparts[0].lower() == "host":
                host = lineparts[1]
                if host == "*":
                    host = None
                cur_host = host
                if host is not None:
                    suppress = False
                    data.setdefault(cur_host, []).extend(default)
            else:
                if lineparts[0] == "#:distkey":
                    cmd = ("DIST", lineparts[1])
                elif lineparts[0] == "#:acceptkey":
                    cmd = ("ACCEPT", lineparts[1])
                elif lineparts[0] == "#:nodist":
                    suppress = True
                    elem = data.pop(cur_host)
                else:
                    continue
                if cur_host is None:
                    default.append(cmd)
                elif not suppress:
                    data.setdefault(cur_host, default).append(cmd)
    return data


def merge_ssh_configs(*configs):
    data = collections.OrderedDict()
    for config in configs:
        for key in config:
            data.setdefault(key, []).extend(config[key])
    return data


def distribute_keys():
    config = merge_ssh_configs(*(parse_ssh_config(fname) for fname in FILENAMES))
    if not config:
        print """
SSH Key Distribution v%i

USAGE:
Edit/create your ~/.ssh/config file like the following:

    host foo
    hostname example.com
    #:distkey foo
    #:acceptkey gates@example.com

    host www.example.com
    #:distkey bar no-pty

This will let this tool contact two hosts. On the first host, the file ~/.ssh/keys/foo.pub (from this machine) will be added to the remote authorized_keys file. If there is a key with the name gates@example.com present, it will be ignored. Every other key will generate a prompt. For the second host, only the key bar.pub will be uploaded with the option "no-pty".
""" % (VERSION, )

    print "Distributing keys ..."
    for host in config:
        if not config[host]:
            continue
        print
        print "Updating Host", host
        ssh_opts = ["ssh", host, "-o", "ClearAllForwardings=yes", "-o", "ConnectTimeout=10"]
        dist_keys = []
        dist_keys_raw = set()
        dist_keys_names = set()
        dist_opts = {}
        for cmd, param in config[host]:
            if cmd == "DIST":
                keyparts = param.split(" ", 1)
                opts = ""
                if keyparts == 2:
                    opts = keyparts[1]
                keyname = keyparts[0]
                keyfilename = os.path.join(KEYS_BASE, keyname + ".pub")
                keydata = file(keyfilename).read().strip()
                if opts:
                    keydata += " " + opts
                keyfileparts = keydata.split(" ", 3)
                dist_keys_raw.add(keyfileparts[1])
                dist_keys.append(keydata)
                dist_opts[keyfileparts[1]] = keyfileparts[3] if len(keyfileparts) > 3 else ""
            elif cmd == "ACCEPT":
                moniker = param
                dist_keys_names.add(moniker)
        try:
            current_auth_keys = subprocess.check_output(ssh_opts + ["cat", "~/.ssh/authorized_keys"])
        except subprocess.CalledProcessError, e:
            print >>sys.stderr, "Host", host, "could not be contacted (%s)" % (str(e), )
            continue
        legacy_keys = []
        for key in current_auth_keys.splitlines():
            if not key:
                continue
            elif key.strip().startswith("#"):
                legacy_keys.append(key)
                continue
            keyparts = key.split(" ", 3)
            keyname = keyparts[2]
            keyraw = keyparts[1]
            keyparts.append("")
            keyopts = keyparts[3]
            if keyname not in dist_keys_names and keyraw not in dist_keys_raw:
                if not ask_yesno("Unknown key found (%s, opts %s) - remove this key?" % (keyname, keyopts)):
                    legacy_keys.append(key)
            elif keyname in dist_keys_names:
                legacy_keys.append(key)

            if (keyraw in dist_opts or keyopts) and keyopts != dist_opts[keyraw]:
                if not ask_yesno("Update key options (%s) [from: %r, to: %r]?" % (keyname, keyopts, dist_opts.get(keyraw, None))):
                    legacy_keys.append(key)
                    dist_keys = [k for k in dist_keys if (k + " XXX").split(" ", 3)[1] != keyraw]
        new_keys = []
        if legacy_keys:
            new_keys.extend(legacy_keys)
            new_keys.append("")
        new_keys.extend(dist_keys)
        new_keys.append("")
        new_keys = "\n".join(new_keys)
        if new_keys != current_auth_keys:
            p = subprocess.Popen(ssh_opts + ["cat > ~/.ssh/authorized_keys_new"], stdin=subprocess.PIPE, stdout=None, close_fds=True)
            p.stdin.write(new_keys)
            p.stdin.close()
            p.wait()
            output = subprocess.check_output(ssh_opts + ["mv", "~/.ssh/authorized_keys_new", "~/.ssh/authorized_keys"])
            if output:
                print output
            print "Updated!"
        else:
            print "Already up-to-date"


if __name__ == '__main__':
    distribute_keys()

