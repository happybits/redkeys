#!/usr/bin/env python

# std lib
import os
import unittest
from io import StringIO

# 3rd party
import redislite

# our package
import redkeys  # noqa

TEST_DIR = os.path.dirname(__file__)
SRC_RDB = os.path.join(TEST_DIR, '.redis_src.db')
SRC = redislite.StrictRedis(SRC_RDB)


def flush_redis_data(conn):
    if conn is None:
        return

    conn.flushdb()


def clean():
    flush_redis_data(SRC)


class BasicTestCase(unittest.TestCase):
    data = [
        ('A{foo}', '1'),
        ('A{bar}', '1'),
        ('A{bazz}', '1'),
        ('B{foo}', '1'),
        ('B{bar}', '1'),
    ]

    def setUp(self):
        clean()
        for k, v in self.data:
            SRC.set(k, v)

    def test(self):
        with redkeys.KeyspaceTracker(redkeys.RedisKeyspaceIterator(SRC)) as t:
            self.assertEqual(t.keyspaces,
                             {'B': 2,
                              'A': 3})

    def test_cli(self):
        out = StringIO()
        redkeys.main(["redislite://%s" % SRC_RDB], out=out)
        output = out.getvalue().strip()
        print(output)
        self.assertIn('B: 40.0%', output)
        self.assertIn('A: 60.0%', output)
        self.assertIn('sampled: 5', output)


if __name__ == '__main__':
    unittest.main(verbosity=2)
