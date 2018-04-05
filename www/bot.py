#!/usr/bin/env python3
import os
import re
import uuid
import sqlite3
import irc.bot

NICKNAME = 'ricebot'
PASSWORD = os.environ.get('RICEBOT_PASSWORD')
SERVER = ('irc.rizon.net', 6667)
CHANNELS = []
HIGHLIGHT_REGEX = re.compile(r'^\s*%s[ :,]+(.*)\s*$' % NICKNAME)
ADMINS = ['icyphox', 'eti', 'nai']
ADMIN_COMMANDS = ['add']

class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, database):
        super().__init__([SERVER], NICKNAME, NICKNAME)
        self.database = database
        self.command_queue = {}

    def on_welcome(self, c, e):
        self.db = sqlite3.connect(self.database)
        c.privmsg('NickServ', 'identify %s' % PASSWORD)
        for channel in CHANNELS:
            c.join(channel)

    def on_privmsg(self, c, e):
        nick = e.source.nick
        msg = e.arguments[0]
        self.enqueue_command(nick, nick, msg)

    def on_pubmsg(self, c, e):
        nick = e.source.nick
        target = e.target
        msg = e.arguments[0]
        match = HIGHLIGHT_REGEX.match(msg)
        if match:
            self.enqueue_command(nick, target, match[1])

    def on_privnotice(self, c, e):
        nick = e.source.nick
        msg = e.arguments[0]
        if nick == 'NickServ':
            args = msg.split(' ')
            if args[0].lower() == 'status':
                target_nick, status = args[1:]
                if not target_nick in self.command_queue:
                    return
                if int(status) == 3:
                    commands = list(self.command_queue[target_nick])
                    del self.command_queue[target_nick]
                    for target, cmd in commands:
                        self.command(target_nick, target, cmd)
                else:
                    del self.command_queue[target_nick]
                    c.privmsg(target_nick, "You have to be identified by password to NickServ to issue commands.")

    def request_status(self, nick):
        self.connection.privmsg('NickServ', 'status %s' % nick)

    def enqueue_command(self, nick, target, cmd):
        if not nick in self.command_queue:
            self.request_status(nick)
            self.command_queue[nick] = []
        self.command_queue[nick].append((target, cmd))

    def command(self, nick, target, cmd):
        c = self.connection
        args = cmd.split()
        cmd = args.pop(0).lower()
        if cmd in ADMIN_COMMANDS and not nick in ADMINS:
            c.privmsg(target, "Only admins can use this command.")
            return
        if cmd == 'ping':
            c.privmsg(target, 'pong')
        elif cmd == 'help':
            c.privmsg(target, "Help coming soon - for now, ask an admin.")
        elif cmd == 'add':
            if len(args) != 1:
                c.privmsg(target, "Syntax: add <nickname>")
                return
            target_nick = args[0]
            key = str(uuid.uuid4())
            try:
                with self.db as db:
                    db.execute('insert into user(key, nickname) values (?, ?)', (key, target_nick))
            except sqlite3.IntegrityError:
                c.privmsg(target, "%s is already in the contest." % target_nick)
            else:
                c.privmsg(target, "%s was added to the contest" % target_nick)
                c.privmsg(target_nick, "You were added to the contest with the key: %s" % key)
        elif cmd == 'list':
            users = self.db.execute('select nickname from user').fetchall()
            c.privmsg(target, "List of contestants: %s" % ", ".join(map(lambda x: x[0], users)))
        elif cmd == 'getkey':
            user = self.db.execute('select key from user where nickname = ?', (nick,)).fetchone()
            if user:
                c.privmsg(nick, "Your key is: %s" % user[0])
            else:
                c.privmsg(target, "You haven't joined the contest.")
