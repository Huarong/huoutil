#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import logging
import hashlib
import pickle
import codecs
import json
from collections import defaultdict
from urlparse import urlparse
# from lxml import etree  # not exist on hadoop
import xml.etree.ElementTree as ET
try:
    import numpy as np
except ImportError:
    pass

HOST_PATTEN = re.compile(r'https?://([a-zA-Z0-9.\-_]+)')


class Context(object):
    def __init__(self):
        self.config = None
        self.state = None


class StateError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class State(object):
    def __init__(self, path=None):
        self.path = path
        if os.path.exists(path):
            self.load()
        else:
            self.dict = {}

    def set(self, key, val):
        self.dict[key] = val
        self.save()

    def get(self, key):
        try:
            val = self.dict[key]
            return val
        except KeyError:
            raise StateError('key [%s] not exist' % key)

    def add(self, key, val):
        if key in self.dict:
            raise StateError('key [%s] already exist' % key)
        else:
            self.dict[key] = val
        self.save()

    def save(self):
        with codecs.open(self.path, 'wb', encoding='utf-8') as f:
            json.dump(self.dict, f)

    def load(self):
        with codecs.open(self.path, 'rb', encoding='utf-8') as f:
            self.dict = json.load(f)

    def __del__(self):
        try:
            self.save()
        except:
            pass


class ConfigError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)


class ConfigBase(object):
    """
    How to use:
        class Config(ConfigBase):
            def __init__(self, path=None):
                super(Config, self).__init__()
                self.NAME = 'Tom'
                self.AGE = 12
                self.LOVE = ['apple', 'banana']
                if path:
                    self.load_conf(path)
    """

    def __init__(self):
        self._path = ''
        self._name = ''
        self._type = ''

    def is_valid_key(self, key):
        if key in self.__dict__:
            return True
        else:
            return False

    def cast(self, key, value):
        init_value = self.__dict__[key]
        if isinstance(init_value, int):
            value = int(value)
        elif isinstance(init_value, float):
            value = float(value)
        elif isinstance(init_value, (list)):
            tokens = value.split(',')
            if init_value:
                element_type = type(init_value[0])
                value = [element_type(t) for t in tokens]
            else:
                value = tokens
            if type(init_value) == tuple:
                value = tuple(value)
            elif type(init_value) == set:
                value = set(value)
        else:
            pass
        return value

    def load_conf(self, path, typ=None):
        ext = path.split('.')[-1]
        if not typ:
            if ext == 'conf':
                typ = 'sh'
        if typ == 'sh':
            self.load_sh_conf(path)
        elif typ == 'json':
            self.load_json_conf(path)
        else:
            raise ValueError(
                'invalid conf type: {0}. Please assign to  "typ" explicitly'.format(
                    typ))
        return None

    def load_sh_conf(self, path):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(self._path)
        self._type = 'sh'
        with codecs.open(path, encoding='utf-8') as fc:
            for line in fc:
                if not line.strip():
                    continue
                if line.lstrip().startswith('#'):
                    continue
                tokens = line.rstrip().split('=')
                if len(tokens) < 2:
                    logging.warning('invalid config line: %s' % line)
                key = tokens[0]
                key = key.upper()
                if self.is_valid_key(key):
                    value = ''.join(tokens[1:])
                    value = self.cast(key, value)
                    self.__setattr__(key, value)
                else:
                    logging.warn('invalid key {0}'.format(key))
        return None

    def load_json_conf(self, path):
        self._path = os.path.abspath(path)
        self._name = os.path.basename(self._path)
        self._type = 'json'
        with codecs.open(path, encoding='utf-8') as fc:
            json_str = ''
            for line in fc:
                if not line.lstrip().startswith('//'):
                    json_str += line.rstrip('\n')
            jsn = json.loads(json_str)
            for key, value in jsn:
                key = key.upper()
                if self.is_valid_key(key):
                    value = self.cast(key, value)
                    self.__setattr__(key, value)
                else:
                    logging.warn('invalid key {0}'.format(key))
        return None

    def dump(self, path):
        with codecs.open(path, 'wb', encoding='utf-8') as fp:
            for key, value in self.__dict__.items():
                fp.write('%s=%s\n' % (key, value))
        return None

    def log(self, logger):
        logger.info('log config:')
        for key, value in self.__dict__.items():
            logger.info('%s=%s' % (key, value))

    def __str__(self):
        return str(self.__dict__)

    def __unicode__(self):
        return self.__str__()


