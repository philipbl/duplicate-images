from sqlalchemy import create_engine, exists, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


class Picture(Base):
    __tablename__ = "Pictures"

    file_name = Column(String, primary_key=True)
    hash = Column(String, index=True)
    file_size = Column(Integer)
    image_size = Column(String)
    capture_time = Column(String)

    def to_dict(self):
        return {'capture_time': self.capture_time,
                'file_name': self.file_name,
                'file_size': self.file_size,
                'hash': self.hash,
                'image_size': self.image_size}


class SQLite(object):
    def __init__(self, path):
        super(SQLite, self).__init__()

        self.eng = create_engine('sqlite:///{}'.format(path))
        Base.metadata.bind = self.eng
        Base.metadata.create_all()

        Session = sessionmaker(bind=self.eng)
        self.session = Session()

    def contains(self, file_name):
        result = self.session.query(exists().where(Picture.file_name == file_name))
        return result.scalar()

    def insert(self, data):
        self.session.add(Picture(**data))
        self.session.commit()

    def remove(self, file_name):
        self.session.query(Picture).filter(Picture.file_name == file_name).delete()
        self.session.commit()

    def clear(self):
        Picture.__table__.drop()

    def all(self):
        result = self.session.query(Picture).all()
        return [r.to_dict() for r in result]

    def count(self):
        return self.session.query(func.count(Picture.file_name)).scalar()

    def find_duplicates(self, match_time):
        # Get all hashes that have duplicates
        hashes = self.session.query(Picture.hash).group_by(Picture.hash).having(func.count(Picture.hash) > 1).all()
        dups = []

        for (hash,) in hashes:
            result = self.session.query(Picture).filter(Picture.hash == hash).all()
            dups.append({'items': [r.to_dict() for r in result],
                         'total': len(result)})

        return dups
