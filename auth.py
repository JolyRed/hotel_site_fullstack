import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form, Depends, status, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Optional
from dotenv import load_dotenv
import requests
from pydantic import ValidationError

# Импорт моделей и схем
from database import SessionLocal, engine, Base
from models import Room, GalleryImage, Feedback, Booking, User
from schemas import FeedbackCreate, BookingCreate, UserCreate, UserLogin, RoomCreate, GalleryImageCreate

# Загрузка переменных окружения
load_dotenv()

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Конфигурация JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Конфигурация Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Инициализация приложения
app = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Функция для получения базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для создания JWT токена
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Функция для получения текущего пользователя
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Функция для отправки уведомлений в Telegram
def send_telegram_notification(message: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        if TELEGRAM_CHAT_ID.startswith('@'):
            chat_id = TELEGRAM_CHAT_ID
        else:
            chat_id = TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID.startswith('-') else f"-100{TELEGRAM_CHAT_ID}"
        
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

# Регистрация пользователя
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(
        username=user.username,
        email=user.email,
        is_admin=False
    )
    new_user.set_password(user.password)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

# Авторизация пользователя
@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Админ-панель
@app.get("/admin")
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    rooms = db.query(Room).all()
    images = db.query(GalleryImage).all()
    bookings = db.query(Booking).all()
    feedbacks = db.query(Feedback).all()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "rooms": rooms,
        "images": images,
        "bookings": bookings,
        "feedbacks": feedbacks
    })

# Добавление номера (админ)
@app.post("/admin/rooms/add")
async def add_room(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    form_data = await request.form()
    room = Room(
        name=form_data.get("name"),
        description=form_data.get("description"),
        price=int(form_data.get("price")),
        image=form_data.get("image"),
        capacity=int(form_data.get("capacity", 1)),
        amenities=form_data.get("amenities", ""),
        is_available=form_data.get("is_available") == "on"
    )
    db.add(room)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# Добавление изображения в галерею (админ)
@app.post("/admin/gallery/add")
async def add_gallery_image(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    form_data = await request.form()
    image = GalleryImage(
        url=form_data.get("url"),
        caption=form_data.get("caption"),
        category=form_data.get("category")
    )
    db.add(image)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

# Основные маршруты
@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/rooms")
def rooms(request: Request, db: Session = Depends(get_db)):
    rooms = db.query(Room).filter(Room.is_available == True).all()
    return templates.TemplateResponse("rooms.html", {"request": request, "rooms": rooms})

@app.get("/gallery")
def gallery(request: Request, db: Session = Depends(get_db)):
    images = db.query(GalleryImage).all()
    return templates.TemplateResponse("gallery.html", {"request": request, "images": images})

@app.get("/feedback")
def feedback_form(request: Request):
    return templates.TemplateResponse("feedback.html", {"request": request})

@app.post("/feedback")
def submit_feedback(
    request: Request,
    fullname: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    message: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        data = FeedbackCreate(fullname=fullname, phone=phone, email=email, message=message)
    except ValidationError as e:
        return templates.TemplateResponse("feedback.html", {"request": request, "errors": e.errors()})

    feedback = Feedback(
        fullname=data.fullname,
        phone=data.phone,
        email=data.email,
        message=data.message
    )
    db.add(feedback)
    db.commit()
    return RedirectResponse(url="/feedback?success=1", status_code=status.HTTP_303_SEE_OTHER)

# Бронирование
@app.get("/book/{room_id}")
def booking_form(request: Request, room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Номер не найден")
    return templates.TemplateResponse("booking.html", {
        "request": request,
        "room": room,
        "min_date": datetime.now().date().isoformat()
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
    guests: int = Form(1),
    special_requests: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        data = BookingCreate(
            room_id=room_id,
            fullname=fullname,
            phone=phone,
            email=email,
            check_in=datetime.strptime(check_in, "%Y-%m-%d").date(),
            check_out=datetime.strptime(check_out, "%Y-%m-%d").date(),
            guests=guests,
            special_requests=special_requests
        )
    except ValidationError as e:
        room = db.query(Room).filter(Room.id == room_id).first()
        return templates.TemplateResponse("booking.html", {
            "request": request,
            "room": room,
            "errors": e.errors(),
            "min_date": datetime.now().date().isoformat()
        })
    
    # Проверка доступности номера
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
            "min_date": datetime.now().date().isoformat()
        })
    
    booking = Booking(
        room_id=data.room_id,
        fullname=data.fullname,
        phone=data.phone,
        email=data.email,
        check_in=data.check_in,
        check_out=data.check_out,
        guests=data.guests,
        special_requests=data.special_requests
    )
    
    db.add(booking)
    db.commit()
    
    # Отправка уведомления в Telegram
    room = db.query(Room).filter(Room.id == room_id).first()
    message = (
        f"<b>Новое бронирование!</b>\n\n"
        f"🔹 Номер: {room.name}\n"
        f"👤 Гость: {data.fullname}\n"
        f"📞 Телефон: {data.phone}\n"
        f"📧 Email: {data.email}\n"
        f"👥 Гостей: {data.guests}\n"
        f"📅 Заезд: {data.check_in}\n"
        f"📅 Выезд: {data.check_out}\n"
        f"🆔 ID брони: {booking.id}"
    )
    send_telegram_notification(message)
    
    return RedirectResponse(url=f"/book/success/{booking.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/book/success/{booking_id}")
def booking_success(request: Request, booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    
    room = db.query(Room).filter(Room.id == booking.room_id).first()
    return templates.TemplateResponse("booking_success.html", {
        "request": request,
        "booking": booking,
        "room": room
    })

# Запуск админки при старте приложения
@app.on_event("startup")
async def startup():
    # Создаем администратора по умолчанию, если его нет
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                is_admin=True
            )
            admin_user.set_password("admin123")
            db.add(admin_user)
            db.commit()
    finally:
        db.close()

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from schemas import UserCreate, UserLogin
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=1))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None

@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        return RedirectResponse("/auth/register?error=exists", status_code=303)
    user = User(username=username, email=email)
    user.set_password(password)
    db.add(user)
    db.commit()
    return RedirectResponse("/auth/login?registered=1", status_code=303)

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.check_password(password):
        return RedirectResponse("/auth/login?error=invalid", status_code=303)
    access_token = create_access_token({"sub": user.username})
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", access_token, httponly=True)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token")
    return response

@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register")
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})