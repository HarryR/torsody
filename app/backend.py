__all__ = ('Api',)

from gevent.queue import JoinableQueue
from gevent.event import AsyncResult
import os
import sys
import traceback
import shutil
import socket
import time
import re
import random
import string
import urllib
from pwd import getpwnam

import stem
import stem.connection
from stem.control import Controller as StemController

API_QUEUE = JoinableQueue()

def chown_R(path, uid, gid):
    for root, dirs, files in os.walk(path):
        for momo in dirs:
            os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
            os.chown(os.path.join(root, momo), uid, gid)

def prosody_telnetcmd(cmd):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('localhost', 5582)
    sock.connect(server_address)
    sock.sendall(cmd + "\n")
    time.sleep(0.1)
    sock.close()

class Api(object):
    @staticmethod
    def call(*args, **kwargs):
        result = AsyncResult()
        API_QUEUE.put([result, args, kwargs])
        return result.get()

    def __init__(self):
        self.stem = None
        self.running = False
        self.init_stem()

    def ping_stem(self):
        if self.stem is None:
            self.init_stem()
        if self.stem is None:
            return False
        if not self.stem.is_alive():
            try:
                self.stem.connect()
            except stem.SocketError:
                pass
            try:
                self.stem.authenticate()
            except stem.connection.MissingPassword:
                return False
            except stem.connection.AuthenticationFailure:
                return False
        return self.stem.is_alive()

    def init_stem(self):
        try:
            self.stem = StemController.from_port()
        except stem.SocketError:
            return False
        try:
            self.stem.authenticate()
        except stem.connection.MissingPassword:
            return False
        except stem.connection.AuthenticationFailure:
            return False
        print("Tor is running version %s" % self.stem.get_version())

    def dispatch(self, args, kwargs):
        if len(args) < 1:
            raise RuntimeError("Args Required")
        funcname = 'api_' + str(args[0])
        args = args[1:]
        if not hasattr(self, funcname):
            raise RuntimeError('Unknwon Function')
        method = getattr(self, funcname)
        return method(*args, **kwargs)

    def valid_username(self, username):
        return re.match(r'^[a-zA-Z0-9]{2,16}$', username) is not None

    def valid_onion(self, hostname):
        return re.match(r'^[a-z2-7]{16}\.onion$', hostname) is not None


    def api_ping(self):
        return "pong"

    def api_create(self, name):
        """
        Given the name of a contact create a new account
        on a new single use .onion
        """
        if not self.valid_username(name):
            return None
        hidden_service = self.tor_create(name)
        if hidden_service is None or hidden_service.hostname is None:
            #raise RuntimeError('Unable to create new .onion for %s' % (name,))
            return None
        password = ''.join(random.choice(string.uppercase + string.lowercase + string.digits) for _ in range(10))
        self.prosody_create(hidden_service.hostname)
        self.prosody_useradd(hidden_service.hostname, name, password)
        return {
            'username': name,
            'hostname': hidden_service.hostname,
            'password': password,
        }

    def api_list(self):
        return self.prosody_hostnames()

    def api_delete(self, hostname):
        if not self.valid_onion(hostname):
            return False
        users = self.prosody_users(hostname)
        if len(users) == 1:
            self.tor_delete(users[0])
        self.prosody_delete(hostname)
        return True

    def prosody_users(self, hostname):
        assert self.valid_onion(hostname)
        if not self.valid_onion(hostname):
            return []
        accounts_dir = '/var/lib/prosody/%s/accounts/' % (self.quote(hostname),)
        if not os.path.exists(accounts_dir):
            return []
        return [x.rsplit('.', 1)[0] for x in os.listdir(accounts_dir)]

    def prosody_hostnames(self):
        return filter(lambda x: self.valid_onion(x), [self.unquote(x) for x in os.listdir('/var/lib/prosody')])

    def quote(self, hostname):
        return urllib.quote(hostname).replace('.', '%2e')

    def unquote(self, hostname):
        if '%' in hostname:
            return urllib.unquote(hostname)
        return hostname

    def prosody_create(self, hostname):
        """
        Create a Prosody virtual host
        """
        assert self.valid_onion(hostname)
        if not self.valid_onion(hostname):
            return False
        prosody_dir = '/var/lib/prosody'
        host_dir = '/'.join([prosody_dir, self.quote(hostname)])
        accounts_dir = '/'.join([host_dir, 'accounts'])
        acct = getpwnam('prosody')
        for dirname in [prosody_dir, host_dir, accounts_dir]:
            if not os.path.exists(dirname):
                os.mkdir(dirname, 0750)
                os.chown(dirname, acct.pw_uid, acct.pw_gid)
        # Create virtualhost config file
        config_file = '/etc/prosody/conf.d/%s.cfg.lua' % (hostname,)
        fh = open(config_file, 'w')
        fh.write('VirtualHost "%s"\n\n' % (hostname,))
        fh.close()
        os.chmod(config_file, 0640)
        acct = getpwnam('prosody')
        os.chown(config_file, 0, acct.pw_gid)
        # Reload and activate hostnames
        prosody_telnetcmd("config:reload()")
        prosody_telnetcmd("host:activate('%s')" % (hostname,))
        return True

    def prosody_useradd(self, hostname, username, password):
        """
        Add jabber user to a Prosody virtual host
        """
        assert self.valid_onion(hostname)
        if not self.valid_onion(hostname):
            return False
        prosody_telnetcmd("user:create('%s@%s', '%s')" % (username, hostname, password))
        return True

    def prosody_userdel(self, hostname, username):
        """
        Delete a jabber user
        """
        assert self.valid_onion(hostname)
        assert self.valid_username(username)
        if not self.valid_onion(hostname) or not self.valid_username(username):
            return False
        # Disconnect user connections!
        prosody_telnetcmd("user:delete('%s@%s')" % (username, hostname))
        prosody_telnetcmd('c2s:close("%s@%s")' % (username, hostname))
        return True

    def prosody_delete(self, hostname):
        """
        Delete a jabber virtual host and all its users
        """
        assert self.valid_onion(hostname)
        if not self.valid_onion(hostname):
            return False
        for username in self.prosody_users(hostname):
            self.prosody_userdel(hostname, username)
        # Disconnect all users and deactivate host
        config_file = '/etc/prosody/conf.d/%s.cfg.lua' % (hostname,)
        if os.path.exists(config_file):
            os.unlink(config_file)
        prosody_telnetcmd("s2s:closeall('%s')" % (hostname,))
        prosody_telnetcmd("host:deactivate('%s')" % (hostname,))
        directory = '/var/lib/prosody/%s/' % (self.quote(hostname),)
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory, True, None
                              )
        except:
            pass
        return True

    def tor_list(self):
        return filter(lambda x: os.path.isdir('/var/lib/tor/'+x), os.listdir('/var/lib/tor/'))

    def tor_create(self, name):
        assert self.valid_username(name)
        if not self.valid_username(name):
            return None
        if not self.ping_stem():
            return None
        conf = self.stem.get_hidden_service_conf()
        self.stem.set_options([
            ('HiddenServiceDir', [name]),
            ('HiddenServicePort', '5269 127.0.0.1:5269'),
            ('HiddenServicePort', '5222 127.0.0.1:5222'),
        ])
        self.stem.save_conf()

        hostname = None
        hostname_path = '/'.join(['/var/lib/tor', name, 'hostname'])
        start_time = time.time()
        while not os.path.exists(hostname_path):
            wait_time = time.time() - start_time
            if wait_time >= 3:
                break
            else:
                time.sleep(0.05)
        if os.path.exists(hostname_path):
            try:
                with open(hostname_path) as hostname_file:
                    hostname = hostname_file.read().strip()
            except:
                pass

        return stem.control.CreateHiddenServiceOutput(
            path=name,
            hostname=hostname,
            config=conf,
        )

    def tor_delete(self, name):
        if not self.valid_username(name):
            return False
        directory = '/var/lib/tor/'+name
        if not os.path.exists(directory):
            return False
        if not self.ping_stem():
            return False
        self.stem.remove_hidden_service(name)
        for path in [directory+'/private_key', directory+'/hostname']:
            if os.path.exists(path):
                os.unlink(path)
        os.rmdir(directory)
        return True

    def run(self):
        self.running = True
        while self.running:
            result, args, kwargs = API_QUEUE.get()
            try:
                try:
                    result.set(self.dispatch(args, kwargs))
                except:
                    e = sys.exc_info()[0]
                    traceback.print_exc()
                    result.set_exception(e)
            finally:
                API_QUEUE.task_done()

    def stop(self):
        self.running = False
        API_QUEUE.join()
        self.stem.close()
