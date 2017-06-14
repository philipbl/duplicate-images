import os

import pyfakefs.fake_filesystem as fake_fs
import duplicate_finder
import mongomock


def test_get_image_files(fs):
    images = ['/file.jpg', '/file.jpeg', '/file.png', '/file.gif',
              '/file.tiff', '/test/1/2/3/file.jpg']
    other = ['/file.txt', '/file.md']

    for x in images + other:
        fs.CreateFile(x)

    assert sorted(list(duplicate_finder.get_image_files('/'))) == sorted(images)


def test_hash_file():
    image_name = 'tests/images/u.jpg'
    result = duplicate_finder.hash_file(image_name)
    assert result != None
    file, hash_, file_size, image_size, capture_time = result

    assert file == image_name
    assert hash_ == '4b9e705db4470db4695c7a14166b2d6dc3a9d0e13c3e87b8e1cbda081e1aa7e9'

    result = duplicate_finder.hash_file('tests/images/nothing.png')
    assert result == None

    result = duplicate_finder.hash_file('tests/images/not_image.txt')
    assert result == None


def test_hash_files_parallel():
    results = duplicate_finder.hash_files_parallel(['tests/images/u.jpg',
                                                    'tests/images/nothing.png',
                                                    'tests/images/not_image.txt'])
    results = list(results)
    assert len(results) == 1

    file, hash_, file_size, image_size, capture_time = results[0]
    assert file == 'tests/images/u.jpg'
    assert hash_ == '4b9e705db4470db4695c7a14166b2d6dc3a9d0e13c3e87b8e1cbda081e1aa7e9'


def test_add_to_database():
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    db_result = db.find_one({'_id' : result[0]})

    assert result[0] == db_result['_id']
    assert result[1] == db_result['hash']
    assert result[2] == db_result['file_size']
    assert result[3] == db_result['image_size']
    assert result[4] == db_result['capture_time']

    # Duplicate entry should print out an error
    duplicate_finder._add_to_database(*result, db=db)


def test_in_database():
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    assert duplicate_finder._in_database('tests/images/u.jpg', db)


def test_new_image_files():
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    results = duplicate_finder.new_image_files(['tests/images/u.jpg', 'another_file'], db)
    results = list(results)

    assert len(results) == 1
    assert results == ['another_file']


def test_add():
    file_name = '{}/tests/images/u.jpg'.format(os.getcwd())
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)

    db_result = db.find_one({'_id' : file_name})
    assert db_result['_id'] == file_name
    assert db_result['hash'] == '4b9e705db4470db4695c7a14166b2d6dc3a9d0e13c3e87b8e1cbda081e1aa7e9'
    assert db.count() > 0


def test_remove():
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)
    assert db.count() > 0
    duplicate_finder.remove(['test'], db)
    assert db.count() > 0

    duplicate_finder.remove(['tests'], db)
    assert db.count() == 0

    duplicate_finder.remove(['tests'], db)
    assert db.count() == 0


def test_clear():
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)

    assert db.count() > 0
    duplicate_finder.clear(db)
    assert db.count() == 0


def test_find():
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.add(['tests'], db)

    dups = duplicate_finder.find(db, match_time=False)
    assert len(dups) == 1

    dup = dups[0]
    assert dup['total'] == 3

    time_dups = duplicate_finder.find(db, match_time=True)
    assert dups == time_dups
