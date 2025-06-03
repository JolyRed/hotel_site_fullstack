from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Room, GalleryImage, Feedback, Booking, User, RoomImage
from auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/admin")
def admin_panel(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    status = request.query_params.get("status")
    if status == "all":
        bookings = db.query(Booking).all()
    else:
        bookings = db.query(Booking).filter(Booking.status.in_(["pending", "confirmed"])).all()
    rooms = db.query(Room).all()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "bookings": bookings,
        "rooms": rooms
    })

@router.post("/admin/rooms/add")
async def add_room(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    form_data = await request.form()
    try:
        price = int(form_data.get("price", 0))
        capacity = int(form_data.get("capacity", 1))
    except ValueError:
        return RedirectResponse("/admin?error=badinput", status_code=303)
    room = Room(
        name=form_data.get("name", "").strip(),
        description=form_data.get("description", "").strip(),
        price=price,
        image=form_data.get("image", "").strip(),
        capacity=capacity,
        amenities=form_data.get("amenities", "").strip(),
        is_available=form_data.get("is_available") == "on"
    )
    db.add(room)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/admin/rooms/delete/{room_id}")
async def delete_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    room = db.query(Room).filter(Room.id == room_id).first()
    if room:
        db.delete(room)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.get("/admin/rooms/edit/{room_id}")
async def edit_room_form(room_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse("edit_room.html", {
        "request": request,
        "room": room,
        "user": current_user
    })

@router.post("/admin/rooms/edit/{room_id}")
async def edit_room(room_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return RedirectResponse("/admin", status_code=303)
    form_data = await request.form()
    room.name = form_data.get("name", room.name)
    room.description = form_data.get("description", room.description)
    room.price = int(form_data.get("price", room.price))
    room.image = form_data.get("image", room.image)
    room.capacity = int(form_data.get("capacity", room.capacity))
    room.amenities = form_data.get("amenities", room.amenities)
    room.is_available = form_data.get("is_available") == "on"
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/admin/gallery/add")
async def add_gallery_image(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    form_data = await request.form()
    image = GalleryImage(
        url=form_data.get("url", "").strip(),
        caption=form_data.get("caption", "").strip(),
        category=form_data.get("category", "").strip()
    )
    db.add(image)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/admin/gallery/delete/{img_id}")
async def delete_gallery_image(img_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    img = db.query(GalleryImage).filter(GalleryImage.id == img_id).first()
    if img:
        db.delete(img)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# Добавить фото
@router.post("/admin/rooms/{room_id}/images/add")
async def add_room_image(room_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    form = await request.form()
    url = form.get("url")
    if url:
        img = RoomImage(url=url, room_id=room_id)
        db.add(img)
        db.commit()
    return RedirectResponse(f"/admin/rooms/edit/{room_id}", status_code=303)

# Удалить фото
@router.post("/admin/rooms/{room_id}/images/delete/{img_id}")
async def delete_room_image(room_id: int, img_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    img = db.query(RoomImage).filter(RoomImage.id == img_id, RoomImage.room_id == room_id).first()
    if img:
        db.delete(img)
        db.commit()
    return RedirectResponse(f"/admin/rooms/edit/{room_id}", status_code=303)

@router.post("/admin/bookings/status/{booking_id}")
def change_booking_status(booking_id: int, status: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user or not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = status
        db.commit()
    return RedirectResponse("/admin", status_code=303)

async def setup_admin(app):
    app.include_router(router, prefix="")

