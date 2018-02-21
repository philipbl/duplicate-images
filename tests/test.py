import os
import shutil

import mongomock
import pyfakefs.fake_filesystem as fake_fs
import pytest

import duplicate_finder


def test_get_image_files():
    images = ['tests/images/u.jpg', 'tests/images/file.png', 'tests/images/file.gif', 'tests/images/file.tiff',
              'tests/images/image.txt', 'tests/images/deeply/nested/different.jpg',
              'tests/images/deeply/nested/image/sideways.jpg', 'tests/images/deeply/nested/image/smaller.jpg']
    other = ['tests/images/not_image.txt', 'tests/images/not_image.jpb', 'README.md']

    assert sorted([str(x).rsplit('/', 1)[1] for x in duplicate_finder.get_image_files('.')]) == \
           sorted([str(x).rsplit('/', 1)[1] for x in images])


def test_hash_file():
    image_name = 'tests/images/u.jpg'
    result = duplicate_finder.hash_file(image_name)
    assert result is not None
    file, hash_, file_size, image_size, capture_time = result

    assert file == image_name
    assert hash_ == '4b9e705db4450db6695cba149e2b2d65c3a950e13c7e8778e1cbda081e12a7eb'

    result = duplicate_finder.hash_file('tests/images/nothing.png')
    assert result is None

    result = duplicate_finder.hash_file('tests/images/not_image.txt')
    assert result is None


def test_hash_file_rotated():
    image_name_1 = 'tests/images/u.jpg'
    image_name_2 = 'tests/images/deeply/nested/image/sideways.jpg'

    result_1 = duplicate_finder.hash_file(image_name_1)
    result_2 = duplicate_finder.hash_file(image_name_2)

    assert result_1[1] == result_2[1]


def test_hash_files_parallel():
    files = ['tests/images/u.jpg',
             'tests/images/nothing.png',
             'tests/images/not_image.txt',
             'tests/images/deeply/nested/different.jpg',
             'tests/images/deeply/nested/image/sideways.jpg',
             'tests/images/deeply/nested/image/smaller.jpg']
    results = duplicate_finder.hash_files_parallel(files)
    results = list(results)
    assert len(results) == 4

    file, hash_, file_size, image_size, capture_time = results[0]
    assert file == 'tests/images/u.jpg'
    assert hash_ == '4b9e705db4450db6695cba149e2b2d65c3a950e13c7e8778e1cbda081e12a7eb'


    duplicate_finder.NUM_PROCESSES = 1
    results_1_process = duplicate_finder.hash_files_parallel(files)
    results_1_process = list(results_1_process)
    assert results_1_process == results


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
