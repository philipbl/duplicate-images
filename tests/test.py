import os
import shutil

import mongomock
import pyfakefs.fake_filesystem as fake_fs
import pytest

import duplicate_finder
from duplicate_finder import images, display, database
from duplicate_finder.database import mongodb, sqlite, tinydb


@pytest.fixture
def db():
    from duplicate_finder.database import sqlite
    path = 'tests/db.sqlite'
    db = sqlite.SQLite(path)

    yield db

    os.remove(path)


def test_get_image_files():
    images = ['tests/images/u.jpg', 'tests/images/file.png', 'tests/images/file.gif', 'tests/images/file.tiff',
              'tests/images/image.txt', 'tests/images/deeply/nested/different.jpg',
              'tests/images/deeply/nested/image/sideways.jpg', 'tests/images/deeply/nested/image/smaller.jpg']

    assert sorted(duplicate_finder.images.get_image_files('./tests')) == \
           sorted([os.path.abspath(x) for x in images])


def test_hash_file():
    image_name = 'tests/images/u.jpg'
    result = duplicate_finder.images.hash_file(image_name)
    assert result[1] is not None
    file_name, metadata = result

    assert file_name == metadata['file_name'] == image_name
    assert metadata['hash'] == '4b9e705db4450db6695cba149e2b2d65c3a950e13c7e8778e1cbda081e12a7eb'

    result = duplicate_finder.images.hash_file('tests/images/nothing.png')
    assert result[1] is None

    result = duplicate_finder.images.hash_file('tests/images/not_image.txt')
    assert result[1] is None


def test_hash_file_rotated():
    image_name_1 = 'tests/images/u.jpg'
    image_name_2 = 'tests/images/deeply/nested/image/sideways.jpg'

    result_1 = duplicate_finder.images.hash_file(image_name_1)
    result_2 = duplicate_finder.images.hash_file(image_name_2)

    assert result_1[1]['hash'] == result_2[1]['hash']


def test_hash_files_parallel():
    files = ['tests/images/u.jpg',
             'tests/images/nothing.png',
             'tests/images/not_image.txt',
             'tests/images/deeply/nested/different.jpg',
             'tests/images/deeply/nested/image/sideways.jpg',
             'tests/images/deeply/nested/image/smaller.jpg']
    results = duplicate_finder.images.hash_files(files, processes=4)

    results = list(results)
    assert len(results) == len(files)
    assert len([r for r in results if r[1] is not None]) == 4

    file, metadata = results[0]
    assert file == 'tests/images/u.jpg'
    assert metadata['hash'] == '4b9e705db4450db6695cba149e2b2d65c3a950e13c7e8778e1cbda081e12a7eb'

    results_1_process = duplicate_finder.images.hash_files(files, 1)
    results_1_process = list(results_1_process)
    assert results_1_process == results


def test_add_to_database(db):
    file_name = 'tests/images/u.jpg'

    _, result = duplicate_finder.images.hash_file(file_name)
    db.insert(result)

    db_results = db.all()
    assert len(db_results) == 1
    db_result = db_results[0]

    assert db_result == result

    # Duplicate entry should return an error
    with pytest.raises(Exception):
        db.insert(result)


def test_in_database(db):
    file_name = 'tests/images/u.jpg'

    _, result = duplicate_finder.images.hash_file(file_name)
    db.insert(result)

    assert db.contains(file_name)


def test_new_image_files(db):
    file_name = 'tests/images/u.jpg'

    _, result = duplicate_finder.images.hash_file(file_name)
    db.insert(result)

    # TODO: Finish this function. I am not sure what new_image_files is doing

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
    assert db_result['hash'] == '4b9e705db4450db6695cba149e2b2d65c3a950e13c7e8778e1cbda081e12a7eb'
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
    duplicate_finder.add(['tests/images/deeply/nested'], db)

    dups = duplicate_finder.find(db, match_time=False)
    assert len(dups) == 1

    dup = dups[0]
    assert dup['total'] == 2

    time_dups = duplicate_finder.find(db, match_time=True)
    assert dups == time_dups


def test_dedup():
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.add(['tests'], db)
    assert db.count() == 8

    dups = duplicate_finder.find(db, match_time=False)
    assert len(dups) == 2

    duplicate_finder.delete_duplicates(dups, db)

    dup = dups[0]

    # The first item should still be in its original place
    assert os.path.exists(dup['items'][0]['file_name'])

    # The rest of the files should be moved to the trash
    for item in dup['items'][1:]:
        assert not os.path.exists(item['file_name'])
        assert os.path.exists(os.path.join('Trash', os.path.basename(item['file_name'])))

    assert db.count() == 4

    # Move files back
    for dup in dups:
        for item in dup['items'][1:]:
            shutil.move(os.path.join('Trash', os.path.basename(item['file_name'])),
                        item['file_name'])
    os.rmdir('Trash')
