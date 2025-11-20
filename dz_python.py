from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid
from odf.opendocument import OpenDocumentText
from odf.text import P

class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.SessionLocal = None
        
    def connect(self):
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        return self.engine
    
    def get_session(self):
        if not self.SessionLocal:
            self.connect()
        return self.SessionLocal()
    
    def create_tables(self):
        if not self.engine:
            self.connect()
        Base.metadata.create_all(bind=self.engine)

Base = declarative_base()

class AbstractTable(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Supplier(AbstractTable):
    __tablename__ = "suppliers"
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    products = relationship("Product", back_populates="supplier")

class Product(AbstractTable):
    __tablename__ = "products"
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

class Order(AbstractTable):
    __tablename__ = "orders"
    order_number = Column(String(100), unique=True, nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255))
    customer_phone = Column(String(50))
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="pending")
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(AbstractTable):
    __tablename__ = "order_items"
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

def generate_order_number():
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

class WaosaDataFiller:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def fill_with_sample_data(self):
        session = self.db.get_session()
        
        supplier = Supplier(
            name="Waosa Supplier",
            contact_person="Waosa Manager",
            email="manager@waosa.com",
            phone="123-456-7890"
        )
        
        products = [
            Product(name="Waosa Product A", price=100.0, quantity=50, supplier=supplier),
            Product(name="Waosa Product B", price=200.0, quantity=30, supplier=supplier),
            Product(name="Waosa Product C", price=150.0, quantity=20, supplier=supplier),
        ]
        
        orders_data = [
            {
                "customer_name": "Alice Johnson",
                "customer_email": "alice@waosa.com",
                "items": [{"product": products[0], "quantity": 2}, {"product": products[1], "quantity": 1}]
            },
            {
                "customer_name": "Bob Smith", 
                "customer_email": "bob@waosa.com",
                "items": [{"product": products[2], "quantity": 3}, {"product": products[0], "quantity": 1}]
            }
        ]
        
        for order_data in orders_data:
            order = Order(
                order_number=generate_order_number(),
                customer_name=order_data["customer_name"],
                customer_email=order_data["customer_email"],
                status="completed"
            )
            
            total_amount = 0
            for item_data in order_data["items"]:
                item_total = item_data["product"].price * item_data["quantity"]
                order_item = OrderItem(
                    order=order,
                    product=item_data["product"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["product"].price,
                    total_price=item_total
                )
                total_amount += item_total
                session.add(order_item)
            
            order.total_amount = total_amount
            session.add(order)
        
        session.add(supplier)
        for product in products:
            session.add(product)
        
        session.commit()
        session.close()
        print("Данные из Waosa Club добавлены")

class OrderManager:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def get_all_orders(self):
        session = self.db.get_session()
        orders = session.query(Order).all()
        session.close()
        return orders
    
    def display_orders(self):
        orders = self.get_all_orders()
        print("\nСПИСОК ЗАКАЗОВ:")
        for order in orders:
            print(f"Заказ {order.order_number}:")
            print(f"  Клиент: {order.customer_name}")
            print(f"  Сумма: ${order.total_amount}")
            print(f"  Статус: {order.status}")
            
            session = self.db.get_session()
            items = session.query(OrderItem).filter_by(order_id=order.id).all()
            for item in items:
                product = session.query(Product).filter_by(id=item.product_id).first()
                print(f"    - {product.name}: {item.quantity} x ${item.unit_price}")
            session.close()
            print()

class ODTExporter:
    def export_orders_to_odt(self, orders, filename="orders.odt"):
        doc = OpenDocumentText()
        
        title = P()
        title.addText("ОТЧЕТ ПО ЗАКАЗАМ")
        doc.text.addElement(title)
        doc.text.addElement(P())
        
        for order in orders:
            order_header = P()
            order_header.addText(f"Заказ: {order.order_number}")
            doc.text.addElement(order_header)
            
            customer_info = P()
            customer_info.addText(f"Клиент: {order.customer_name}")
            doc.text.addElement(customer_info)
            
            amount_info = P()
            amount_info.addText(f"Сумма: ${order.total_amount} | Статус: {order.status}")
            doc.text.addElement(amount_info)
            
            doc.text.addElement(P())
        
        doc.save(filename)
        print(f"Файл {filename} создан")

def main():
    db = DatabaseConnection("sqlite:///waosa.db")
    db.create_tables()
    
    filler = WaosaDataFiller(db)
    filler.fill_with_sample_data()
    
    manager = OrderManager(db)
    manager.display_orders()
    
    orders = manager.get_all_orders()
    exporter = ODTExporter()
    exporter.export_orders_to_odt(orders)
    
    print("Готово!")

if __name__ == "__main__":
    main()