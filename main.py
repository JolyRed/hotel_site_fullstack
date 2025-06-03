import os
from datetime import date
from fastapi import FastAPI, Request, Form, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Room, GalleryImage, Feedback, Booking, User, RoomImage
from schemas import FeedbackCreate, BookingCreate
from pydantic import ValidationError
from dotenv import load_dotenv
from admin import setup_admin
import requests
from auth import router as auth_router, get_current_user
from fastapi.encoders import jsonable_encoder
import json


# Сначала загружаем переменные окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.on_event('startup')
async def startup():
    await setup_admin(app)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)  # Получаем пользователя
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user}  # Передаём user!
    )

@app.get("/rooms")
def rooms(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    rooms = db.query(Room).all()
    # Собираем фото для каждой комнаты
    room_images = {room.id: [img.url for img in room.images] for room in rooms}
    room_images_json = json.dumps(room_images, ensure_ascii=False)
    return templates.TemplateResponse(
        "rooms.html",
        {
            "request": request,
            "rooms": rooms,
            "user": user,
            "room_images_json": room_images_json
        }
    )

@app.get("/gallery")
def gallery(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    images = db.query(GalleryImage).all()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images, "user": user})

@app.get("/feedback")
def feedback_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("feedback.html", {"request": request, "user": user})

