from sqlalchemy import Column, Integer, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from werkzeug.security import generate_password_hash, check_password_hash

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    price = Column(Integer)
    image = Column(String)  # можно оставить как "главное фото"
    capacity = Column(Integer, default=1)
    amenities = Column(String)
    is_available = Column(Boolean, default=True)
    images = relationship("RoomImage", back_populates="room")

class RoomImage(Base):
    __tablename__ = "room_images"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    url = Column(String)
    room = relationship("Room", back_populates="images")

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    caption = Column(String)
    category = Column(String)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    message = Column(String)

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    fullname = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    check_in = Column(Date)
    check_out = Column(Date)
    status = Column(String, default="pending")