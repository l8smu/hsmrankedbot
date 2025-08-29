#!/usr/bin/env python3
"""
Demo of the Professional Expense Reporting System
This script demonstrates the key features of the expense management system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import ExpenseStorage, datetime, timedelta

def run_demo():
    """Run a comprehensive demo of the expense reporting system"""
    
    print("=" * 70)
    print("           PROFESSIONAL EXPENSE REPORTING SYSTEM DEMO")
    print("=" * 70)
    print()
    
    # Initialize storage
    storage = ExpenseStorage()
    
    # Demo 1: Dashboard Overview
    print("🔍 DASHBOARD OVERVIEW")
    print("-" * 40)
    stats = storage.get_dashboard_stats()
    print(f"Total Expenses: {stats['totalExpenses']}")
    print(f"Pending Approvals: {stats['pendingApprovals']}")
    print(f"Approved Amount: ${stats['approvedAmount']:,.2f}")
    print(f"Rejected Count: {stats['rejectedCount']}")
    print(f"Monthly Total: ${stats['monthlyTotal']:,.2f}")
    print()
    
    # Demo 2: Current Expenses
    print("📊 CURRENT EXPENSES")
    print("-" * 40)
    for expense in storage.expenses.values():
        user = storage.users.get(expense['userId'], {})
        status_emoji = "✅" if expense['status'] == 'approved' else "⏳" if expense['status'] == 'pending' else "❌"
        print(f"{status_emoji} {expense['title']}")
        print(f"   Amount: ${expense['amount']:,.2f} | User: {user.get('name', 'Unknown')}")
        print(f"   Category: {expense['category']} | Status: {expense['status'].upper()}")
        print()
    
    # Demo 3: Creating New Expense
    print("✨ CREATING NEW EXPENSE")
    print("-" * 40)
    new_expense_data = {
        'userId': 'user-3',
        'title': 'Software License Renewal',
        'description': 'Annual subscription for development tools',
        'amount': 299.99,
        'category': 'software',
        'status': 'pending'
    }
    
    new_expense = storage.create_expense(new_expense_data)
    print(f"New expense created: {new_expense['title']}")
    print(f"ID: {new_expense['id']}")
    print(f"Amount: ${new_expense['amount']:,.2f}")
    print(f"Status: {new_expense['status'].upper()}")
    print()
    
    # Demo 4: Approval Process
    print("🔍 APPROVAL PROCESS")
    print("-" * 40)
    
    # Find a pending expense to approve
    pending_expense = None
    for expense in storage.expenses.values():
        if expense['status'] == 'pending':
            pending_expense = expense
            break
    
    if pending_expense:
        print(f"Approving expense: {pending_expense['title']}")
        print(f"Amount: ${pending_expense['amount']:,.2f}")
        
        # Approve the expense
        approval_result = storage.approve_expense(pending_expense['id'], 'user-2')
        
        print(f"✅ Expense approved by {storage.users['user-2']['name']}")
        print(f"New status: {approval_result['expense']['status'].upper()}")
        print()
    
    # Demo 5: Rejection Process
    print("🚫 REJECTION PROCESS")
    print("-" * 40)
    
    # Find another pending expense to reject
    pending_expense = None
    for expense in storage.expenses.values():
        if expense['status'] == 'pending':
            pending_expense = expense
            break
    
    if pending_expense:
        print(f"Rejecting expense: {pending_expense['title']}")
        print(f"Amount: ${pending_expense['amount']:,.2f}")
        
        # Reject the expense
        rejection_result = storage.reject_expense(
            pending_expense['id'], 
            'user-2', 
            'Insufficient documentation provided'
        )
        
        print(f"❌ Expense rejected by {storage.users['user-2']['name']}")
        print(f"Reason: {rejection_result['expense']['rejectionReason']}")
        print(f"New status: {rejection_result['expense']['status'].upper()}")
        print()
    
    # Demo 6: Updated Dashboard
    print("📈 UPDATED DASHBOARD")
    print("-" * 40)
    updated_stats = storage.get_dashboard_stats()
    print(f"Total Expenses: {updated_stats['totalExpenses']}")
    print(f"Pending Approvals: {updated_stats['pendingApprovals']}")
    print(f"Approved Amount: ${updated_stats['approvedAmount']:,.2f}")
    print(f"Rejected Count: {updated_stats['rejectedCount']}")
    print(f"Monthly Total: ${updated_stats['monthlyTotal']:,.2f}")
    print()
    
    # Demo 7: Export Feature
    print("💾 DATA EXPORT FEATURE")
    print("-" * 40)
    
    # Export to JSON
    start_date = (datetime.now() - timedelta(days=30)).isoformat()
    end_date = datetime.now().isoformat()
    
    export_data = storage.export_expenses(start_date, end_date, 'json')
    print(f"Exported {len(export_data['expenses'])} expenses")
    print(f"Total amount: ${export_data['totalAmount']:,.2f}")
    print(f"Date range: {start_date[:10]} to {end_date[:10]}")
    print()
    
    # Demo 8: User Management
    print("👥 USER MANAGEMENT")
    print("-" * 40)
    for user in storage.users.values():
        print(f"• {user['name']} ({user['email']})")
        print(f"  Role: {user['role'].upper()} | Department: {user['department']}")
        if user.get('managerId'):
            manager = storage.users.get(user['managerId'], {})
            print(f"  Manager: {manager.get('name', 'Unknown')}")
        print()
    
    # Demo 9: System Features Summary
    print("🚀 SYSTEM FEATURES SUMMARY")
    print("-" * 40)
    print("✅ Automated expense submission")
    print("✅ Multi-level approval workflows")
    print("✅ Real-time dashboard analytics")
    print("✅ Comprehensive expense tracking")
    print("✅ Data export capabilities (CSV/JSON)")
    print("✅ User role management")
    print("✅ Expense categorization")
    print("✅ Approval history tracking")
    print("✅ Rejection reason documentation")
    print("✅ Monthly and yearly reporting")
    print()
    
    print("=" * 70)
    print("           DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("This professional expense reporting system provides:")
    print("• Complete expense lifecycle management")
    print("• Automated approval workflows")
    print("• Comprehensive analytics and reporting")
    print("• Data export for external analysis")
    print("• User-friendly interface for all stakeholders")
    print()
    print("Ready for deployment in business environments!")

if __name__ == "__main__":
    run_demo()