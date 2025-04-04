```python

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Association tables for many-to-many relationships
staff_group_association = Table(
    'staff_group_association',
    Base.metadata,
    Column('staff_id', String, ForeignKey('staff.id')),
    Column('group_id', String, ForeignKey('staff_groups.id'))
)

menu_item_category_association = Table(
    'menu_item_category_association',
    Base.metadata,
    Column('menu_item_id', String, ForeignKey('menu_items.id')),
    Column('category_id', String, ForeignKey('categories.id'))
)

# DONE
class Company(Base):
    __tablename__ = 'companies'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    logo = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    staff_count = Column(Integer, default=0)
    outlets = Column(Integer, default=0)
    contact_email = Column(String)
    contact_phone = Column(String)
    subscription_plan = Column(Enum('basic', 'premium', 'enterprise', name='subscription_plan_type'))
    subscription_status = Column(Enum('active', 'trial', 'expired', name='subscription_status_type'))
    subscription_start_date = Column(DateTime)
    subscription_end_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlets = relationship("Outlet", back_populates="company")
    staff = relationship("Staff", back_populates="company")
    sales_data = relationship("CompanySalesData", back_populates="company")

# DONE
class Outlet(Base):
    __tablename__ = 'outlets'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    city = Column(String)
    state = Column(String)
    country = Column(String)
    phone = Column(String)
    email = Column(String)
    manager_id = Column(String, ForeignKey('staff.id'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="outlets")
    tables = relationship("Table", back_populates="outlet")
    orders = relationship("Order", back_populates="outlet")
    staff = relationship("Staff", back_populates="outlet")
    inventory_items = relationship("InventoryItem", back_populates="outlet")
    manager = relationship("Staff", foreign_keys=[manager_id])

# DONE
class Staff(Base):
    __tablename__ = 'staff'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    outlet_id = Column(String, ForeignKey('outlets.id'))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    role = Column(String, nullable=False)
    department = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    group_id = Column(String, ForeignKey('staff_groups.id'))

    # Relationships
    company = relationship("Company", back_populates="staff")
    outlet = relationship("Outlet", back_populates="staff", foreign_keys=[outlet_id])
    attendance_records = relationship("AttendanceRecord", back_populates="staff")
    leave_applications = relationship("LeaveApplication", back_populates="staff")
    payroll = relationship("StaffPayroll", back_populates="staff")
    orders_handled = relationship("Order", back_populates="handler")
    groups = relationship("StaffGroup", secondary=staff_group_association, back_populates="staff_members")


class StaffGroup(Base):
    __tablename__ = 'staff_groups'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    permissions_orders_create = Column(Boolean, default=False)
    permissions_orders_read = Column(Boolean, default=False)
    permissions_orders_update = Column(Boolean, default=False)
    permissions_orders_delete = Column(Boolean, default=False)
    permissions_inventory_create = Column(Boolean, default=False)
    permissions_inventory_read = Column(Boolean, default=False)
    permissions_inventory_update = Column(Boolean, default=False)
    permissions_inventory_delete = Column(Boolean, default=False)
    permissions_stock_create = Column(Boolean, default=False)
    permissions_stock_read = Column(Boolean, default=False)
    permissions_stock_update = Column(Boolean, default=False)
    permissions_stock_delete = Column(Boolean, default=False)
    visible_routes = Column(Text)  # JSON stored as text
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff_members = relationship("Staff", secondary=staff_group_association, back_populates="groups")

# DONE
class AttendanceRecord(Base):
    __tablename__ = 'attendance_records'

    id = Column(String, primary_key=True)
    staff_id = Column(String, ForeignKey('staff.id'), nullable=False)
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime)
    status = Column(Enum('present', 'late', 'absent', 'on-leave', name='attendance_status_type'))
    overtime = Column(Float)  # Hours
    night_shift = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="attendance_records")


class LeaveApplication(Base):
    __tablename__ = 'leave_applications'

    id = Column(String, primary_key=True)
    staff_id = Column(String, ForeignKey('staff.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    type = Column(Enum('annual', 'sick', 'parental', 'unpaid', 'compassionate', name='leave_type'))
    status = Column(Enum('pending', 'approved', 'rejected', name='leave_status_type'))
    reason = Column(Text, nullable=False)
    approved_by = Column(String, ForeignKey('staff.id'))
    approved_on = Column(DateTime)
    attachments = Column(Text)  # JSON array stored as text
    comments = Column(Text)
    days = Column(Integer, nullable=False)
    is_paid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="leave_applications", foreign_keys=[staff_id])
    approver = relationship("Staff", foreign_keys=[approved_by])


class LeaveBalance(Base):
    __tablename__ = 'leave_balances'

    id = Column(String, primary_key=True)
    staff_id = Column(String, ForeignKey('staff.id'), nullable=False)
    annual = Column(Float, default=0)
    sick = Column(Float, default=0)
    parental = Column(Float, default=0)
    unpaid = Column(Float, default=0)
    compassionate = Column(Float, default=0)
    total = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff")


class StaffPayroll(Base):
    __tablename__ = 'staff_payrolls'

    id = Column(String, primary_key=True)
    staff_id = Column(String, ForeignKey('staff.id'), nullable=False)
    payroll_period_id = Column(String, ForeignKey('payroll_periods.id'), nullable=False)
    pay_type = Column(Enum('hourly', 'monthly', name='pay_type'))
    rate = Column(Float, nullable=False)
    hours_worked = Column(Float)
    days_worked = Column(Integer)
    present_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    on_leave_days = Column(Integer, default=0)
    late_penalty = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    overtime_rate = Column(Float)
    night_shifts = Column(Integer, default=0)
    night_shift_allowance = Column(Float, default=0)
    calculated_daily_pay = Column(Float)
    calculated_weekly_pay = Column(Float)
    calculated_monthly_pay = Column(Float)
    start_date = Column(DateTime, nullable=False)
    status = Column(Enum('active', 'inactive', name='payroll_status_type'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff", back_populates="payroll")
    payroll_period = relationship("PayrollPeriod", back_populates="staff_payrolls")


class PayrollPeriod(Base):
    __tablename__ = 'payroll_periods'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum('draft', 'processed', 'paid', name='period_status_type'))
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    staff_payrolls = relationship("StaffPayroll", back_populates="payroll_period")


class PayrollSettings(Base):
    __tablename__ = 'payroll_settings'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    late_penalty_enabled = Column(Boolean, default=False)
    late_penalty_amount = Column(Float, default=0)
    clock_in_start_time = Column(String)  # Time stored as string
    clock_in_end_time = Column(String)  # Time stored as string
    late_after_minutes = Column(Integer, default=15)
    overtime_multiplier = Column(Float, default=1.5)
    night_shift_start_time = Column(String)  # Time stored as string
    night_shift_end_time = Column(String)  # Time stored as string
    night_shift_allowance_default = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# DONE
class Table(Base):
    __tablename__ = 'tables'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    number = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum('available', 'occupied', 'reserved', 'maintenance', name='table_status_type'), default='available')
    location = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet", back_populates="tables")
    orders = relationship("Order", back_populates="table")
    reservations = relationship("Reservation", back_populates="table")

# DONE
class Order(Base):
    __tablename__ = 'orders'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    table_id = Column(String, ForeignKey('tables.id'))
    handler_id = Column(String, ForeignKey('staff.id'))
    customer_id = Column(String, ForeignKey('customers.id'))
    type = Column(Enum('Food', 'Drinks', 'Laundry', name='order_type'))
    status = Column(Enum('New', 'In Progress', 'Ready', 'Completed', 'Cancelled', name='order_status_type'))
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet", back_populates="orders")
    table = relationship("Table", back_populates="orders")
    handler = relationship("Staff", back_populates="orders_handled")
    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

# DONE
class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey('orders.id'), nullable=False)
    menu_item_id = Column(String, ForeignKey('menu_items.id'))
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="order_items")
    menu_item = relationship("MenuItem", back_populates="order_items")


class MenuItem(Base):
    __tablename__ = 'menu_items'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    image = Column(String)
    is_available = Column(Boolean, default=True)
    preparation_time = Column(Integer)  # Minutes
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet")
    order_items = relationship("OrderItem", back_populates="menu_item")
    categories = relationship("Category", secondary=menu_item_category_association, back_populates="menu_items")


class Category(Base):
    __tablename__ = 'categories'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    menu_items = relationship("MenuItem", secondary=menu_item_category_association, back_populates="categories")


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    orders = relationship("Order", back_populates="customer")
    reservations = relationship("Reservation", back_populates="customer")
    feedback = relationship("Feedback", back_populates="customer")


class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    table_id = Column(String, ForeignKey('tables.id'))
    customer_id = Column(String, ForeignKey('customers.id'))
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=False)
    guests = Column(Integer, nullable=False)
    children = Column(Integer, default=0)
    status = Column(Enum('pending', 'confirmed', 'cancelled', 'completed', name='reservation_status_type'))
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet")
    table = relationship("Table", back_populates="reservations")
    customer = relationship("Customer", back_populates="reservations")


class Event(Base):
    __tablename__ = 'events'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum('upcoming', 'ongoing', 'completed', 'cancelled', name='event_status_type'))
    seating_arrangement = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet")
    menu_selections = relationship("EventMenuItem", back_populates="event")


class EventMenuItem(Base):
    __tablename__ = 'event_menu_items'

    id = Column(String, primary_key=True)
    event_id = Column(String, ForeignKey('events.id'), nullable=False)
    menu_item_id = Column(String, ForeignKey('menu_items.id'), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    event = relationship("Event", back_populates="menu_selections")
    menu_item = relationship("MenuItem")


class InventoryItem(Base):
    __tablename__ = 'inventory_items'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    min_quantity = Column(Float)
    max_quantity = Column(Float)
    price_per_unit = Column(Float)
    supplier_id = Column(String, ForeignKey('suppliers.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet", back_populates="inventory_items")
    supplier = relationship("Supplier", back_populates="inventory_items")
    stock_movements = relationship("StockMovement", back_populates="inventory_item")


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    name = Column(String, nullable=False)
    contact_person = Column(String)
    email = Column(String)
    phone = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")


class StockMovement(Base):
    __tablename__ = 'stock_movements'

    id = Column(String, primary_key=True)
    inventory_item_id = Column(String, ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    type = Column(Enum('in', 'out', 'adjustment', name='movement_type'))
    reason = Column(String)
    performed_by = Column(String, ForeignKey('staff.id'))
    created_at = Column(DateTime, default=func.now())

    # Relationships
    inventory_item = relationship("InventoryItem", back_populates="stock_movements")
    staff = relationship("Staff")


class StoreRequest(Base):
    __tablename__ = 'store_requests'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    requested_by = Column(String, ForeignKey('staff.id'), nullable=False)
    approved_by = Column(String, ForeignKey('staff.id'))
    status = Column(Enum('pending', 'approved', 'rejected', 'fulfilled', name='request_status_type'))
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet")
    requester = relationship("Staff", foreign_keys=[requested_by])
    approver = relationship("Staff", foreign_keys=[approved_by])
    items = relationship("StoreRequestItem", back_populates="store_request")


class StoreRequestItem(Base):
    __tablename__ = 'store_request_items'

    id = Column(String, primary_key=True)
    store_request_id = Column(String, ForeignKey('store_requests.id'), nullable=False)
    inventory_item_id = Column(String, ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    fulfilled_quantity = Column(Float, default=0)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    store_request = relationship("StoreRequest", back_populates="items")
    inventory_item = relationship("InventoryItem")


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey('orders.id'))
    amount = Column(Float, nullable=False)
    method = Column(String, nullable=False)
    status = Column(Enum('pending', 'completed', 'failed', 'refunded', name='payment_status_type'))
    transaction_id = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Order")


class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    customer_id = Column(String, ForeignKey('customers.id'))
    order_id = Column(String, ForeignKey('orders.id'))
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    outlet = relationship("Outlet")
    customer = relationship("Customer", back_populates="feedback")
    order = relationship("Order")


class Issue(Base):
    __tablename__ = 'issues'

    id = Column(String, primary_key=True)
    outlet_id = Column(String, ForeignKey('outlets.id'), nullable=False)
    reported_by = Column(String, ForeignKey('staff.id'), nullable=False)
    assigned_to = Column(String, ForeignKey('staff.id'))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String)
    priority = Column(Enum('low', 'medium', 'high', 'critical', name='issue_priority_type'))
    status = Column(Enum('open', 'in_progress', 'resolved', 'closed', name='issue_status_type'))
    resolution = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    outlet = relationship("Outlet")
    reporter = relationship("Staff", foreign_keys=[reported_by])
    assignee = relationship("Staff", foreign_keys=[assigned_to])


class CompanySalesData(Base):
    __tablename__ = 'company_sales_data'

    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey('companies.id'), nullable=False)
    date = Column(String, nullable=False)
    total_sales = Column(Float, default=0)
    average_order_value = Column(Float, default=0)
    order_count = Column(Integer, default=0)
    customer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="sales_data")
    sales_by_category = relationship("SalesByCategory", back_populates="company_sales")
    sales_by_time = relationship("SalesByTime", back_populates="company_sales")
    top_selling_items = relationship("TopSellingItem", back_populates="company_sales")


class SalesByCategory(Base):
    __tablename__ = 'sales_by_category'

    id = Column(String, primary_key=True)
    company_sales_id = Column(String, ForeignKey('company_sales_data.id'), nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, default=0)

    # Relationships
    company_sales = relationship("CompanySalesData", back_populates="sales_by_category")


class SalesByTime(Base):
    __tablename__ = 'sales_by_time'

    id = Column(String, primary_key=True)
    company_sales_id = Column(String, ForeignKey('company_sales_data.id'), nullable=False)
    hour = Column(String, nullable=False)
    amount = Column(Float, default=0)

    # Relationships
    company_sales = relationship("CompanySalesData", back_populates="sales_by_time")


class TopSellingItem(Base):
    __tablename__ = 'top_selling_items'

    id = Column(String, primary_key=True)
    company_sales_id = Column(String, ForeignKey('company_sales_data.id'), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    revenue = Column(Float, default=0)

    # Relationships
    company_sales = relationship("CompanySalesData", back_populates="top_selling_items")

```
