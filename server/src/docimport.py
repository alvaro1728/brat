#!/usr/bin/env python

from __future__ import with_statement

'''
Simple interface to for importing files into the data directory.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
Version:    2011-02-21
'''

from httplib import HTTPConnection
from socket import error as SocketError
from urlparse import urlparse

from annotation import open_textfile
from common import ProtocolError
from config import DATA_DIR
from document import real_directory
from annotation import JOINED_ANN_FILE_SUFF, TEXT_FILE_SUFFIX
from os.path import join as join_path
from os.path import isdir, isfile
from os import access, remove, W_OK
from jsonwrap import loads

### Constants
DEFAULT_IMPORT_DIR = 'import'
###

class InvalidDirError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'Invalid directory'

    def json(self, json_dic):
        json_dic['exception'] = 'invalidDirError'
        return json_dic


class FileExistsError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'File exists: %s' % self.path

    def json(self, json_dic):
        json_dic['exception'] = 'fileExistsError'
        return json_dic


class NoWritePermissionError(ProtocolError):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return 'No write permission to %s' % self.path

    def json(self, json_dic):
        json_dic['exception'] = 'noWritePermissionError'
        return json_dic

class InvalidConnectionSchemeError(ProtocolError):
    def __init__(self, url, scheme):
        self.url = url
        self.scheme = scheme

    def __str__(self):
        return ('The URL "%s" uses the unsupported scheme "%s"'
                ' "%s"') % (self.url, self.scheme, )

    def json(self, json_dic):
        json_dic['exception'] = 'invalidConnectionSchemeError'

class HttpError(ProtocolError):
    def __init__(self, method, url, error):
        self.method = method
        self.url = url
        self.error = error

    def __str__(self):
        return ('HTTP %s request to %s failed. %s'
                % (self.method, self.url, self.error, ))

    def json(self, json_dic):
        json_dic['exception'] = 'httpError'

class FormatError(ProtocolError):
    def __init__(self, url, error):
        self.url = url
        self.error = error

    def __str__(self):
        return ('Format error with response from %s. %s'
                % (self.url, self.error, ))

    def json(self, json_dic):
        json_dic['exception'] = 'formatError'

#TODO: Chop this function up
def save_import(text, docid, collection=None):
    '''
    TODO: DOC:
    '''

    directory = collection

    if directory is None:
        dir_path = DATA_DIR
    else:
        #XXX: These "security" measures can surely be fooled
        if (directory.count('../') or directory == '..'):
            raise InvalidDirError(directory)

        dir_path = real_directory(directory)

    # Is the directory a directory and are we allowed to write?
    if not isdir(dir_path):
        raise InvalidDirError(dir_path)
    if not access(dir_path, W_OK):
        raise NoWritePermissionError(dir_path)

    base_path = join_path(dir_path, docid)
    txt_path = base_path + '.' + TEXT_FILE_SUFFIX
    ann_path = base_path + '.' + JOINED_ANN_FILE_SUFF

    # Before we proceed, verify that we are not overwriting
    for path in (txt_path, ann_path):
        if isfile(path):
            raise FileExistsError(path)

    # Make sure we have a valid POSIX text file, i.e. that the
    # file ends in a newline.
    if text != "" and text[-1] != '\n':
        text = text + '\n'

    with open_textfile(txt_path, 'w') as txt_file:
        txt_file.write(text)

    # Touch the ann file so that we can edit the file later
    with open(ann_path, 'w') as _:
        pass

    return { 'document': docid }

def getApiData(apiUrl):
    url_soup = urlparse(apiUrl)

    if url_soup.scheme == 'http':
        Connection = HTTPConnection
    elif url_soup.scheme == 'https':
        from httplib import HTTPSConnection
        Connection = HTTPSConnection

    conn = None
    try:
        conn = Connection(url_soup.netloc)
        req_headers = {
            'Accept': 'application/json',
        }
        try:
            conn.request('GET', str(apiUrl), None, headers=req_headers)
        except SocketError, e:
            raise HttpError('GET', apiUrl, e)
        resp = conn.getresponse()

        # Did the request succeed?
        if resp.status != 200:
            raise HttpError('GET', apiUrl, '%s %s' % (resp.status, resp.reason))
        # Finally, we can read the response data
        resp_data = resp.read()
    finally:
        if conn is not None:
            conn.close()
    return resp_data

