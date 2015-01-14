#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
import logging


def file2dict(path, kn=0, vn=1, sep='\t', encoding='utf-8'):
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
            tokens = line.rstrip('\n').split(sep)
            try:
                key = tokens[kn]
                value = tokens[vn]
            except IndexError:
                logging.exception(line)
                continue
            d[key] = value
    return d


def mkdir(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return None

def p(s, encoding='utf-8'):
    print s.encode(encoding)