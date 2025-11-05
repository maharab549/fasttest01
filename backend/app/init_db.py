from sqlalchemy import create_engine
from backend.app.models import Base

engine = create_engine('sqlite:///D:/All github project/fasttest01/backend/marketplace.db')
Base.metadata.create_all(bind=engine)
print("All tables created!")