def getFileData(location):
    with open(location, 'r') as testFile:
        json = testFile.read().replace('\n', '')
    return json

def save_web_page_import(url, docid, overwrite, collection=None):
    '''
    TODO: DOC:
    '''

    directory = collection

    if directory is None:
        dir_path = DATA_DIR
    else:
        #XXX: These "security" measures can surely be fooled
        if (directory.count('../') or directory == '..'):
            raise InvalidDirError(directory)

        dir_path = real_directory(directory)

    # Is the directory a directory and are we allowed to write?
    if not isdir(dir_path):
        raise InvalidDirError(dir_path)
    if not access(dir_path, W_OK):
        raise NoWritePermissionError(dir_path)

    base_path = join_path(dir_path, docid)
    txt_path = base_path + '.' + TEXT_FILE_SUFFIX
    ann_path = base_path + '.' + JOINED_ANN_FILE_SUFF

    # Before we proceed, verify that we are not overwriting
    for path in (txt_path, ann_path):
        if isfile(path):
            if not overwrite or overwrite == 'false':
                raise FileExistsError(path)
            remove(path)

    apiUrl = 'http://api-ie.qna.bf2.yahoo.com:4080/ie_ws/v1/ie_ws?url=' + url
    data = getApiData(apiUrl)

    # location = join_path(dir_path, 'input.json')
    # data = getFileData(location)

    try:
        json_resp = loads(data)
    except ValueError, e:
        raise FormatError(apiUrl, e)

    # Make sure we have a valid POSIX text file, i.e. that the
    # file ends in a newline.
    response = json_resp[1]
    text = response['doc']
    if text != "" and text[-1] != '\n':
        text = text + '\n'

    with open_textfile(txt_path, 'w') as txt_file:
        txt_file.write(text)

    annotations = ""
    index = 1
    for sentence in response['annotatedSentences']:
        for annotation in sentence['spans']:
            if len(annotation['tokens']) > 0:
                token = annotation['tokens'][0]

                type = token['namedEntity']
                if len(annotation['annotations']) > 0:
                    type = annotation['annotations'].keys()[0].split('.')[-1]

                annotations += 'T' + str(index) + '\t' + str(type) + ' ' + str(token['start']) + ' ' + str(token['end']) + '\t' + str(token['word']) + '\n'
                index += 1

    with open_textfile(ann_path, 'w') as ann_file:
        ann_file.write(annotations)
    return { 'document': docid }

if __name__ == '__main__':
    # TODO: Update these to conform with the new API
    '''
    from unittest import TestCase
    from tempfile import mkdtemp
    from shutil import rmtree
    from os import mkdir


    class SaveImportTest(TestCase):
        test_text = 'This is not a drill, this is a drill *BRRR!*'
        test_dir = 'test'
        test_filename = 'test'

        def setUp(self):
            self.tmpdir = mkdtemp()
            mkdir(join_path(self.tmpdir, SaveImportTest.test_dir))
            mkdir(join_path(self.tmpdir, DEFAULT_IMPORT_DIR))

        def tearDown(self):
            rmtree(self.tmpdir)

        def test_import(self):
            save_import(SaveImportTest.test_text, SaveImportTest.test_filename,
                    relative_dir=SaveImportTest.test_dir,
                    directory=self.tmpdir)
        
        def test_default_import_dir(self):
            save_import(SaveImportTest.test_text, SaveImportTest.test_filename,
                    directory=self.tmpdir)
   

    import unittest
    unittest.main()
    '''
