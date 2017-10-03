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
        while True:
            cursor, keys = r.scan(cursor=cursor, count=500)
            p = r.pipeline(transaction=False)
            for key in keys:
                p.dump(key)
            debug_result = p.execute()

            for i, key in enumerate(keys):
                size = len(debug_result[i]) + len(key) + 20
                key = key.decode('utf-8')
                match = self.keyspace_pattern.match(key)

                if not match:
                    match = self.index_pattern.match(key)

                keyspace = match.group(1) if match else '__unknown__'

                yield keyspace, size

            if cursor == 0:
                break


class KeyspaceEmitter(object):
    def __init__(self, iterator, callback):
        self.iterator = iterator
        self.callback = callback

    def process(self):
        for keyspace, size in self.iterator.process():
            self.callback(keyspace, size)
            yield keyspace, size


class KeyspaceTracker(object):
    def __init__(self, *keyspace_iterators):
        self.keyspaces = {}
        self.total_count = 0
        self.total_size = 0
        self.keyspace_iterators = keyspace_iterators

    def process(self):
        keyspaces = self.keyspaces
        keyspace_iterators = self.keyspace_iterators
        try:
            for iterator in keyspace_iterators:
                for keyspace, size in iterator.process():
                    try:
                        tracker = keyspaces[keyspace]
                    except KeyError:
                        keyspaces[keyspace] = tracker = {'count': 0, 'size': 0}
                    tracker['count'] += 1
                    tracker['size'] += size
                    self.total_size += size
                    self.total_count += 1
                    yield self.total_count
        except KeyboardInterrupt:
            pass

    def __enter__(self):
        for _ in self.process():
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.keyspace_iterators = []

    def stats_output(self):
        total_size = self.total_size
        for k, v in sorted(self.keyspaces.items(), key=lambda x: x[1]['size']):
            percentage = (v['size'] / total_size) * 100
            average = v['size'] / v['count']
            yield "%s bytes=%d count=%d  avg-bytes=%.2f percentage=%.2f" % (
                k, v['size'], v['count'], average, percentage)
