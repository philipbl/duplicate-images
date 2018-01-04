import pymongo


class MongoDB(object):
    def __init__(self, path):
        super(MongoDB, self).__init__()
        self.client = pymongo.MongoClient(path)
        self.db = self.client.image_database.images

    def contains(self, file_name):
        return self.db.count({"_id": file_name}) > 0

    def insert(self, data):
        data['_id'] = data['file_name']
        self.db.insert_one(data)

    def remove(self, file_name):
        self.db.delete_one({'_id': file_name})

    def clear(self):
        self.db.drop()

    def all(self):
        return list(self.db.find())

    def count(self):
        return self.db.count()

    def find_duplicates(self, match_time):
        dups = self.db.aggregate([{
            "$group": {
                "_id": "$hash",
                "total": {"$sum": 1},
                "items": {
                    "$push": {
                        "file_name": "$_id",
                        "file_size": "$file_size",
                        "image_size": "$image_size",
                        "capture_time": "$capture_time"
                    }
                }
            }
        },
        {
            "$match": {
                "total": {"$gt": 1}
            }
        }])

        return list(dups)
