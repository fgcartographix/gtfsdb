import sys
import time
from gtfsdb.model import SRID
from geoalchemy import GeometryColumn, GeometryDDL, Point, LineString, WKTSpatialElement
from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from .base import Base


__all__ = ['Pattern', 'Shape']


class Pattern(Base):
    __tablename__ = 'patterns'

    shape_id = Column(String, primary_key=True)
    pattern_dist = Column(Numeric(20,10))

    def geom_from_shape(self, shape_points):
        wkt = 'LINESTRING('
        for point in shape_points:
            coords = '%s %s' %(point.shape_pt_lon, point.shape_pt_lat)
            wkt = '%s%s, ' %(wkt, coords)
        wkt = '%s)' %(wkt.rstrip(', '))
        self.geom = WKTSpatialElement(wkt)

    @classmethod
    def add_geometry_column(cls):
        cls.geom = GeometryColumn(LineString(2))
        GeometryDDL(cls.__table__)

    @classmethod
    def get_filename(cls):
        return None

    @classmethod
    def load(cls, engine):
        start_time = time.time()
        s = ' - %s' %(cls.__tablename__)
        sys.stdout.write(s)
        Session = sessionmaker(bind=engine)
        session = Session()
        q = session.query(
            Shape.shape_id,
            func.max(Shape.shape_dist_traveled).label('dist')
        )
        shapes = q.group_by(Shape.shape_id)
        for shape in shapes:
            pattern = cls()
            pattern.shape_id = shape.shape_id
            pattern.pattern_dist = shape.dist
            if hasattr(cls, 'geom'):
                q = session.query(Shape)
                q = q.filter(Shape.shape_id == shape.shape_id)
                q = q.order_by(Shape.shape_pt_sequence)
                pattern.geom_from_shape(q)
            session.add(pattern)
        session.commit()
        session.close()
        processing_time = time.time() - start_time
        print ' (%.0f seconds)' %(processing_time)


class Shape(Base):
    __tablename__ = 'shapes'

    required_fields = [
        'shape_id',
        'shape_pt_lat',
        'shape_pt_lon',
        'shape_pt_sequence'
    ]
    optional_fields = ['shape_dist_traveled']

    shape_id = Column(String, primary_key=True)
    shape_pt_lat = Column(Numeric(12,9))
    shape_pt_lon = Column(Numeric(12,9))
    shape_pt_sequence = Column(Integer, primary_key=True)
    shape_dist_traveled = Column(Numeric(20,10))

    @classmethod
    def add_geometry_column(cls):
        cls.geom = GeometryColumn(Point(2))
        GeometryDDL(cls.__table__)

    @classmethod
    def add_geom_to_dict(cls, row):
        wkt = 'SRID=%s;POINT(%s %s)' %(
            SRID,
            row['shape_pt_lon'],
            row['shape_pt_lat']
        )
        row['geom'] = WKTSpatialElement(wkt)