def mkdir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return None


def init_log(logname, filename, level=logging.DEBUG, console=True):
    # make log file directory when not exist
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory)

    logger = logging.getLogger(logname)
    formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    fileHandler = logging.FileHandler(filename, mode='a')
    fileHandler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(fileHandler)
    if console:
        streamHandler = logging.StreamHandler()
        streamHandler.setFormatter(formatter)
        logger.addHandler(streamHandler)

    return logger


def file2dict(path,
              kn=0,
              vn=1,
              sep='\t',
              encoding='utf-8',
              ktype=None,
              vtype=None):
    """
    build a dict from a file.
    @param path: input file path
    @param kn: the column number of key
    @param vn: the column number of value
    @param sep: the field seperator
    @param encoding: the input encoding
    @return: a key value dict

    """
    d = {}
    with codecs.open(path, encoding=encoding) as fp:
        for line in fp:
            tokens = line.rstrip().split(sep)
            try:
                key = tokens[kn]
                if ktype:
                    key = ktype(key)
                value = tokens[vn]
                if vtype:
                    value = vtype(value)
                d[key] = value
            except IndexError:
                logging.exception('invalid line: %s' % line)
    return d


def file2set(path, n=0, sep='\t', encoding='utf-8', typ=None):
    """
    build a set from a file.
    @param path: input file path
    @param kn: the column number of key
    @param sep: the field seperator
    @param encoding: the input encoding
    @return: a set

    """
    d = set()
    with codecs.open(path, encoding=encoding) as fp:
        for line in fp:
            tokens = line.rstrip().split(sep)
            try:
                value = tokens[n]
                if typ:
                    value = typ(value)
                d.add(value)
            except IndexError:
                logging.exception('invalid line: %s' % line)
    return d


def cout(s, encoding='utf-8', newline=True):
    sys.stdout.write(s.encode(encoding))
    if newline:
        sys.stdout.write('\n')
    return None


def print_list(lst):
    for e in lst:
        p(e)
    return None


def print_matrix(matrix):
    for lst in matrix:
        print_list(lst)
    return None


def p(obj, encoding='utf-8', indent=0):
    indent = indent
    typ = type(obj)
    if typ == str or typ == unicode:
        logging.info(' ' * indent, )
        logging.info(obj.encode(encoding))
    elif typ == list or typ == tuple:
        for e in obj:
            p(e, indent=indent)
    elif typ == dict or typ == defaultdict:
        indent += 4
        for k, v in obj.items():
            p(k)
            p(v, indent=indent)
    else:
        logging.info(obj)
    return None


def splite_sentence(text):
    long_sep = u'\x03\x04。！？；!?;'
    short_sep = u'，,:： '
    long_sents = []
    offset_begin = 0
    short_sents = []
    for i, e in enumerate(text):
        if e in short_sep:
            short_sents.append(text[offset_begin:i + 1])
            offset_begin = i + 1
        elif e in long_sep:
            short_sents.append(text[offset_begin:i + 1])
            long_sents.append(short_sents)
            short_sents = []
            offset_begin = i + 1
        else:
            pass
    if offset_begin != len(text):
        short_sents.append(text[offset_begin:])
    if short_sents:
        long_sents.append(short_sents)
    return long_sents


def file_line_num(path, encoding='utf-8'):
    with codecs.open(path, encoding=encoding) as fp:
        for i, _ in enumerate(fp):
            pass
    return i + 1


