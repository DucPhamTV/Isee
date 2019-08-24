
"""ICleaner class
- Observe directory files size and delete old files if needed
"""
import os
from collections import namedtuple
import time

FileObj = namedtuple('FileObj', ['file_path', 'size', 'creation_time'])

class Icleaner(object):

    def __init__(self, storage_path, limit_size):
        self.path = storage_path
        self.limit = limit_size

    def _scan_storage(self):
        total_size = 0
        files = []
        for dirpath, dirnames, filenames in os.walk(self.path):
            for f in filenames:
                if not f.endswith('.ts'):
                    continue

                fp = os.path.join(dirpath, f)

                if not os.path.islink(fp):
                    file_size = os.path.getsize(fp)
                    creation_time = os.path.getmtime(fp)
                    total_size += file_size
                    files.append(FileObj(fp, file_size, creation_time))

        files.sort(key= lambda x: x.creation_time)
        print("Info: total size {0}, number of files {1}".format(total_size, len(files)))

        return total_size, files

    def _get_old_files(self, files_list, current_size, limit_size):
        for f in files_list:
            if current_size < limit_size:
                break

            current_size -= f.size
            yield f

    def cleaning(self):
        current_size, files_list = self._scan_storage()
        for f in self._get_old_files(files_list, current_size, self.limit):
            try:
                print("Info: removing {}".format(f.file_path))
                os.remove(f.file_path)
            except OSError:
                print("Error: {} doesn't exist".format(f.file_path))

if __name__ == '__main__':
    storage_path = '/home/pi/Monitor/NhaDuc'
    limit_size = 5000000000
    cleaner = Icleaner(storage_path, limit_size)
    while True:
        cleaner.cleaning()
        time.sleep(60)
