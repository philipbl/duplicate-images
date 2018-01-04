from collections import Counter

import tinydb


class TinyDB(object):
    def __init__(self, path):
        super(TinyDB, self).__init__()
        self.db = tinydb.TinyDB(path)

    def contains(self, file_name):
        return self.db.contains(tinydb.where('file_name') == file_name)

    def insert(self, data):
        self.db.insert(data)

    def remove(self, file_name):
        item = self.db.get(tinydb.where('file_name') == file_name)
        self.db.remove(doc_ids=[item.doc_id])

    def clear(self):
        self.db.purge()

    def all(self):
        return self.db.all()

    def count(self):
        return len(self.db)

    def find_duplicates(self, match_time):
        items = self.db.all()
        counter = Counter([item['hash'] for item in items])
        Image = tinydb.Query()
        dups = []

        for item in counter:
            if counter[item] < 2:
                # No duplicates
                continue

            # Collect up all of the duplicate documents
            dups.append({'total': counter[item],
                         'items': self.db.search(Image.hash == item)})

        return dups

