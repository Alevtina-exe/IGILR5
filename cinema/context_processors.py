import calendar
from datetime import datetime
import zoneinfo

def footer_info_processor(request):
    user_tz_name = "Europe/Minsk"
    user_now = datetime.now(zoneinfo.ZoneInfo(user_tz_name))
    text_cal = calendar.TextCalendar(calendar.MONDAY).formatmonth(user_now.year, user_now.month)

    return {
        'footer_user_tz': user_tz_name,
        'footer_current_date': user_now.strftime("%d/%m/%Y"),
        'footer_text_calendar': text_cal,
    }