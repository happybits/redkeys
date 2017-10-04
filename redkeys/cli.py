import argparse
import redis
import sys
from signal import signal, SIGTERM
from .api import RedisKeyspaceIterator, KeyspaceTracker

try:
    import redislite
except ImportError:
    redislite = None

__all__ = ['main']


def get_redis_connection(host):
    if redislite and host.startswith("redislite://"):
        return redislite.StrictRedis(host[12:])
    else:
        return redis.StrictRedis.from_url(host)


def process(hosts, out, err=None):
    connections = [get_redis_connection(host) for host in hosts]
    iterators = [RedisKeyspaceIterator(conn) for conn in connections]
    tracker = KeyspaceTracker(*iterators)
    total_count = 0
    for total_count in tracker.process():
        if err and total_count % 1000 == 0:
            err.write(u'\rprocessed: %d' % total_count)

    if err:
        err.write(u'\rprocessed: %d' % total_count)

    out.write(u'\n======================\n')
    for line in tracker.stats_output():
        out.write(u'%s\n' % line)

    out.write(u'======================\n')


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description='iterate through all the keys and collect stats on each '
                    'keyspace')
    parser.add_argument('servers',
                        type=str,
                        nargs='+',
                        help='list of servers in the form of hostname:port')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='turn on verbose output')

    return parser.parse_args(args=args)


# pylint: disable=unused-argument
def sigterm_handler(signum, frame):
    raise SystemExit('--- Caught SIGTERM; Attempting to quit gracefully ---')


def main(args=None, out=None, err=None):
    signal(SIGTERM, sigterm_handler)
    args = parse_args(args=args)
    if err is None:
        err = sys.stderr

    if not args.verbose:
        err = None

    if out is None:
        out = sys.stdout

    process(args.servers, out=out, err=err)
