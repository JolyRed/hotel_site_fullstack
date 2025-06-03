from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class FeedbackCreate(BaseModel):
    fullname: str
    phone: str
    email: EmailStr
    message: Optional[str] = None

class BookingCreate(BaseModel):
    room_id: int
    fullname: str
    phone: str
    email: EmailStr
    check_in: date
    check_out: date

class RoomCreate(BaseModel):
    name: str
    description: Optional[str]
    price: int
    image: Optional[str]
    capacity: Optional[int] = 1
    amenities: Optional[str]
    is_available: Optional[bool] = True

class GalleryImageCreate(BaseModel):
    url: str
    caption: Optional[str]
    category: Optional[str]