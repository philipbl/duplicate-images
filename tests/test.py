"""Autotest"""
import os
import shutil

import mongomock

import duplicate_finder


def test_get_image_files():
    """test_get_image_files"""
    images = ['u.jpg', 'u.heic', 'file.png', 'file.gif', 'file.tiff',
              'image.txt', 'deeply/nested/different.jpg',
              'deeply/nested/image/sideways.jpg', 'deeply/nested/image/smaller.jpg',
              'not_image.jpg', 'not_image.txt']

    assert sorted([
                str(x).rsplit('/tests/images/', 1)[1]
                for x in duplicate_finder.get_files('tests/images/')
            ]) == sorted([str(x) for x in images])


def test_hash_file():
    """test_hash_file"""
    image_name = 'tests/images/u.jpg'
    result = duplicate_finder.hash_file(image_name)
    assert result is not None
    file, (hashes, _) = result

    assert file == image_name
    assert hashes == [b'bin:b\xcfq\xb4*\x15\x9eJ\xf4n\xd9M\x83zG\x05',
                      b'img:\xc3\x95\n\x87<~\xe1\x1e', b'img:\xd2y\x0e\xba-\xa2\xb0=',
                      b'img:\x96:](i\xd4\xb4\xb6', b'img:\x87\xd3[\x10x\x18\xe5\xd7']

    result = duplicate_finder.hash_file('tests/images/nothing.png')
    assert result is None

    file, (hashes, _) = duplicate_finder.hash_file('tests/images/not_image.txt')
    assert hashes == [b'bin:\x9b-z\xdf\x0e\xde\x89\x8c\x062\xec\x87\xf6g\x01\xe8']


def test_hash_file_rotated():
    """test_hash_file_rotated"""
    image_name_1 = 'tests/images/u.jpg'
    image_name_2 = 'tests/images/deeply/nested/image/sideways.jpg'

    result_1 = duplicate_finder.hash_file(image_name_1)
    result_2 = duplicate_finder.hash_file(image_name_2)
    hashes_1 = result_1[1][0]
    hashes_2 = result_2[1][0]

    # filter only images hashes
    hashes_1 = list(filter(lambda hash: b'img:' in hash, hashes_1))
    hashes_2 = list(filter(lambda hash: b'img:' in hash, hashes_2))

    assert hashes_1.sort() == hashes_2.sort()


def test_hash_files_parallel():
    """test_hash_files_parallel"""
    files = ['tests/images/u.jpg',
             'tests/images/nothing.png',
             'tests/images/not_image.txt',
             'tests/images/deeply/nested/different.jpg',
             'tests/images/deeply/nested/image/sideways.jpg',
             'tests/images/deeply/nested/image/smaller.jpg']
    results = duplicate_finder.hash_files_parallel(files)
    results = list(results)
    assert len(results) == 5

    file, (hashes, _) = results[0]
    assert file == 'tests/images/u.jpg'
    assert hashes == [b'bin:b\xcfq\xb4*\x15\x9eJ\xf4n\xd9M\x83zG\x05',
                      b'img:\xc3\x95\n\x87<~\xe1\x1e', b'img:\xd2y\x0e\xba-\xa2\xb0=',
                      b'img:\x96:](i\xd4\xb4\xb6', b'img:\x87\xd3[\x10x\x18\xe5\xd7']

    duplicate_finder.NUM_PROCESSES = 1
    results_1_process = duplicate_finder.hash_files_parallel(files)
    results_1_process = list(results_1_process)
    assert results_1_process == results


def test_add_to_database():
    """test_add_to_database"""
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    db_result = db.find_one({'_id': result[0]})

    assert result[0] == db_result['_id']
    assert result[1][0] == db_result['hashes']
    assert result[1][1] == db_result['meta']

    # Duplicate entry should print out an error
    duplicate_finder._add_to_database(*result, db=db)


def test_in_database():
    """test_in_database"""
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    assert duplicate_finder._in_database('tests/images/u.jpg', db)


