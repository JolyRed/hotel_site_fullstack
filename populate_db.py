from database import SessionLocal, engine, Base
from models import Room, GalleryImage, Booking
from datetime import date, timedelta

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if db.query(Room).count() == 0:
    rooms = [
        Room(
            name="Номер Стандарт",
            description="Уютный номер с видом на горы",
            price=3500,  # Исправлено: число, а не строка
            image="https://greenhills-crimea.ru/wp-content/uploads/2023/12/SmallMidle_Kott.png"
        ),
        Room(
            name="Коттедж",
            description="Просторный коттедж с балконом",
            price=7000,
            image="https://greenhills-crimea.ru/wp-content/uploads/2024/01/Rainbow_kottages.jpg"
        ),
        Room(
            name="Семейный коттедж",
            description="Идеально подходит для большой семьи или компании",
            price=8500,
            image="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQxZvtuLibYEtn0O0yMCVPpTeDVdKtVDHtZ8w&s"
        )
    ]
    db.add_all(rooms)

if db.query(GalleryImage).count() == 0:
    urls = [
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/territory-11.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/Stoyanka_avto-2fg0.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/SmallMidle_Kott.png",
        "https://greenhills-crimea.ru/wp-content/uploads/2024/01/Rainbow_kottages.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/General_dinner_place-1ad36.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/territory-bbc.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/Swings1d.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/z_f48be99e.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/View_Road_Hill_1273.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/View_on_sea_1297.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/View_down_8ac.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/Shore3cc06.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/Roses_b_kitchen.jpg",
        "https://greenhills-crimea.ru/wp-content/uploads/2023/12/Shore2d06.jpg",
    ]
    images = [GalleryImage(url=url) for url in urls]
    db.add_all(images)

if db.query(Booking).count() == 0:
    bookings = [
        Booking(
            room_id=1,
            fullname="Иван Иванов",
            phone="+79781234567",
            email="ivan@example.com",
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=10),
            status="confirmed"
        ),
        Booking(
            room_id=2,
            fullname="Петр Петров",
            phone="+79787654321",
            email="petr@example.com",
            check_in=date.today() + timedelta(days=3),
            check_out=date.today() + timedelta(days=7),
            status="pending"
        )
    ]
    db.add_all(bookings)

db.commit()
db.close()
