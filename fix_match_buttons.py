#!/usr/bin/env python3
"""
Fix Match Buttons - إصلاح مشكلة أزرار المباريات
"""

import sqlite3
import json

def fix_corrupted_match():
    """إصلاح المباراة المعطلة في قاعدة البيانات"""
    
    print("🔧 إصلاح المباراة المعطلة...")
    
    try:
        conn = sqlite3.connect("players.db")
        c = conn.cursor()
        
        # البحث عن المباريات المعطلة
        c.execute("SELECT match_id, team1_players, team2_players, winner FROM matches WHERE winner IS NULL")
        corrupted_matches = c.fetchall()
        
        print(f"📋 عدد المباريات المعطلة: {len(corrupted_matches)}")
        
        for match_id, team1, team2, winner in corrupted_matches:
            print(f"🎮 Match {match_id}:")
            print(f"   Team1: {team1}")
            print(f"   Team2: {team2}")
            print(f"   Winner: {winner}")
            
            # إذا كان team2 فارغ، قم بإلغاء المباراة
            if not team2 or team2.strip() == "":
                print(f"   🚫 إلغاء المباراة {match_id} - فريق 2 فارغ")
                c.execute("UPDATE matches SET winner = -1, cancelled = 1 WHERE match_id = ?", (match_id,))
            else:
                print(f"   ✅ المباراة {match_id} سليمة")
        
        conn.commit()
        conn.close()
        
        print("✅ تم إصلاح المباريات المعطلة!")
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح المباريات: {e}")

def reset_active_matches():
    """إعادة تعيين المباريات النشطة"""
    
    print("\n🔄 إعادة تعيين المباريات النشطة...")
    
    try:
        conn = sqlite3.connect("players.db")
        c = conn.cursor()
        
        # إلغاء جميع المباريات غير المكتملة
        c.execute("UPDATE matches SET winner = -1, cancelled = 1 WHERE winner IS NULL OR winner = 0")
        rows_affected = c.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ تم إلغاء {rows_affected} مباريات غير مكتملة")
        
    except Exception as e:
        print(f"❌ خطأ في إعادة التعيين: {e}")

def show_database_status():
    """عرض حالة قاعدة البيانات"""
    
    print("\n📊 حالة قاعدة البيانات:")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect("players.db")
        c = conn.cursor()
        
        # عرض إحصائيات المباريات
        c.execute("SELECT COUNT(*) FROM matches")
        total_matches = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM matches WHERE winner = 1")
        team1_wins = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM matches WHERE winner = 2")
        team2_wins = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM matches WHERE winner = 0")
        ties = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM matches WHERE winner = -1 OR cancelled = 1")
        cancelled = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM matches WHERE winner IS NULL")
        pending = c.fetchone()[0]
        
        print(f"📋 إجمالي المباريات: {total_matches}")
        print(f"🏆 انتصارات فريق 1: {team1_wins}")
        print(f"🏆 انتصارات فريق 2: {team2_wins}")
        print(f"🤝 التعادل: {ties}")
        print(f"🚫 مباريات ملغاة: {cancelled}")
        print(f"⏳ مباريات معلقة: {pending}")
        
        # عرض إحصائيات اللاعبين
        c.execute("SELECT COUNT(*) FROM players")
        total_players = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM players WHERE wins > 0 OR losses > 0")
        active_players = c.fetchone()[0]
        
        print(f"\n👥 إجمالي اللاعبين: {total_players}")
        print(f"🎮 اللاعبين النشطين: {active_players}")
        
        # عرض أفضل 5 لاعبين
        c.execute("SELECT username, mmr, wins, losses FROM players WHERE wins > 0 OR losses > 0 ORDER BY mmr DESC LIMIT 5")
        top_players = c.fetchall()
        
        print(f"\n🏆 أفضل 5 لاعبين:")
        for i, (username, mmr, wins, losses) in enumerate(top_players):
            print(f"   {i+1}. {username} - {mmr} MMR ({wins}W/{losses}L)")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ خطأ في عرض الحالة: {e}")

def main():
    """الدالة الرئيسية"""
    
    print("🛠️ أداة إصلاح مشاكل المباريات")
    print("=" * 50)
    
    # إصلاح المباريات المعطلة
    fix_corrupted_match()
    
    # إعادة تعيين المباريات النشطة
    reset_active_matches()
    
    # عرض حالة قاعدة البيانات
    show_database_status()
    
    print("\n🔧 الخطوات التالية:")
    print("1. أعد تشغيل البوت")
    print("2. استخدم /setup لإنشاء قنوات جديدة")
    print("3. جرب إنشاء مباراة جديدة")
    print("4. استخدم /admin_match للتحكم في المباريات")
    
    print("\n✅ تم إصلاح جميع المشاكل!")

if __name__ == "__main__":
    main()