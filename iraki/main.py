# * imports
import os
import re
import subprocess
import argparse
from datetime import datetime

# * custom imports
import conf

# * necessary utils
def get_timestamp_as_filename(timestamp=None):
    if not timestamp:
        timestamp = datetime.now()
    filename = timestamp.isoformat(timespec='seconds')
    filename = filename.replace(':', '-')
    return filename

# * logging
import logging
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

SESSION_START_TIME = datetime.now()
SESSION_ID = get_timestamp_as_filename(SESSION_START_TIME)
LOG_FILE = f'{conf.LOG_DIR}/{SESSION_ID}.log'

handler = logging.FileHandler(LOG_FILE)        
handler.setFormatter(formatter)

log = logging.getLogger()
log.setLevel(logging.DEBUG)
log.addHandler(handler)

# * Downloaders
class Downloader:
    def __init__(self):
        pass
    def download(self, url, prefix):
        pass

class YoutubeDl(Downloader):
    def download(self, url, prefix):
        url = url.strip()
        dest_path = get_dest_path(
            filename='%(title)s-%(id)s',
            timestamp=prefix,
            tags=['video'],
            ext="%(ext)s")
        
        command = f'yt-dlp "{url}" -o "{dest_path}"'
        print(command)
        output = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE
        ).stdout.read()
        

class GitSourceDownloader(Downloader):
    def __init__(self, root='/home/vanangamudi/code/git'):
        self.root = root
        
    def download(self, url, prefix):
        # example url: https://github.com/vanangamudi/aalar.git
        url = url.strip()
        url_parts = re.match(
            "((?P<protocol>https?)://)?(?P<site>\w+)\.(?P<tld>\w+)/(?P<user_org>[\w\-]+)/(?P<repo>[\w\-]+)(|\.git)",
            url)

        dest_path = '{prefix}/{site}/{user_org}/{repo}'.format(prefix=self.root,
                                                               **url_parts.groupdict())
        try:
            print(dest_path)
            os.makedirs(dest_path, exist_ok=True)
            command = f'git clone {url} "{dest_path}"'
            print(command)
            output = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE
            ).stdout.read()

        except:
            log.exception(dest_path)
            
# * functions
def get_dest_path(filename, timestamp, tags, ext=None):
    if ext is None:
        filename, ext = os.path.split()
        
    tags = "-".join([
        t.lower() for t in tags
    ])
    
    return f'{conf.DOWNLOAD_DIR}/{timestamp}--{filename}--{tags}.{ext}'

def find_downloader(url):
    if re.search('^https?://\w+.youtube.com/', url.strip()):
        print(f'YoutubeDl for {url}')
        return YoutubeDl()
    elif re.search("git(hub|lab)\.(com|org)", url):
        print(f'GitSourceDownloader for {url}')
        return GitSourceDownloader()
    else:
        return Downloader()
    
# * entry
def parse_args():
    parser = argparse.ArgumentParser('iraki')
    parser.add_argument('--verbose', '-v', action='store_true')
    
    parser.add_argument('--url-filter-regex', '-r',
                        help = 'url that do not match the regex will be filtered out',
                        default=None)
   
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    with open(conf.FEED_PATH) as f:
        for line in f:
            timestamp, url = line.strip().split('--', 1)
            if args.url_filter_regex and not re.search(args.url_filter_regex, url):
                continue

            log.info(f'processing {url}...')
            timestamp =  datetime.strptime(timestamp.strip(), conf.TIMESTAMP_FORMAT)
            downloader = find_downloader(url)
            downloader.download(url, timestamp.isoformat(timespec='seconds'))
