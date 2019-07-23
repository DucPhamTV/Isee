
"""ICleaner class
- Observe directory files size and delete old files if needed
"""
import os
from collections import namedtuple

FileObj = namedtuple('FileObj', ['file_path', 'size', 'creation_time'])

class Icleaner(object):

    def __init__(self, storage_path, limit_size):
        self.path = storage_path
        self.limit = limit_size

    def _scan_storage(self):
        total_size = 0
        files = []
        for dirpath, dirnames, filenames in os.walk(self.storage_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    file_size = os.path.getsize(fp)
                    creation_time = os.path.getmtime()
                    total_size += file_size
                    files.append(FileObj(fp, file_size, creation_time))

        return total_size, files.sort(key= lambda x: x.creation_time)

    def _get_old_files(self, files_list, current_size, limit_size):
        for f in files_list:
            if current_size < limit_size:
                break

            current_size -= f.size
            yield f

    def cleaning(self):
        current_size, files_list = self._scan_storage()
        for f in self._get_old_files(files_list, current_size, current_size - 40 * 1024 * 1024):
            try:
                print("Info: removing {}".format(f.file_path))
                #os.remove(f.file_path)
            except OSError:
                print("Error: {} doesn't exist".format(f.file_path))

if __name__ == '__main__':
    storage_path = '/media/usb'
    limit_size = 5000000000
    cleaner = Icleaner(storage_path, limit_size)
    while True:
        cleaner.cleaning()
        time.sleep(5)
