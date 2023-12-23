# * imports
import re
import subprocess
from datetime import datetime

# * custom imports
import conf

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
        
        command = f'yt-dlp {url} -o "{dest_path}"'
        print(command)
        output = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE
        ).stdout.read()
        

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
        return YoutubeDl()
    else:
        return Downloader()
    
# * entry

if __name__ == "__main__":
    #args = parser_args()

    with open(conf.FEED_PATH) as f:
        for line in f:
            timestamp, url = line.split('--', 1)
            timestamp =  datetime.strptime(timestamp.strip(), conf.TIMESTAMP_FORMAT)
            downloader = find_downloader(url)
            downloader.download(url, timestamp.isoformat(timespec='seconds'))
