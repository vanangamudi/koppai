# * Standard Import
import glob
import argparse
import sys
import os
import csv

import re
import json
import subprocess
import hashlib
import pathlib
import logging

from datetime import datetime
from collections import OrderedDict, defaultdict
from pprint import pformat, pprint

# * third party libraries
import exiftool
from pypdf import PdfWriter, PdfReader

# * imports
import conf

# * Global variables


# * logging
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

SESSION_ID = datetime.now().isoformat(timespec='seconds')
LOG_FILE = f'{conf.LOG_DIR}/{SESSION_ID}.log'

handler = logging.FileHandler(LOG_FILE)        
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.INFO)
log.addHandler(handler)

# * Index
def _check_path(path, name):
    if not os.path.exists(path):
        print(f'{name} {path} does not exist!')
        key  = input('want to create it? [Y/n]: ')
        if key.lower() == 'y':
            print('creating {name} directory... ')
            os.makedirs(path)
            print('DONE.')
        else:
            print('cannot proceed further, exiting.... ')
            exit(0)

class Index:
    ENUM_ADD_SUCCESS = 0
    ENUM_DUPLICATE = 1
    def __init__(self, rootpath, name, fieldnames):
        self.rootpath = rootpath
        self.name = name
        self.index = {}
        self.fieldnames = fieldnames
        self.duplicates = defaultdict(list)

        self.index_path = f'{conf.INDEX_DIR}/{name}.csv'
        self.duplicates_path = f'{conf.INDEX_DIR}/{name}_duplicates.csv'

        _check_path(conf.INDEX_DIR, 'index directory')
        self.load()
                
    def add(self, key, record):
        if key in self.index:
            duplicate = self.index[key]
            if not duplicate['original_path'] == record['original_path']:
                print(f'file already exists:\
                {record["original_path"]} with same hash {key}\
                form {duplicate["original_path"]}')
                
                self.duplicates[key].append(record)
            return self.ENUM_DUPLICATE
        else:
            self.index[key] = record
            return self.ENUM_ADD_SUCCESS
    
    def remove(self, key):
        record = self.index[key]
        del self.index[key]
        return record
    
    def read_index(self):
        try:
            with open(self.index_path) as ip:
                reader = csv.DictReader(ip, fieldnames=self.fieldnames)
                for record in reader:
                    self.index[record['short_hash']] = record
        except:
            log.exception('reading index')
        
    def write_index(self):
        with open(self.index_path, 'w') as of:
            writer = csv.DictWriter(of, fieldnames=self.fieldnames)
            writer.writeheader()
            for values in self.index.values():
                writer.writerow(values)
                
    def write_duplicates(self,):
        with open(self.duplicates_path, 'w') as of:
            writer = csv.DictWriter(of, fieldnames=self.fieldnames)
            writer.writeheader()
            for key in self.duplicates.keys():
                for values in self.duplicates[key]:
                    writer.writerow(values)
                    
    def read_duplicates(self):
        try:
            with open(self.duplicates_path) as ip:
                reader = csv.DictReader(ip, fieldnames=self.fieldnames)
                for record in reader:
                    self.duplicates[record['short_hash']].append(record)
        except:
            log.exception('reading duplicates')
            
    def save(self):
        self.write_index()
        self.write_duplicates()

    def load(self):
        self.read_index()
        self.read_duplicates()

# * Process files for metadata
def parse_exif(filepath):
    with exiftool.ExifTool() as et:
        try:
            return et.execute_json(filepath)[0]
        except:
            log.exception(filepath)
            
