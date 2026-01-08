#!/usr/bin/env python3
"""
Generate 10-15 realistic supplier records with contact details and performance metrics.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.config import SessionLocal
from src.database.models import Supplier
import random

# Supplier templates by category
SUPPLIERS = [
    {
        'supplier_id': 'TECH-001',
        'supplier_name': 'TechSource Electronics',
        'contact_person': 'Michael Chen',
        'email': 'michael.chen@techsource.com',
        'phone': '+1-408-555-0123',
        'address': '1234 Innovation Way',
        'city': 'San Jose',
        'state_province': 'California',
        'country': 'USA',
        'postal_code': '95110',
        'payment_terms': 'Net 30',
        'default_lead_time_days': 7,
        'category': 'Electronics'
    },
    {
        'supplier_id': 'TECH-002',
        'supplier_name': 'ElectroWholesale Corp',
        'contact_person': 'Sarah Johnson',
        'email': 'sarah.j@electrowholesale.com',
        'phone': '+1-512-555-0234',
        'address': '5678 Tech Parkway',
        'city': 'Austin',
        'state_province': 'Texas',
        'country': 'USA',
        'postal_code': '78701',
        'payment_terms': '2/10 Net 30',
        'default_lead_time_days': 5,
        'category': 'Electronics'
    },
    {
        'supplier_id': 'HOME-001',
        'supplier_name': 'HomeGoods Direct',
        'contact_person': 'Robert Williams',
        'email': 'r.williams@homegoodsdirect.com',
        'phone': '+1-214-555-0345',
        'address': '9012 Commerce Dr',
        'city': 'Dallas',
        'state_province': 'Texas',
        'country': 'USA',
        'postal_code': '75201',
        'payment_terms': 'Net 60',
        'default_lead_time_days': 10,
        'category': 'Home Goods'
    },
    {
        'supplier_id': 'FASH-001',
        'supplier_name': 'Fashion Imports Inc',
        'contact_person': 'Emily Rodriguez',
        'email': 'emily.r@fashionimports.com',
        'phone': '+1-212-555-0456',
        'address': '3456 Garment District',
        'city': 'New York',
        'state_province': 'New York',
        'country': 'USA',
        'postal_code': '10018',
        'payment_terms': 'Net 45',
        'default_lead_time_days': 14,
        'category': 'Fashion'
    },
    {
        'supplier_id': 'SPORT-001',
        'supplier_name': 'Athletic Gear Supply',
        'contact_person': 'David Martinez',
        'email': 'david.m@athleticgear.com',
        'phone': '+1-503-555-0567',
        'address': '7890 Sports Ave',
        'city': 'Portland',
        'state_province': 'Oregon',
        'country': 'USA',
        'postal_code': '97201',
        'payment_terms': 'Net 30',
        'default_lead_time_days': 8,
        'category': 'Sports'
    },
    {
        'supplier_id': 'OFFICE-001',
        'supplier_name': 'Office Supplies Plus',
        'contact_person': 'Jennifer Lee',
        'email': 'jennifer.lee@officeplus.com',
        'phone': '+1-617-555-0678',
        'address': '2345 Business Blvd',
        'city': 'Boston',
        'state_province': 'Massachusetts',
        'country': 'USA',
        'postal_code': '02101',
        'payment_terms': '2/10 Net 30',
        'default_lead_time_days': 5,
        'category': 'Office'
    },
    {
        'supplier_id': 'HOME-002',
        'supplier_name': 'Kitchen & Bath Wholesale',
        'contact_person': 'Thomas Anderson',
        'email': 'thomas.a@kitchenbath.com',
        'phone': '+1-305-555-0789',
        'address': '6789 Warehouse Way',
        'city': 'Miami',
        'state_province': 'Florida',
        'country': 'USA',
        'postal_code': '33101',
        'payment_terms': 'Net 45',
        'default_lead_time_days': 12,
        'category': 'Home Goods'
    },
    {
        'supplier_id': 'TECH-003',
        'supplier_name': 'Digital Components Ltd',
        'contact_person': 'Lisa Wang',
        'email': 'lisa.wang@digitalcomp.com',
        'phone': '+1-206-555-0890',
        'address': '1122 Tech Center',
        'city': 'Seattle',
        'state_province': 'Washington',
        'country': 'USA',
        'postal_code': '98101',
        'payment_terms': 'Net 30',
        'default_lead_time_days': 6,
        'category': 'Electronics'
    },
    {
        'supplier_id': 'FASH-002',
        'supplier_name': 'Apparel Direct',
        'contact_person': 'Jessica Brown',
        'email': 'j.brown@appareldirect.com',
        'phone': '+1-323-555-0901',
        'address': '3344 Fashion Sq',
        'city': 'Los Angeles',
        'state_province': 'California',
        'country': 'USA',
        'postal_code': '90012',
        'payment_terms': 'Net 60',
        'default_lead_time_days': 15,
        'category': 'Fashion'
    },
    {
        'supplier_id': 'SPORT-002',
        'supplier_name': 'Outdoor Equipment Co',
        'contact_person': 'Mark Thompson',
        'email': 'mark.t@outdoorequip.com',
        'phone': '+1-303-555-1012',
        'address': '5566 Mountain Dr',
        'city': 'Denver',
        'state_province': 'Colorado',
        'country': 'USA',
        'postal_code': '80201',
        'payment_terms': 'Net 30',
        'default_lead_time_days': 9,
        'category': 'Sports'
    },
    {
        'supplier_id': 'GENERAL-001',
        'supplier_name': 'Universal Distributors',
        'contact_person': 'Amanda Garcia',
        'email': 'amanda.g@universaldist.com',
        'phone': '+1-312-555-1123',
        'address': '7788 Distribution Pkwy',
        'city': 'Chicago',
        'state_province': 'Illinois',
        'country': 'USA',
        'postal_code': '60601',
        'payment_terms': '2/10 Net 45',
        'default_lead_time_days': 7,
        'category': 'General'
    },
    {
        'supplier_id': 'BEAUTY-001',
        'supplier_name': 'Beauty & Personal Care Supply',
        'contact_person': 'Rachel Kim',
        'email': 'rachel.kim@beautycare.com',
        'phone': '+1-415-555-1234',
        'address': '9900 Beauty Blvd',
        'city': 'San Francisco',
        'state_province': 'California',
        'country': 'USA',
        'postal_code': '94101',
        'payment_terms': 'Net 30',
        'default_lead_time_days': 8,
        'category': 'Beauty'
    }
]


def generate_performance_metrics(category: str) -> dict:
    """Generate realistic performance metrics based on supplier category"""
    # Electronics suppliers tend to have better metrics
    if category == 'Electronics':
        on_time_rate = round(random.uniform(92, 99), 2)
        quality = round(random.uniform(4.3, 5.0), 2)
    elif category == 'Fashion':
        on_time_rate = round(random.uniform(85, 95), 2)
        quality = round(random.uniform(3.8, 4.7), 2)
    else:
        on_time_rate = round(random.uniform(88, 96), 2)
        quality = round(random.uniform(4.0, 4.8), 2)

    return {
        'on_time_delivery_rate': on_time_rate,
        'quality_rating': quality
    }


def main():
    print("🏭 Generating supplier data...")

    session = SessionLocal()
    try:
        # Clear existing suppliers
        session.query(Supplier).delete()
        session.commit()

        suppliers_created = 0

        for supplier_data in SUPPLIERS:
            # Add performance metrics
            metrics = generate_performance_metrics(supplier_data.get('category', 'General'))
            supplier_data.update(metrics)

            # Remove category (not in database schema)
            category = supplier_data.pop('category', None)

            # Create supplier record
            supplier = Supplier(**supplier_data)
            session.add(supplier)
            suppliers_created += 1

            print(f"  ✅ {supplier.supplier_name} ({category}) - "
                  f"On-time: {supplier.on_time_delivery_rate}%, "
                  f"Quality: {supplier.quality_rating}/5")

        session.commit()
        print(f"\n✅ Successfully created {suppliers_created} suppliers!")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
