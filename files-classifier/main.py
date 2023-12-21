import glob
import exiftool
from tqdm import tqdm
import sqlite3

from pymongo import MongoClient


import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


Registry = {
    'metadata_extractors' : {
        'pdf' : 'exiftool',
        'jpg|png|webp' : 'exiftool'
    }
}

def find_all_keys():
    failed = []
    with exiftool.ExifToolHelper() as et:
        attrs  ={}
        for filepath in tqdm(glob.glob(
                "/home/vanangamudi/ko-pa-ni/**",
                recursive=True)):
            try:
                attrs[filepath] = et.get_metadata(filepath)[0]
            except:
                failed.append(filepath)

    all_keys = []
    for filepath, metadata in attrs.items():
        all_keys.extend(metadata.keys())
        all_keys = list(set(all_keys))

    import csv

    all_keys = ["filepath"] + all_keys
    with open('metadata.tsv', 'w') as output_file:
        writer = csv.DictWriter(output_file,
                                delimiter='\t',
                                fieldnames=all_keys)

        writer.writeheader()
        for filepath, metadata in attrs.items():
            metadata["filepath"] = filepath
            writer.writerow(metadata)


    with open('failed_files.txt', 'w') as of:
        of.write("\n".join(failed))

    with open('fieldnames.txt', 'w') as of:
        of.write("\n".join(all_keys))


        
MONGODB_HOST = "10.135.133.115"
MONGODB_PORT = 27017

client = MongoClient(MONGODB_HOST, MONGODB_PORT)

db = client.koppai
coll = db.exiftool

failed = []
with exiftool.ExifToolHelper() as et:
    for filepath in tqdm(glob.glob(
            "/home/vanangamudi/ko-pa-ni/**",
            recursive=True)):
        try:
            attrs = et.get_metadata(filepath)[0]
            #print(filepath)
            coll.insert_one(attrs)
        except:
            failed.append(filepath)
            log.exception(filepath)
            
