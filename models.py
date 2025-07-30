from datetime import datetime
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
# Note: In a typical Flask-SQLAlchemy setup, you would use db.Model directly.
# Since you're using SQLAlchemy's declarative_base, we'll stick to that.

# Create a declarative base for your models
base = declarative_base()

class User(base):
    """
    User model for authentication and profile management.
    """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    Username = Column(String(50), nullable=False, unique=True)
    # It's highly recommended to hash passwords (e.g., using Werkzeug's security)
    # and store a longer hash, not a plain string of length 10.
    Password_hash = Column(String(255), nullable=False) # Increased length for hashed passwords
    Name = Column(String(50), nullable=False)
    Email = Column(String(120), nullable=False, unique=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    banned = Column(Boolean, nullable=False, default=False)

    def set_password(self, password):
        self.Password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.Password_hash, password)

    def __repr__(self):
        return f"<User {self.Username}>"

class Parking_lot(base):
    """
    Parking Lot model to store details about different parking locations.
    """
    __tablename__ = 'parking_lot'
    id = Column(Integer, primary_key=True)
    Prime_location_name = Column(String(50), nullable=False, unique=True)
    Price_Per_Hour = Column(Float, nullable=False)
    Address = Column(String(512), nullable=False, unique=True)
    Pin_Code = Column(Integer, nullable=False, unique=True)
    Max_Spots = Column(Integer, nullable=False) # Total number of spots in this lot

    def __repr__(self):
        return f"<Parking_lot {self.Prime_location_name}>"

from sqlalchemy.orm import relationship

class Parking_Spot(base):
    """
    Parking Spot model to track individual spots within a parking lot.
    """
    __tablename__ = 'parking_spot'
    id = Column(Integer, primary_key=True)
    Lot_id = Column(Integer, ForeignKey('parking_lot.id'), nullable=False)
    Status = Column(String(20), nullable=False, default='free') # e.g., 'free', 'reserved', 'occupied'
    Spot_number = Column(Integer, nullable=False) # Spot number within the lot
    # Note: 'Spot_number' should probably be unique per Lot_id, not globally unique.
    # For simplicity, keeping it globally unique as per original, but consider a composite unique constraint.
    # __table_args__ = (UniqueConstraint('Lot_id', 'Spot_number'),) if you want unique per lot

    parking_lot = relationship('Parking_lot')

    def __repr__(self):
        return f"<Parking_Spot {self.Spot_number} (Lot: {self.Lot_id}) - {self.Status}>"

from sqlalchemy.orm import relationship

class Reservation(base):
    """
    Reservation model to store details of a user's parking reservation.
    """
    __tablename__ = 'reservation'
    id = Column(Integer, primary_key=True)
    Spot_id = Column(Integer, ForeignKey('parking_spot.id'), nullable=False)
    User_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    Parking_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    Leaving_time = Column(DateTime, nullable=False)
    Total_Cost = Column(Float, nullable=False)

    user = relationship('User')
    spot = relationship('Parking_Spot')

    def __repr__(self):
        return f"<Reservation {self.id} (User: {self.User_id}, Spot: {self.Spot_id})>"