def test_new_files():
    """test_new_files"""
    db = mongomock.MongoClient().image_database.images
    result = duplicate_finder.hash_file('tests/images/u.jpg')
    duplicate_finder._add_to_database(*result, db=db)

    results = duplicate_finder.new_files(['tests/images/u.jpg', 'another_file'], db)
    results = list(results)

    assert len(results) == 1
    assert results == ['another_file']


def test_add():
    """test_add"""
    file_name = f'{os.getcwd()}/tests/images/u.jpg'
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)

    db_result = db.find_one({'_id': file_name})
    assert db_result['_id'] == file_name
    assert db_result['hashes'] == [b'bin:b\xcfq\xb4*\x15\x9eJ\xf4n\xd9M\x83zG\x05',
                                   b'img:\xc3\x95\n\x87<~\xe1\x1e', b'img:\xd2y\x0e\xba-\xa2\xb0=',
                                   b'img:\x96:](i\xd4\xb4\xb6', b'img:\x87\xd3[\x10x\x18\xe5\xd7']
    assert db.count_documents({}) > 0


def test_remove():
    """test_remove"""
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)
    assert db.count_documents({}) > 0
    duplicate_finder.remove(['test'], db)
    assert db.count_documents({}) > 0

    duplicate_finder.remove(['tests'], db)
    assert db.count_documents({}) == 0

    duplicate_finder.remove(['tests'], db)
    assert db.count_documents({}) == 0


def test_clear():
    """test_clear"""
    db = mongomock.MongoClient().image_database.images

    duplicate_finder.add(['tests'], db)

    assert db.count_documents({}) > 0
    duplicate_finder.clear(db)
    assert db.count_documents({}) == 0


def test_find():
    """test_find"""
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.add(['tests/images/deeply/nested'], db)

    dups = duplicate_finder.find(db, match_time=False)
    assert len(dups) == 1

    dup = dups[0]
    assert dup['total'] == 2

    time_dups = duplicate_finder.find(db, match_time=True)
    assert dups == time_dups


def test_find_videos():
    """test_find_videos"""
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.clear(db)
    duplicate_finder.add(['tests/videos/'], db)

    dups = duplicate_finder.find(db, match_time=False)

    assert len(dups) == 8
    assert {dups[0]['total'], dups[1]['total'], dups[2]['total'], dups[3]['total'],
            dups[4]['total'], dups[5]['total'], dups[6]['total'], dups[7]['total']} == {2, 3, 4}

    found = False
    for duplicate in dups:
        if b'img:\x83+\x03s=\xf2vT' in duplicate['_id']:
            found = True
            assert duplicate['total'] == 4
            filenames = {item['file_name'].rsplit('tests/videos/', 1)[1]
                         for item in duplicate['items']}
            assert filenames == {'2.mp4', '3.mp4', '4.mkv', '6.avi'}

    assert found is True


def test_find_fuzzy():
    """test_find_fuzzy"""
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.add(['tests/images/'], db)

    dups = duplicate_finder.find_threshold(db, 0)
    assert len(dups) == 3
    assert {dups[0]['total'], dups[1]['total'], dups[2]['total']} == {2, 5, 8}

    dups = duplicate_finder.find_threshold(db, 10)
    assert len(dups) == 2
    assert {dups[0]['total'], dups[1]['total']} == {2, 8}


def test_dedup():
    """test_dedup"""
    db = mongomock.MongoClient().image_database.images
    duplicate_finder.add(['tests/images'], db)
    assert db.count_documents({}) == 11

    dups = duplicate_finder.find(db, match_time=False)
    assert len(dups) == 6

    duplicate_finder.delete_duplicates(dups, db)

    dup = dups[0]

    # The first item should still be in its original place
    assert os.path.exists(dup['items'][0]['file_name'])

    # The rest of the files should be moved to the trash
    for item in dup['items'][1:]:
        assert not os.path.exists(item['file_name'])
        assert os.path.exists(os.path.join('Trash', os.path.basename(item['file_name'])))

    assert db.count_documents({}) == 3

    # Move files back
    for dup in dups:
        for item in dup['items'][1:]:
            shutil.copy(os.path.join('Trash', os.path.basename(item['file_name'])),
                        item['file_name'])

    shutil.rmtree('Trash')
