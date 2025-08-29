#!/usr/bin/env python3
"""
Export Demo - Generate sample expense reports in CSV and JSON formats
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ExpenseStorage, datetime, timedelta
import json

def create_export_files():
    """Create sample export files to demonstrate export capabilities"""
    
    storage = ExpenseStorage()
    
    # Add some additional sample expenses for better demo
    sample_expenses = [
        {
            'userId': 'user-1',
            'title': 'Conference Registration',
            'description': 'Annual Tech Conference 2025',
            'amount': 1500.00,
            'category': 'training',
            'status': 'approved'
        },
        {
            'userId': 'user-2',
            'title': 'Client Dinner',
            'description': 'Business dinner with potential client',
            'amount': 180.75,
            'category': 'meals',
            'status': 'pending'
        },
        {
            'userId': 'user-3',
            'title': 'Taxi to Airport',
            'description': 'Transportation for business trip',
            'amount': 65.00,
            'category': 'travel',
            'status': 'approved'
        }
    ]
    
    # Add the sample expenses
    for expense_data in sample_expenses:
        storage.create_expense(expense_data)
    
    # Approve some expenses
    for expense in storage.expenses.values():
        if expense['status'] == 'pending' and expense['title'] != 'Client Dinner':
            storage.approve_expense(expense['id'], 'user-2')
    
    # Export date range
    start_date = (datetime.now() - timedelta(days=30)).isoformat()
    end_date = datetime.now().isoformat()
    
    # Generate CSV export
    csv_data = storage.export_expenses(start_date, end_date, 'csv')
    with open('expense_report.csv', 'w', newline='', encoding='utf-8') as f:
        f.write(csv_data)
    
    # Generate JSON export
    json_data = storage.export_expenses(start_date, end_date, 'json')
    with open('expense_report.json', 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, default=str)
    
    print("Export files created successfully!")
    print("Files generated:")
    print("- expense_report.csv: CSV format for spreadsheet analysis")
    print("- expense_report.json: JSON format for system integration")
    print()
    
    # Show summary
    print("Export Summary:")
    print(f"Total expenses exported: {len(json_data['expenses'])}")
    print(f"Total amount: ${json_data['totalAmount']:,.2f}")
    print(f"Date range: {start_date[:10]} to {end_date[:10]}")
    print()
    
    # Show sample data
    print("Sample exported data:")
    print("First 3 expenses:")
    for i, expense in enumerate(json_data['expenses'][:3]):
        user = next(u for u in json_data['users'] if u['id'] == expense['userId'])
        print(f"{i+1}. {expense['title']} - ${expense['amount']:,.2f}")
        print(f"   User: {user['name']} | Status: {expense['status']}")
    
    return len(json_data['expenses']), json_data['totalAmount']

if __name__ == "__main__":
    create_export_files()