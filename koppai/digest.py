# * Import
import glob
import argparse
import sys
import os
import csv

import subprocess
import hashlib
import exiftool
import conf

from collections import OrderedDict, defaultdict

# * Global variables


# * Index
class Index:
    ENUM_ADD_SUCCESS = 0
    ENUM_DUPLICATE = 1
    def __init__(self, rootpath, fieldnames):
        self.rootpath = rootpath
        self.index_path = f'{rootpath}/index.csv'
        self.duplicates_path = f'{rootpath}/duplicates_index.csv'
        self.index = {}
        self.fieldnames = fieldnames
        self.duplicates = defaultdict(list)

        self.load()
        
    def add(self, key, record):
        if key in self.index:
            print(f'file already exists: {record["original_path"]} with same hash {key}')
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
                    self.index[record[0]] = record
        except:
            pass
        
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
                    self.duplicates[record[0]].append(record)
        except:
            pass
            
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

def check_filepath(filename):
    if '|' not in filename:
        return True
    return False

# * Manager
class Manager:
    def __init__(self, args):
        self.index = Index(conf.KOPPAI_ROOT,
                           fieldnames = [
                               'short_hash',
                               'extension',
                               'original_path'
                           ])
        self._check_store()
        
    def _check_store(self):
        return self._check_path(conf.KOPPAI_ROOT)
    
    def _check_path(self, path):
        if not os.path.exists(path):
            print(f'koppai root {path} does not exist!')
            key  = input('want to create it? [Y/n]: ')
            if key.lower() == 'y':
                print('creating directory... ')
                os.makedirs(path)
                print('DONE.')
            else:
                print('cannot proceed further, exiting.... ')
                exit(0)

    def make_dest_path(self, short_hash):
        dest_path = '{}/{}/{}'.format(short_hash[-6:-4],
                                      short_hash[-4:-2],
                                      short_hash[-2:])
        dest_full_path = f'{conf.STORE_DIR}/{dest_path}'
        return dest_path, dest_full_path


    def add_file(self, filepath, move_p=False):
        filepath = os.path.abspath(filepath)
        ext = os.path.splitext(filepath)[1].strip('.')
        
        hash_ = hash_file(filepath)
        short_hash = hash_[-6:]
        dest_path, dest_full_path = self.make_dest_path(hash_)

        dest_path = f'{dest_path}.{ext}'
        dest_full_path = f'{dest_full_path}.{ext}'

        record = OrderedDict({
            'short_hash': short_hash,
            'extension' : ext,
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

    def add_dir(self, directory):
        paths = []
        for root, dirs, files in os.walk(directory):
            for name in files:
                path = self.add_file(os.path.join(root, name))
                paths.append(path)
            for name in dirs:
                path = self.add_dir(os.path.join(root, name))
                paths.extend(path)
        return paths

    def add(self, path):
        if os.path.isdir(path):
            dest_path = self.add_dir(path)
        elif os.path.isfile(path):
            dest_path = self.add_file(path)

        return dest_path

def parse_args():
    parser = argparse.ArgumentParser('vizhungi')
    subparsers = parser.add_subparsers()
    parser.add_argument('filepath',
                    help='path to the file; add or retrieve info about file')
    
    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('--task', default='add')

    info_parser = subparsers.add_parser('info')
    info_parser.add_argument('--task', default='info')
   
    return parser.parse_args()

# * entry            
if __name__ == '__main__':

    args = parse_args()
    manager = Manager(args)
    if args.task == 'add':
        path = manager.add(args.filepath)
        print('file: {} added to store addr: {}'.format(args.filepath, path))
    if args.task == 'info':
        manager.info(filepath)

    manager.index.save()
