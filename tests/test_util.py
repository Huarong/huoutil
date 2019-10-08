#!/usr/bin/env python
# coding=utf-8

import os
import sys

sys.path.insert(0, '.')
from huoutil.util import ConfigBase
from huoutil.util import file2dictlist
TESTDATA = './tests/testdata/'


class Config(ConfigBase):
    def __init__(self, path=None):
        super(Config, self).__init__()
        self.NAME = 'Tom'
        self.AGE = 12
        self.LOVE = ['apple', 'banana']
        if path:
            self.load_conf(path)


def test_config():
    conf_path = os.path.join(TESTDATA, 'test.conf')
    cfg = Config(conf_path)
    assert cfg.NAME == 'Tian'
    assert cfg.AGE == 32
    assert cfg.LOVE == ['apple', 'banana']


def test_file2dictlist():
    data = file2dictlist('./tests/testdata/test_file2dictlist', kn=0, vn=1)
    assert data[u'胰岛素'] == [u'低血糖', u'呕吐']
    data = file2dictlist('./tests/testdata/test_file2dictlist', kn=0, vn=None, dup=False)
    assert data[u'胰岛素'] == [u'低血糖', u'呕吐', u'子宫收缩']
    assert data[u'泻药'] == []
    assert data[u'催吐药'] == [u'呕吐 排尿困难']
    data = file2dictlist('./tests/testdata/test_file2dictlist', kn=0, vn=None)
    assert data[u'胰岛素'] == [u'低血糖', u'呕吐', u'子宫收缩', u'子宫收缩', u'子宫收缩']