def hash_file(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest()

def hash_string(string_, encoding='utf-8'):
    return hashlib.sha256(string_.encode(encoding)).hexdigest()

def hash_dict(dict_):
    return hash_string(json.dumps(dict_))
    
def get_dir_structure(path):
    dir_structure = {
        'name': os.path.basename(path)
    }
    
    if os.path.isfile(path):
        dir_structure['type'] = "file"
    else:
        dir_structure['type'] = "directory"
        dir_structure['children'] = [
            get_dir_structure(os.path.join(path, name))
            for name in os.listdir(path)
        ]
                
    return dir_structure

def get_tags(path):
    return ['tag', 'tag list']

def check_filepath(filename):
    if '|' not in filename:
        return True
    return False

def sanitize_text(text):
    text = re.sub('&#x.*?;', '', text)
    text = re.sub('[/\\?%*:|"<>]', '', text)
    return text
        
def make_good_filename(filepath):
    name = os.path.basename(filepath)
    if os.path.splitext(filepath)[1].lower().strip('.') == 'pdf':
        with open(filepath, 'rb') as f:
            try:
                pdf_reader = PdfReader(f) 
                name = pdf_reader.metadata.title
            except:
                log.exception(filepath)
    if not name:
        name = os.path.basename(os.path.splitext(filepath)[0])
    name = re.sub(r'\s+', ' ', name)
    name = name.lower().replace(' ', '-')
    return name

# * Manager
class Manager:
    def __init__(self, args):
        self.args = args
        self.session_id = datetime.now().isoformat(timespec='seconds')
        self.index = Index(
            conf.KOPPAI_ROOT,
            name='files',
            fieldnames = [
                'short_hash',
                'extension',
                'path',
                'original_path',

            ])
        
        self.dir_structure_index = Index(
            conf.KOPPAI_ROOT,
            name='directory_structure',
            fieldnames=[
                'dir_hash',
                'collection',
                'structure_json'
            ]
        )
        self._check_store()

    def _check_store(self):
        return _check_path(conf.KOPPAI_ROOT, 'root directory')
    
    def make_dest_path(self, short_hash):
        dest_path = '{}/{}/{}'.format(short_hash[-6:-4],
                                      short_hash[-4:-2],
                                      short_hash[-2:])
        dest_full_path = f'{conf.STORE_DIR}/{dest_path}'
        return dest_path, dest_full_path


    def add_file(self, filepath, dir_hash, move_p=False):
        filename = os.path.basename(filepath)
        filepath = os.path.abspath(filepath)
        ext = os.path.splitext(filepath)[1].strip('.')
        
        hash_ = hash_file(filepath)
        short_hash = hash_[-6:]
        dest_path, dest_full_path = self.make_dest_path(hash_)

        mtime = datetime.fromtimestamp(
            os.path.getmtime(filepath)).isoformat(timespec="seconds")

        tags = get_tags(filepath)
        tags = '-'.join([
            tag
            .replace(' ', '')
            .lower()
            for tag in tags
        ])

        filename = make_good_filename(filepath)
        new_name = f'{mtime}--{filename}--{dir_hash}--{tags}.{ext}'
        
        dest_path = f'{dest_path}/{new_name}'
        dest_full_path = f'{dest_full_path}/{new_name}'

        record = OrderedDict({
            'short_hash': short_hash,
            'extension' : ext,
            'path': dest_full_path,
            'original_path' : filepath,
        })
        
        if self.index.add(short_hash, record) == Index.ENUM_DUPLICATE:
            return self.index.index[short_hash]
        else:
            command = "cp -p"
            if move_p:
                command = "mv"

            if False:
                subprocess.Popen(
                    f'{command} filepath {dest_path}',
                    shell=True,
                    stdout=subprocess.PIPE
                ).stdout.read()

            self.index.add(record['short_hash'], record)
            self.index.write_index()
            return dest_path

    def add_dir(self, directory, dir_hash, collection):
        paths = []
        for root, dirs, files in os.walk(directory):
            for name in files:
                path = self.add_file(os.path.join(root, name),
                                     dir_hash)
                paths.append(path)
            for name in dirs:
                path = self.add_dir(os.path.join(root, name),
                                    dir_hash,
                                    collection)
                paths.extend(path)
        return paths

    def add(self, path, collection):
        path = os.path.abspath(path)
        if os.path.isdir(path):
            dir_structure = get_dir_structure(path)
            dir_hash = hash_dict(dir_structure)
            dir_hash = dir_hash[-6:]
            self.dir_structure_index.add(dir_hash, {
                'dir_hash': dir_hash,
                'collection': collection,
                'structure': json.dumps(dir_structure)
            })

            dest_path = self.add_dir(path, dir_hash, collection)
        elif os.path.isfile(path):
            dest_path = self.add_file(path)

        return dest_path
    
    def info(self, query):
        return self.index.index[query]

def parse_args():
    parser = argparse.ArgumentParser('vizhungi')
    subparsers = parser.add_subparsers()
    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('--task', default='add')
    add_parser.add_argument('filepath',
                    help='path to the file; add or retrieve info about file')
    add_parser.add_argument('collection',
                        help='collection name',
                        default='general')
    

    info_parser = subparsers.add_parser('info')
    info_parser.add_argument('--task', default='info')
    info_parser.add_argument('query')
   
    return parser.parse_args()

# * entry            
if __name__ == '__main__':

    args = parse_args()
    pprint(args)
    manager = Manager(args)
    if args.task == 'add':
        path = manager.add(args.filepath, args.collection)
        #print('file: {} added to store addr: {}'.format(args.filepath, path))
    if args.task == 'info':
        pprint(manager.info(args.query))

    manager.index.save()
