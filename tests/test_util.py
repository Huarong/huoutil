import os
import sys

sys.path.insert(0, '.')
from huoutil.util import ConfigBase

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
