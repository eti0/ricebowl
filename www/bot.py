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

class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, database):
        irc.bot.SingleServerIRCBot.__init__(self, [SERVER], NICKNAME, NICKNAME)
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.command_queue = {}

    def on_welcome(self, c, e):
        c.privmsg('NickServ', 'identify %s' % PASSWORD)
        for channel in CHANNELS:
            c.join(channel)

    def on_privmsg(self, c, e):
        nick = e.source.nick
        msg = e.arguments[0]
        self.enqueue_command(nick, nick, msg)
        self.request_status(nick)

    def on_pubmsg(self, c, e):
        nick = e.source.nick
        target = e.target
        msg = e.arguments[0]
        match = HIGHLIGHT_REGEX.match(msg)
        if match:
            self.enqueue_command(nick, target, match[1])
            self.request_status(nick)

    def on_privnotice(self, c, e):
        nick = e.source.nick
        msg = e.arguments[0]
        if nick == 'NickServ':
            args = msg.split(' ')
            if args[0].lower() == 'status':
                target_nick, status = args[1:]
                if status == '3' and target_nick in self.command_queue:
                    while self.command_queue[target_nick]:
                        target, cmd = self.command_queue[target_nick].pop(0)
                        self.command(target_nick, target, cmd)
                else:
                    del self.command_queue[target_nick]
                    c.privmsg(target_nick, "You have to be identified by password to NickServ to issue commands.")

    def request_status(self, nick):
        self.connection.privmsg('NickServ', 'status %s' % nick)

    def enqueue_command(self, nick, target, cmd):
        if not nick in self.command_queue:
            self.command_queue[nick] = []
        self.command_queue[nick].append((target, cmd))

    def command(self, nick, target, cmd):
        c = self.connection
        args = cmd.split()
        cmd = args.pop(0).lower()
        if cmd == 'ping':
            c.privmsg(target, 'pong')
        elif cmd == 'help':
            c.privmsg(target, "Help coming soon - for now, ask an admin.")
        elif cmd == 'add':
            if nick in ADMINS:
                if len(args) == 1:
                    target_nick = args[0]
                    with self.db as db:
                        db.execute('insert into user(key, nickname) values (?, ?)', (str(uuid.uuid4()), target_nick))
                    c.privmsg(target, "%s was added to the contest" % target_nick)
                else:
                    c.privmsg(target, "Syntax: add <nickname>")
            else:
                c.privmsg(target, "Only admins can use this command.")
        elif cmd == 'list':
            users = self.db.execute('select nickname from user').fetchall()
            nicknames = map(lambda x: x[0], users)
            c.privmsg(target, "List of contestants: %s" % ", ".join(nicknames))
        elif cmd == 'getkey':
            user = self.db.execute('select key from user where nickname = ?', (nick,)).fetchone()
            if user:
                key, = user
                c.privmsg(nick, "Your key is:")
                c.privmsg(nick, key)
            else:
                c.privmsg(target, "You haven't joined the contest.")
