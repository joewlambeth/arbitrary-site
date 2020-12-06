import datetime
import enum
from .db import Base
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum, Date, Time
from sqlalchemy.orm import relationship

# THE VALLEY OF JOINT TABLES

class UserGroup(Base):
    __tablename__ = 'user_group'
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)

    def __repr__(self):
        return "<UserGroup (User[%r]) (Group[%r])>" % (self.user_id, self.group_id)

class NewspostGroup(Base):
    __tablename__ = 'newspost_group'
    news_id = Column(Integer, ForeignKey('news.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)

    def __repr__(self):
        return "<NewspostGroup (Newspost[%r]) (Group[%r])>" % (self.news_id, self.group_id)

class GalleryGroup(Base):
    __tablename__ = "gallery_group"
    gallery_id = Column(Integer, ForeignKey('gallery.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)

    def __repr__(self):
        return "<GalleryGroup (Gallery[%r]) (Group[%r])>" % (self.gallery_id, self.group_id)

class NewspostTag(Base):
    __tablename__ = "newspost_tag"
    news_id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tag.id"), primary_key=True)

    def __repr__(self):
        return "<NewspostTag (Newspost[%r]) (Tag[%r])>" % (self.news_id, self.tag_id)

class GalleryTag(Base):
    __tablename__ = "gallery_tag"
    gallery_id = Column(Integer, ForeignKey("gallery.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tag.id"), primary_key=True)

    def __repr__(self):
        return "<GalleryTag (Image[%r]) (Tag[%r])>" % (self.gallery_id, self.tag_id)

# END JOINT TABLES

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(24), unique=True, nullable=False)
    password = Column(Text, nullable=False)
    permissions = Column(Text, nullable=False)
    groups = relationship("Group", secondary="user_group", back_populates="users")
    
    def __init__(self, username=None, password=None, permissions=None):
        self.username = username
        self.password = password
        self.permissions = permissions

    def __repr__(self):
        return "<User[%r] %r>" % (self.id, self.username)

class NewsPost(Base):
    __tablename__ = 'news'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime(True), nullable=False, default=datetime.datetime.now())
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    group = relationship("Group", secondary="newspost_group", back_populates="newsposts")
    tag = relationship("Tag", secondary="newspost_tag")
    
    def __init__(self, title=None, body=None):
        self.title = title
        self.body = body

    def __repr__(self):
        return "<NewsPost[%r] %r>" % (self.id, self.title)

class Gallery(Base):
    __tablename__ = 'gallery'
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    link = Column(Text, nullable=False)
    created = Column(DateTime(True), nullable=False, default=datetime.datetime.now())
    group = relationship("Group", secondary="gallery_group", back_populates="gallery")
    tag = relationship("Tag", secondary="gallery_tag")

    def __init__(self, title=None, link=None):
        self.title = title
        self.link = link

    def __repr__(self):
        return "<Image[%r] %r>" % (self.id, self.title)

class GroupEnum(enum.Enum):
    groups = 1
    connect = 2

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    grouptype = Column(Enum(GroupEnum), nullable=False)
    popularity = Column(Integer)
    users = relationship("User", secondary="user_group", back_populates="groups")
    newsposts = relationship("NewsPost", secondary="newspost_group", back_populates="group")
    gallery = relationship("Gallery", secondary="gallery_group", back_populates="group")

    def __init__(self, title=None, description=None):
        self.title = title
        self.description = description
        self.popularity = 0

    def __repr__(self):
        return "<Group[%r] %r>" % (self.id, self.title)


class Bulletin(Base):
    __tablename__ = 'bulletin'
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    link = Column(Text, nullable=False)
    created = Column(DateTime(True), nullable=False, default=datetime.datetime.now())

    def __init__(self, title=None, link=None):
        self.title = title
        self.link = link

    def __repr__(self):
        return "<Bulletin[%r] %r>" % (self.id, self.title)

class Tag(Base):
    __tablename__ = "tag"
    id = Column(Integer, primary_key = True)
    tag = Column(Text)

    def __init__(self, tag):
        self.tag = tag

    def __repr__(self):
        return "<Tag[%r] %r>" % (self.id, self.tag)

class Activity(Base):
    __tablename__ = "activity"
    id = Column(Integer, primary_key = True)
    user = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    item = Column(Text, nullable=False)
    field = Column(Text)
    date = Column(Date, nullable=False)
    time = Column(Time(True), nullable=False)

    def __init__(self, user, action, item, field=None):
        self.user = user
        self.action = action
        self.item = item
        self.field = field
        self.date = datetime.date.today()
        self.time = datetime.datetime.now().time()

    def __str__(self):
        # [01-01-1970 00:00:00] jlambeth added <User[2] admin>
        # OR
        # [01-01-1970 00:00:00] jlambeth changed <User[2] admin> password
        return "[%r %r] %s %s %s" % (self.date.isoformat(), self.time.isoformat('seconds'), self.user, self.action, self.item) + ((' ' + self.field) if self.field else '')

    def __repr__(self):
        return "<Activity[%r] %r>" % (self.id, self.__str__())