import exiftool
import glob
import argparse
import sys
import os
from tqdm import tqdm

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

from collections import defaultdict, Counter

def main(rootpath):

    filetypes = defaultdict(set)
    counter = defaultdict(int)
    
    with exiftool.ExifTool() as et:
        for filepath in tqdm(
                glob.glob(
                    rootpath + '**', recursive=True)):
            if not os.path.isfile(filepath):
                continue
            
            ext = os.path.splitext(filepath)[1].strip('.')
            if len(ext) > 6:
                ext = 'UNK'
            counter[ext] += 1
                
            try:
                metadata = et.execute_json(filepath)[0]
                filetypes[ext].add((
                    metadata['File:FileType'],
                    metadata['File:FileTypeExtension'],
                    metadata['File:MIMEType']
                ))
                
            except KeyboardInterrupt:
                raise KeyboardInterruptXS
            except:
                log.exception(filepath)
    return filetypes, counter



if __name__ == '__main__':

    if  len(sys.argv) < 2:
        print('gimme more!')
        exit(0)

    filetypes, counter = main(sys.argv[1])

    with open('filetypes.csv', 'w') as f:
        print('Extension', '\t', 'Type','\t', 'Ext' '\t', 'MIME' '\t', 'Count', file=f)
        for ext, fts in filetypes.items():
            for ft in fts:
                print(ext, '\t', '\t'.join([str(i) for i in ft]), '\t', counter[ext], file=f)
