SSH Key Distribution
====================

(c) 2013 Alexander Schremmer <alex AT alexanderweb DOT de>
License: MIT

Manage/upload/revoke SSH public keys from remote servers. Usage:

You need a master machine where you keep your public keys. On this machine,
edit/create your ~/.ssh/config file like the following:

    #:distkey master

    host foo
    hostname example.com
    #:distkey foo
    #:acceptkey gates@example.com

    host www.example.com
    #:distkey bar no-pty

Afterwards, you simply run the tool to update your remote machines'
authorized_keys files.

In this example, the tool will contact two hosts. On the first host, the file
~/.ssh/keys/foo.pub (from this machine) will be added to the remote
authorized_keys file. If there is a key with the name gates@example.com
present, it will be left intact. Every other key will generate a prompt. For
the second host, only the key bar.pub will be uploaded with the option
"no-pty". Furthermore, every machine will get the key master.pub.

Usually, you will need a few #:distkey statements for global keys and for
certain machines. And you will need #:acceptkey statements if you are sharing
an account with another user.
