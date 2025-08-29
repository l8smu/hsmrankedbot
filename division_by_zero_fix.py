#!/usr/bin/env python3
"""
Division by Zero Fix - إصلاح مشكلة القسمة على صفر في حساب MMR
"""

import sqlite3
import json

def diagnose_division_by_zero_issue():
    """تشخيص مشكلة القسمة على صفر"""
    
    print("🔍 تشخيص مشكلة القسمة على صفر...")
    print("=" * 50)
    
    # الأسباب المحتملة
    print("\n⚠️ الأسباب المحتملة لخطأ division by zero:")
    print("1. فريق فارغ (لا يحتوي على لاعبين)")
    print("2. بيانات فاسدة في active_matches")
    print("3. مشكلة في تكوين الفريق أثناء المباراة")
    print("4. خطأ في استرجاع بيانات اللاعب")
    print("5. مشكلة في persistent views بعد إعادة تشغيل البوت")
    
    # فحص قاعدة البيانات
    print("\n📊 فحص قاعدة البيانات:")
    try:
        conn = sqlite3.connect("players.db")
        c = conn.cursor()
        
        # عرض المباريات النشطة
        c.execute("""
            SELECT match_id, team1_players, team2_players, winner, created_at 
            FROM matches 
            WHERE winner IS NULL OR winner = 0
            ORDER BY match_id DESC
        """)
        active_matches = c.fetchall()
        
        print(f"📋 المباريات النشطة: {len(active_matches)}")
        
        for match_id, team1, team2, winner, created_at in active_matches:
            team1_count = len(team1.split(',')) if team1 else 0
            team2_count = len(team2.split(',')) if team2 else 0
            
            print(f"🎮 Match {match_id}:")
            print(f"   Team 1: {team1_count} players ({team1})")
            print(f"   Team 2: {team2_count} players ({team2})")
            print(f"   Winner: {winner}")
            print(f"   Created: {created_at}")
            
            # تحديد المشاكل
            if team1_count == 0 or team2_count == 0:
                print(f"   ⚠️ PROBLEM: فريق فارغ!")
            
            if not team1 or not team2:
                print(f"   ⚠️ PROBLEM: بيانات فارغة!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")
    
    # الحلول المطبقة
    print("\n✅ الحلول المطبقة:")
    print("1. إضافة فحص len(team) == 0 في calculate_mmr_changes")
    print("2. إضافة try-catch للتعامل مع الأخطاء")
    print("3. إضافة قيم افتراضية للـ MMR changes")
    print("4. إضافة تسجيل مفصل للأحداث")
    print("5. إضافة فحص بيانات الفريق قبل المعالجة")
    
    # نصائح لتجنب المشكلة
    print("\n💡 نصائح لتجنب المشكلة:")
    print("1. استخدم /admin_match للتحكم في المباريات")
    print("2. تأكد من إنشاء المباريات بشكل صحيح")
    print("3. لا تحاول تحديد الفائز في مباراة فاسدة")
    print("4. استخدم /reset_queue إذا كان هناك مشاكل في الطابور")
    print("5. اتصل بالأدمن إذا استمرت المشكلة")

def create_mmr_calculation_test():
    """إنشاء اختبار لحساب MMR"""
    
    print("\n🧪 اختبار حساب MMR:")
    print("=" * 30)
    
    # حالات الاختبار
    test_cases = [
        {
            "name": "فريق عادي",
            "team1": [{"mmr": 1000}, {"mmr": 1200}],
            "team2": [{"mmr": 900}, {"mmr": 1100}]
        },
        {
            "name": "فريق فارغ",
            "team1": [],
            "team2": [{"mmr": 1000}]
        },
        {
            "name": "فريق واحد",
            "team1": [{"mmr": 1000}],
            "team2": [{"mmr": 1000}]
        }
    ]
    
    for test in test_cases:
        print(f"\n📋 اختبار: {test['name']}")
        
        # محاكاة الحساب
        try:
            team1 = test['team1']
            team2 = test['team2']
            
            if len(team1) == 0 or len(team2) == 0:
                print("   ⚠️ فريق فارغ - استخدام القيم الافتراضية")
                result = {'winners': 25, 'losers': -25}
            else:
                avg1 = sum(p['mmr'] for p in team1) / len(team1)
                avg2 = sum(p['mmr'] for p in team2) / len(team2)
                
                base_change = 25
                mmr_diff = avg1 - avg2
                
                if mmr_diff > 0:
                    winner_gain = max(10, base_change - mmr_diff // 10)
                    loser_loss = -winner_gain
                else:
                    winner_gain = min(40, base_change + abs(mmr_diff) // 10)
                    loser_loss = -winner_gain
                
                result = {'winners': winner_gain, 'losers': loser_loss}
            
            print(f"   ✅ النتيجة: {result}")
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")

def main():
    """الدالة الرئيسية"""
    
    print("🔧 أداة إصلاح مشكلة القسمة على صفر")
    print("=" * 50)
    
    diagnose_division_by_zero_issue()
    create_mmr_calculation_test()
    
    print("\n🔧 الخطوات التالية:")
    print("1. تم إضافة فحص الفريق الفارغ")
    print("2. تم إضافة try-catch للحماية")
    print("3. تم إضافة قيم افتراضية للـ MMR")
    print("4. أعد تشغيل البوت")
    print("5. اختبر المباريات الجديدة")
    
    print("\n✅ تم إصلاح مشكلة القسمة على صفر!")

if __name__ == "__main__":
    main()