def timer(func, logger=None):
    def wrapper(*arg, **kw):
        t1 = time.time()
        func(*arg, **kw)
        t2 = time.time()
        infomation = '%0.4f sec %s' % ((t2 - t1), func.func_code)
        if logger:
            logger.info(infomation)
        else:
            sys.stderr.write('%s\n' % infomation)
        return None

    return wrapper


def load_matrix(path, skip_lines=0):
    matrix = []
    with open(path) as f:
        # skip the head lines
        for i in range(skip_lines):
            f.readline()
        for line in f.readlines():
            row = [float(e) for e in line.split()]
            matrix.append(row)
    return matrix


def dump_matrix(matrix, path, headlines=[]):
    with open(path, 'wb') as out:
        for line in headlines:
            out.write(line)
            out.write(os.linesep)
        for row in matrix:
            out.write(' '.join([str(e) for e in row]))
            out.write(os.linesep)
    logging.info('Finish writing matrix to %s' % path)
    return None


def pickle_me(obj, path, typ=None):
    with open(path, 'wb') as f:
        if typ == 'json':
            json.dump(obj, f)
        else:
            pickle.dump(obj, f)
    return None


def load_pickle(path, typ=None):
    with open(path) as f:
        if typ == 'json':
            return json.load(f)
        else:
            return pickle.load(f)


def xml2list(xml):
    ###### there is no lxml on hadoop ###########
    # try:
    #     # http://stackoverflow.com/questions/16396565/how-to-make-lxmls-iterparse-ignore-invalid-xml-charachters
    #     para = etree.XML(xml)
    # except etree.XMLSyntaxError:
    #     return None
    # subsent_list = para.xpath('//subsent/text()')
    # ret = [unicode(subsent) for subsent in subsent_list]
    # return ret
    ############################################

    try:
        para = ET.XML(xml.encode('utf-8'))
    except ET.ParseError:
        return None
    subsent_list = para.findall('./*/subsent')
    ret = [unicode(subsent.text) for subsent in subsent_list]
    return ret


def append_file(a, b, encoding='utf-8'):
    """
    append file a to file b
    """
    with codecs.open(a, 'rb', encoding=encoding) as fa, \
        codecs.open(b, 'ab', encoding=encoding) as fb:
        fb.write(fa.read())
    return None


class Answer(object):
    def __init__(self):
        self.sents = []
        self.query = ''
        self.url = ''


class Sentence(object):
    def __init__(self, s=''):
        self.query = ''
        self.s = s
        self.baseline = 0.0
        self.is_opinion = 0.0
        self.sent_sim_cooc = 0.0
        self.lexrank = 0.0
        self.word2vec = 0.0
        self.score = 0.0

    def __eq__(self, other):
        if isinstance(other, Sentence):
            return (self.query == other.query and self.s == other.s)
        else:
            return False

    def __ne__(self, other):
        return (not self.__eq__(other))

    def __hash__(self):
        return hash(self.query + self.s)


def gaussian(x, mu, sig):

    ret = np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.)))
    return ret


def gaussian_list(a):
    """
    a: a numpy array
    """
    if len(a) <= 1:
        return a
    mu = a.mean()
    sig = np.sqrt(np.sum((a - mu)**2) / len(a))
    return gaussian(a, mu, sig)


def median(lst):
    return sorted(lst)[len(lst) / 2]


def chunk(iterable, size):
    if not iterable:
        return []
    ret = []
    begin_idx = 0
    for i, e in enumerate(iterable):
        if i != 0 and i % size == 0:
            ret.append(iterable[begin_idx:i])
            begin_idx = i
    # append the last part
    ret.append(iterable[begin_idx:])
    return ret


def test_chunk():
    assert chunk([], 2) == []
    assert chunk([1], 2) == [[1]]
    assert chunk([1, 2], 2) == [[1, 2]]
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def is_number(s):
    try:
        f = float(s)
        return True
    except ValueError:
        return False


def find_host(s):
    found = HOST_PATTEN.findall(s)
    return found


def url2host(url):
    found = HOST_PATTEN.findall(url)
    if found:
        return found[0]
    else:
        return None
