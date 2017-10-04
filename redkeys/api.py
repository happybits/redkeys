from __future__ import division
import re

__all__ = ['RedisKeyspaceIterator', 'KeyspaceTracker', 'KeyspaceEmitter']


class RedisKeyspaceIterator(object):
    keyspace_pattern = re.compile(
        r'^([A-Za-z0-9\:\-_]{1,100})\{[A-Za-z0-9_\-\.\+\(\)]{1,500}\}$')
    index_pattern = re.compile(r'^([A-Za-z0-9\:\-_]{1,100})\:[0-9]+\:u\:?$')

    def __init__(self, redis_connection):
        self.conn = redis_connection

    def process(self):
        cursor = 0
        r = self.conn
        patterns = [self.keyspace_pattern, self.index_pattern]
        while True:
            cursor, keys = r.scan(cursor=cursor, count=500)

            for key in keys:
                key = key.decode('utf-8')
                match = None
                for pattern in patterns:
                    match = pattern.match(key)
                    if match:
                        yield match.group(1)
                        break
                if not match:
                    yield '__unknown__'

            if cursor == 0:
                break


class KeyspaceEmitter(object):
    def __init__(self, iterator, callback):
        self.iterator = iterator
        self.callback = callback

    def process(self):
        for keyspace, size in self.iterator.process():
            self.callback(keyspace)
            yield keyspace


class KeyspaceTracker(object):
    def __init__(self, *keyspace_iterators):
        self.keyspaces = {}
        self.total = 0
        self.keyspace_iterators = keyspace_iterators

    def process(self):
        keyspaces = self.keyspaces
        keyspace_iterators = self.keyspace_iterators
        try:
            for iterator in keyspace_iterators:
                for keyspace in iterator.process():
                    try:
                        keyspaces[keyspace] += 1
                    except KeyError:
                        keyspaces[keyspace] = 1
                    self.total += 1
                    yield self.total
        except KeyboardInterrupt:
            pass

    def __enter__(self):
        for _ in self.process():
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.keyspace_iterators = []

    def stats_output(self):
        total = self.total
        for k, v in sorted(self.keyspaces.items(), key=lambda x: x[1]):
            percentage = (v / total) * 100
            yield "%s: %.1f%%" % (k, percentage)

        yield ""
        yield "sampled: %d" % total
