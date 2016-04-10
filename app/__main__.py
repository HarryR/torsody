from gevent import monkey; monkey.patch_all()
import argparse, sys, re, logging, logging.config, os
from .server import run_server

def is_valid_hostname(hostname):
    """
    Is the string a possibly valid hostname or IP?
    """
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


class HostnameAction(argparse.Action):
    """
    VAlidates a hostname or IP argument
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) > 1:
            raise argparse.ArgumentError(self, "can only accept 1 hostname")
        value = values[0]
        if not is_valid_hostname(value):
            raise argparse.ArgumentError(self, "invalid hostname or ip")
        setattr(namespace, self.dest, value)


class TcpIpPortAction(argparse.Action):
    """
    Validates a TCP/IP port argument
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) > 1:
            raise argparse.ArgumentError(self, "can only accept 1 port")
        try:
            value = int(values[0])
        except:
            raise argparse.ArgumentError(self, "must be valid TCP/IP port")
        if value < 1 or value >= 0xFFFF:
            raise argparse.ArgumentError(self, "out of range for TCP/IP port")
        setattr(namespace, self.dest, value)


def main():
    default_config = os.path.join(os.getcwd(), "settings.cfg")
    parser = argparse.ArgumentParser(description='App Server')
    parser.add_argument('--config', type=argparse.FileType('r'), help='App config file', metavar='APP_CONF', default=default_config)
    parser.add_argument('--logging', type=argparse.FileType('r'), help='Python logging.conf', metavar='LOG_CONF')
    parser.add_argument('--http-host', type=str, action=HostnameAction, default='0.0.0.0', nargs=1, metavar='HOST', help='Bind Host for HTTP server')
    parser.add_argument('--http-port', type=int, action=TcpIpPortAction, default=8080, nargs=1, metavar='PORT', help='Bind Port for HTTP server')

    args = parser.parse_args().__dict__

    if args['logging'] is not None:
        logging.config.fileConfig(args['logging'])

    return run_server(args)


if __name__ == '__main__':
    sys.exit(main())