@app.post("/feedback")
def submit_feedback(
    request: Request,
    fullname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    message: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    try:
        data = FeedbackCreate(fullname=fullname, phone=phone, email=email, message=message)
    except ValidationError as e:
        return templates.TemplateResponse("feedback.html", {"request": request, "errors": e.errors(), "user": user})

    feedback = Feedback(fullname=data.fullname, phone=data.phone, email=data.email, message=data.message)
    db.add(feedback)
    db.commit()
    return RedirectResponse(url="/feedback?success=1", status_code=status.HTTP_303_SEE_OTHER)

def send_telegram_notification(message: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        chat_id = TELEGRAM_CHAT_ID
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")



@app.get("/book/{room_id}")
def booking_form(request: Request, room_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login?next=/book/{}".format(room_id), status_code=303)
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Номер не найден")
    return templates.TemplateResponse("booking.html", {
        "request": request,
        "room": room,
        "user": user,
        "min_date": date.today().isoformat()
    })

@app.post("/book")
def submit_booking(
    request: Request,
    room_id: int = Form(...),
    fullname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/auth/login", status_code=303)
    try:
        data = BookingCreate(
            room_id=room_id,
            fullname=fullname,
            phone=phone,
            email=email,
            check_in=date.fromisoformat(check_in),
            check_out=date.fromisoformat(check_out)
        )
    except ValidationError as e:
        room = db.query(Room).filter(Room.id == room_id).first()
        return templates.TemplateResponse("booking.html", {
            "request": request,
            "room": room,
            "errors": e.errors(),
            "min_date": date.today().isoformat()
        })

    existing_booking = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.check_out > data.check_in,
        Booking.check_in < data.check_out,
        Booking.status == "confirmed"
    ).first()

    if existing_booking:
        room = db.query(Room).filter(Room.id == room_id).first()
        return templates.TemplateResponse("booking.html", {
            "request": request,
            "room": room,
            "error": "Номер уже забронирован на выбранные даты",
            "min_date": date.today().isoformat()
        })

    booking = Booking(
        room_id=data.room_id,
        fullname=data.fullname,
        phone=data.phone,
        email=data.email,
        check_in=data.check_in,
        check_out=data.check_out,
        user_id=user.id,
        status="pending"
    )

    db.add(booking)
    db.commit()

    room = db.query(Room).filter(Room.id == room_id).first()
    message = (
        f"<b>Новое бронирование!</b>\n\n"
        f"🔹 Номер: {room.name}\n"
        f"👤 Гость: {data.fullname}\n"
        f"📞 Телефон: {data.phone}\n"
        f"📧 Email: {data.email}\n"
        f"📅 Заезд: {data.check_in}\n"
        f"📅 Выезд: {data.check_out}\n"
        f"🆔 ID брони: {booking.id}"
    )
    send_telegram_notification(message)

    return RedirectResponse(url=f"/book/success/{booking.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/book/success/{booking_id}")
def booking_success(request: Request, booking_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)  # Получаем пользователя
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    room = db.query(Room).filter(Room.id == booking.room_id).first()
    return templates.TemplateResponse("booking_success.html", {
        "request": request,
        "booking": booking,
        "room": room,
        "user": user  # Передаём user!
    })

@app.get("/my-bookings")
def my_bookings(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bookings = db.query(Booking).filter(
        Booking.user_id == current_user.id,
        Booking.status.in_(["pending", "confirmed"])
    ).all()
    return templates.TemplateResponse("my_bookings.html", {
        "request": request,
        "bookings": bookings,
        "user": current_user
    })

@app.post("/my-bookings/cancel/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user.id).first()
    if booking and booking.status in ["pending", "confirmed"]:
        booking.status = "cancelled"
        db.commit()
    return RedirectResponse("/my-bookings", status_code=303)

@app.get("/settings")
def settings_form(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("settings.html", {"request": request, "user": current_user})

@app.get("/admin/bookings")
def admin_bookings(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    bookings = db.query(Booking).filter(Booking.status == "pending").all()
    return templates.TemplateResponse("admin_bookings.html", {
        "request": request,
        "bookings": bookings,
        "user": current_user  # <-- обязательно!
    })

@app.post("/admin/bookings/confirm/{booking_id}")
def confirm_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking and booking.status == "pending":
        booking.status = "confirmed"
        db.commit()
        # Отправляем уведомление в Telegram
        room = db.query(Room).filter(Room.id == booking.room_id).first()
        message = (
            f"<b>Бронирование подтверждено!</b>\n\n"
            f"🔹 Номер: {room.name if room else booking.room_id}\n"
            f"👤 Гость: {booking.fullname}\n"
            f"📞 Телефон: {booking.phone}\n"
            f"📧 Email: {booking.email}\n"
            f"📅 Заезд: {booking.check_in}\n"
            f"📅 Выезд: {booking.check_out}\n"
            f"🆔 ID брони: {booking.id}"
        )
        send_telegram_notification(message)
    return RedirectResponse("/admin/bookings", status_code=303)

@app.get("/admin")
def admin_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    status = request.query_params.get("status")
    if status == "all":
        bookings = db.query(Booking).all()
    else:
        bookings = db.query(Booking).filter(Booking.status.in_(["pending", "confirmed"])).all()
    rooms = db.query(Room).all()
    images = db.query(GalleryImage).all()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "user": user, "rooms": rooms, "bookings": bookings, "images": images}
    )

# Показать форму редактирования
@app.get("/admin/rooms/edit/{room_id}")
def edit_room_form(request: Request, room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    room = db.query(Room).filter(Room.id == room_id).first()
    return templates.TemplateResponse("edit_room.html", {"request": request, "room": room, "user": current_user})

# Обработать изменения
@app.post("/admin/rooms/edit/{room_id}")
def edit_room(
    request: Request,
    room_id: int,
    name: str = Form(...),
    description: str = Form(...),
    price: int = Form(...),
    image: str = Form(...),
    capacity: int = Form(...),
    amenities: str = Form(...),
    is_available: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    room = db.query(Room).filter(Room.id == room_id).first()
    room.name = name
    room.description = description
    room.price = price
    room.image = image
    room.capacity = capacity
    room.amenities = amenities
    room.is_available = is_available
    db.commit()
    return RedirectResponse("/admin", status_code=303)

# Добавить фото
@app.post("/admin/rooms/{room_id}/add-photo")
def add_room_photo(room_id: int, photo_url: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    db.add(RoomImage(room_id=room_id, url=photo_url))
    db.commit()
    return RedirectResponse(f"/admin", status_code=303)

# Удалить фото
@app.post("/admin/rooms/{room_id}/delete-photo/{photo_id}")
def delete_room_photo(room_id: int, photo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)
    img = db.query(RoomImage).filter(RoomImage.id == photo_id, RoomImage.room_id == room_id).first()
    if img:
        db.delete(img)
        db.commit()
    return RedirectResponse(f"/admin", status_code=303)

@app.get("/about")
def about(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})