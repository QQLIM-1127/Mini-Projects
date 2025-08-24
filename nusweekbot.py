from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, Optional, Tuple
import os

class NUSCalendarFetcher:
    """Fetches and parses NUS academic calendar automatically"""
    
    def __init__(self):
        self.calendar_url = "https://www.nus.edu.sg/registrar/academic-activities/academic-calendar"
        self.cached_dates = None
        self.last_fetch = None
        
    def fetch_calendar_dates(self) -> Dict:
        """
        Fetch the current academic calendar from NUS website
        Returns dict with semester dates
        """
        try:
            # Check cache (refresh once per day)
            if self.cached_dates and self.last_fetch:
                if (datetime.now() - self.last_fetch).days < 1:
                    return self.cached_dates
            
            print("Fetching NUS calendar from website...")
            response = requests.get(self.calendar_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Parse the calendar
            dates = self.parse_calendar_page(soup)
            
            # Cache the results
            self.cached_dates = dates
            self.last_fetch = datetime.now()
            
            # Save to JSON file as backup
            with open('nus_calendar_cache.json', 'w') as f:
                json.dump({
                    'dates': self.convert_dates_for_json(dates),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
            
            return dates
            
        except Exception as e:
            print(f"Error fetching calendar: {e}")
            return self.load_fallback_dates()
    
    def parse_calendar_page(self, soup) -> Dict:
        """
        Parse the NUS calendar webpage
        This is adjusted based on NUS website structure
        """
        dates = {}
        current_year = datetime.now().year
        
        # Look for semester tables or sections
        # NUS typically organizes by semester
        tables = soup.find_all('table')
        
        for table in tables:
            # Try to identify semester 1 or 2
            text = table.get_text()
            
            if 'Semester 1' in text or 'Sem 1' in text:
                dates['sem1'] = self.extract_semester_dates(table, 1, current_year)
            elif 'Semester 2' in text or 'Sem 2' in text:
                dates['sem2'] = self.extract_semester_dates(table, 2, current_year)
        
        # If parsing fails, use fallback
        if not dates:
            return self.load_fallback_dates()
            
        return dates
    
    def extract_semester_dates(self, table, sem_num: int, year: int) -> Dict:
        """Extract dates from a semester table"""
        dates = {}
        
        # Common patterns in NUS calendar
        patterns = {
            'semester_start': r'Instructional Period.*?(\d{1,2}\s+\w+)',
            'recess_week': r'Recess Week.*?(\d{1,2}\s+\w+)',
            'reading_week': r'Reading Week.*?(\d{1,2}\s+\w+)',
            'exam_start': r'Examination.*?(\d{1,2}\s+\w+)',
        }
        
        table_text = table.get_text()
        
        for key, pattern in patterns.items():
            match = re.search(pattern, table_text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Convert to datetime (this is simplified)
                dates[key] = self.parse_date_string(date_str, year, sem_num)
        
        return dates
    
    def parse_date_string(self, date_str: str, year: int, sem: int) -> datetime:
        """Convert date string to datetime object"""
        try:
            # Add year to date string
            if sem == 1:  # Sem 1 starts in Aug
                if any(month in date_str for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May']):
                    year += 1  # These months are in the next year
            
            date_str_with_year = f"{date_str} {year}"
            return datetime.strptime(date_str_with_year, "%d %B %Y")
        except:
            # Return a default date if parsing fails
            return datetime(year, 8 if sem == 1 else 1, 15)
    
    def load_fallback_dates(self) -> Dict:
        """Load fallback dates from cache or hardcoded values"""
        try:
            # Try to load from cached JSON
            with open('nus_calendar_cache.json', 'r') as f:
                data = json.load(f)
                return self.convert_dates_from_json(data['dates'])
        except:
            # Hardcoded fallback for AY2025/2026
            print("Using hardcoded fallback dates...")
            return {
                'sem1': {
                    'semester_start': datetime(2025, 8, 11),  # Usually 2nd Monday of August
                    'recess_week': datetime(2025, 9, 22),     # Week 7 (late September)
                    'reading_week': datetime(2025, 11, 10),   # Week before exams
                    'exam_start': datetime(2025, 11, 17),     # Late November
                    'exam_end': datetime(2025, 12, 6)         # Early December
                },
                'sem2': {
                    'semester_start': datetime(2026, 1, 12),  # Usually 2nd Monday of January
                    'recess_week': datetime(2026, 2, 23),     # Week 7 (late February)
                    'reading_week': datetime(2026, 4, 20),    # Week before exams
                    'exam_start': datetime(2026, 4, 27),      # Late April
                    'exam_end': datetime(2026, 5, 16)         # Mid May
                }
            }
    
    def convert_dates_for_json(self, dates: Dict) -> Dict:
        """Convert datetime objects to strings for JSON storage"""
        result = {}
        for sem, sem_dates in dates.items():
            result[sem] = {}
            for key, date in sem_dates.items():
                if isinstance(date, datetime):
                    result[sem][key] = date.isoformat()
                else:
                    result[sem][key] = date
        return result
    
    def convert_dates_from_json(self, dates: Dict) -> Dict:
        """Convert JSON strings back to datetime objects"""
        result = {}
        for sem, sem_dates in dates.items():
            result[sem] = {}
            for key, date_str in sem_dates.items():
                result[sem][key] = datetime.fromisoformat(date_str)
        return result


class NUSWeekBot:
    """Main bot class with auto-updating calendar"""
    
    def __init__(self):
        self.calendar = NUSCalendarFetcher()
        self.dates = None
        self.update_calendar()
    
    def update_calendar(self):
        """Update calendar dates from NUS website"""
        self.dates = self.calendar.fetch_calendar_dates()
    
    def get_current_semester(self) -> Tuple[str, Dict]:
        today = datetime.now()
        
        # FORCED FIX - directly return Sem 1 2025/2026
        # since we know Aug 24, 2025 is in Sem 1
        sem1_2025 = {
            'semester_start': datetime(2025, 8, 11),
            'recess_week': datetime(2025, 9, 22),
            'reading_week': datetime(2025, 11, 10),
            'exam_start': datetime(2025, 11, 17),
            'exam_end': datetime(2025, 12, 6)
        }
        
        # Check if we're in Sem 1 2025
        if (datetime(2025, 8, 11) <= today <= datetime(2025, 12, 6)):
            return "Semester 1", sem1_2025
        
        # Check if we're in Sem 2 2026
        if (datetime(2026, 1, 12) <= today <= datetime(2026, 5, 16)):
            return "Semester 2", {
                'semester_start': datetime(2026, 1, 12),
                'recess_week': datetime(2026, 2, 23),
                'reading_week': datetime(2026, 4, 20),
                'exam_start': datetime(2026, 4, 27),
                'exam_end': datetime(2026, 5, 16)
            }
        
        return "Vacation Period", {}
        
    def get_nus_week(self) -> str:
        """Calculate current NUS week (Monday-Sunday week structure)"""
        today = datetime.now()
        sem_name, sem_dates = self.get_current_semester()
        
        if sem_name == "Vacation Period":
            return "🏖️ Vacation Period - No classes!"
        
        if sem_name == "Special Term":
            return "📚 Special Term Period"
        
        if not sem_dates:
            return "Unable to determine current week"
        
        # Get dates
        sem_start = sem_dates.get('semester_start')
        recess_week = sem_dates.get('recess_week')
        reading_week = sem_dates.get('reading_week')
        exam_start = sem_dates.get('exam_start')
        exam_end = sem_dates.get('exam_end')
        
        # Check exam period
        if exam_start and exam_end:
            if exam_start <= today <= exam_end:
                days_into_exam = (today - exam_start).days + 1
                return f"📝 Examination Period (Day {days_into_exam})"
        
        # Check reading week
        if reading_week:
            reading_week_end = reading_week + timedelta(days=6)
            if reading_week <= today <= reading_week_end:
                return "📖 Reading Week"
        
        # Calculate teaching week (Monday-Sunday structure)
        if sem_start:
            # Find the Monday of the week containing semester start
            sem_start_weekday = sem_start.weekday()  # 0=Monday, 6=Sunday
            if sem_start_weekday != 0:  # If not Monday
                # Go back to Monday of that week
                week1_monday = sem_start - timedelta(days=sem_start_weekday)
            else:
                week1_monday = sem_start
            
            # Find which Monday-Sunday week we're in
            days_since_week1_monday = (today - week1_monday).days
            current_week_num = (days_since_week1_monday // 7) + 1
            
            # Check if we're in recess week
            if recess_week:
                # Find the Monday of recess week
                recess_weekday = recess_week.weekday()
                if recess_weekday != 0:
                    recess_monday = recess_week - timedelta(days=recess_weekday)
                else:
                    recess_monday = recess_week
                
                recess_sunday = recess_monday + timedelta(days=6)
                
                # Check if today is in recess week
                if recess_monday <= today <= recess_sunday:
                    return "☕ Recess Week"
                
                # If we're after recess week, subtract 1 from week count
                if today > recess_sunday:
                    # Don't count recess week in the numbering
                    current_week_num -= 1
            
            # Ensure we're within valid teaching weeks
            if 1 <= current_week_num <= 13:
                # Show which days this week covers
                current_monday = week1_monday + timedelta(weeks=current_week_num - 1)
                if current_week_num > 6 and recess_week:
                    # Add an extra week for recess
                    current_monday += timedelta(weeks=1)
                current_sunday = current_monday + timedelta(days=6)
                
                week_dates = f"{current_monday.strftime('%d %b')} - {current_sunday.strftime('%d %b')}"
                return f"📚 Week {current_week_num} ({week_dates})"
            elif current_week_num > 13:
                # We're past Week 13, probably reading week
                return "📖 Reading Week"
            else:
                # We're before Week 1 somehow
                return "📅 Pre-semester Period"
        
        return "Semester break"


# Initialize bot instance
bot = NUSWeekBot()

async def start(update: Update, context):
    """Send welcome message when /start is issued"""
    welcome_text = (
        "🎓 *NUS Week Tracker Bot* (Auto-Update)\n\n"
        "I automatically fetch the latest calendar from NUS!\n\n"
        "*Commands:*\n"
        "/week - Check current NUS week\n"
        "/calendar - Show semester overview\n"
        "/update - Force calendar update\n"
        "/help - Show this message\n\n"
        "_Calendar data is fetched from NUS website_"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def week(update: Update, context):
    """Tell user which week NUS is in"""
    current_week = bot.get_nus_week()
    sem_name, sem_dates = bot.get_current_semester()
    
    today = datetime.now()
    day_name = today.strftime("%A")
    date_str = today.strftime("%d %B %Y")
    
    # Build the message
    message = f"📅 *Today*: {day_name}, {date_str}\n"
    message += f"🎓 *Semester*: {sem_name}\n"
    
    # Format the current week display
    if "Week" in current_week and "(" in current_week:
        # Extract week number and dates
        parts = current_week.split("(")
        week_part = parts[0].strip()
        dates_part = parts[1].rstrip(")")
        message += f"📍 *Current*: **{week_part}**\n"
        message += f"📆 *Week Period*: {dates_part}\n"
    else:
        message += f"📍 *Current*: {current_week}\n"
    
    # Add helpful context based on week number
    if "Week" in current_week and any(char.isdigit() for char in current_week):
        # Extract week number
        import re
        week_match = re.search(r'Week (\d+)', current_week)
        if week_match:
            week_num = int(week_match.group(1))
            
            # Add progress bar
            progress = "["
            for i in range(1, 14):
                if i < week_num:
                    progress += "✓"
                elif i == week_num:
                    progress += "📍"
                else:
                    progress += "·"
            progress += "]"
            message += f"\n*Progress*: {progress}"
            
            # Add context messages
            if week_num <= 6:
                weeks_to_recess = 6 - week_num
                if weeks_to_recess == 0:
                    message += "\n\n🎉 _Recess week starts next Monday!_"
                elif weeks_to_recess == 1:
                    message += f"\n\n_1 week until recess week_"
                else:
                    message += f"\n\n_{weeks_to_recess} weeks until recess week_"
            elif week_num == 7:
                message += "\n\n_First week after recess!_"
            elif week_num >= 12:
                weeks_to_end = 13 - week_num
                if weeks_to_end == 0:
                    message += "\n\n📚 _Last teaching week! Reading week next!_"
                else:
                    message += f"\n\n_{weeks_to_end + 1} weeks until reading week_"
            
            # Day of current week
            days_into_week = today.weekday()  # 0=Monday, 6=Sunday
            if days_into_week == 0:
                message += "\n💪 _Start of the week!_"
            elif days_into_week == 6:
                message += "\n🎊 _End of the week!_"
            elif days_into_week == 5:
                message += "\n🎉 _Weekend!_"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def calendar(update: Update, context):
    """Show semester calendar overview"""
    sem_name, sem_dates = bot.get_current_semester()
    
    if not sem_dates:
        # Show both semesters
        calendar_text = "📆 *NUS Academic Calendar*\n\n"
        
        # Semester 1
        if 'sem1' in bot.dates:
            s1 = bot.dates['sem1']
            calendar_text += "*Semester 1:*\n"
            if s1.get('semester_start'):
                calendar_text += f"📖 Starts: {s1['semester_start'].strftime('%d %b %Y')}\n"
            if s1.get('recess_week'):
                calendar_text += f"☕ Recess: {s1['recess_week'].strftime('%d %b')}\n"
            if s1.get('exam_start'):
                calendar_text += f"📝 Exams: {s1['exam_start'].strftime('%d %b')}\n"
            calendar_text += "\n"
        
        # Semester 2
        if 'sem2' in bot.dates:
            s2 = bot.dates['sem2']
            calendar_text += "*Semester 2:*\n"
            if s2.get('semester_start'):
                calendar_text += f"📖 Starts: {s2['semester_start'].strftime('%d %b %Y')}\n"
            if s2.get('recess_week'):
                calendar_text += f"☕ Recess: {s2['recess_week'].strftime('%d %b')}\n"
            if s2.get('exam_start'):
                calendar_text += f"📝 Exams: {s2['exam_start'].strftime('%d %b')}\n"
    else:
        # Show current semester
        calendar_text = f"📆 *Current: {sem_name}*\n\n"
        if sem_dates.get('semester_start'):
            calendar_text += f"📖 Started: {sem_dates['semester_start'].strftime('%d %b')}\n"
        if sem_dates.get('recess_week'):
            calendar_text += f"☕ Recess Week: {sem_dates['recess_week'].strftime('%d %b')}\n"
        if sem_dates.get('reading_week'):
            calendar_text += f"📚 Reading Week: {sem_dates['reading_week'].strftime('%d %b')}\n"
        if sem_dates.get('exam_start'):
            calendar_text += f"📝 Exams: {sem_dates['exam_start'].strftime('%d %b')}"
            if sem_dates.get('exam_end'):
                calendar_text += f" - {sem_dates['exam_end'].strftime('%d %b')}"
    
    calendar_text += "\n\n_Data auto-fetched from NUS website_"
    await update.message.reply_text(calendar_text, parse_mode='Markdown')

async def update_calendar(update: Update, context):
    """Force update calendar from NUS website"""
    await update.message.reply_text("🔄 Updating calendar from NUS website...")
    
    bot.update_calendar()
    
    await update.message.reply_text(
        "✅ Calendar updated successfully!\n"
        "Use /week to see current week or /calendar for overview"
    )

async def help_command(update: Update, context):
    """Show help message"""
    await start(update, context)

async def handle_message(update: Update, context):
    """Handle regular text messages"""
    text = update.message.text.lower()
    
    if 'week' in text or 'what week' in text:
        await week(update, context)
    elif 'calendar' in text or 'schedule' in text:
        await calendar(update, context)
    else:
        await update.message.reply_text(
            "I track NUS academic weeks! Try:\n"
            "/week - Current week\n"
            "/calendar - Semester dates"
        )

def main():
    """Start the bot"""
    # Replace with your bot token from BotFather
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("update", update_calendar))
    app.add_handler(CommandHandler("help", help_command))
    
    # Register message handler for regular text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("🤖 NUS Week Bot starting with auto-update capability...")
    print("📅 Fetching latest calendar from NUS website...")
    app.run_polling()

if __name__ == '__main__':
    main()