class NDZKS_Time
{
    static bool IsLeapYear(int year)
    {
        if ((year % 400) == 0) return true;
        if ((year % 100) == 0) return false;
        if ((year % 4) == 0) return true;
        return false;
    }

    static int DaysBeforeMonth(int year, int month)
    {
        int days = 0;

        if (month > 1) days += 31;
        if (month > 2)
        {
            if (IsLeapYear(year)) days += 29;
            else days += 28;
        }
        if (month > 3) days += 31;
        if (month > 4) days += 30;
        if (month > 5) days += 31;
        if (month > 6) days += 30;
        if (month > 7) days += 31;
        if (month > 8) days += 31;
        if (month > 9) days += 30;
        if (month > 10) days += 31;
        if (month > 11) days += 30;

        return days;
    }

    static int GetNowUTC()
    {
        int year;
        int month;
        int day;
        int hour;
        int minute;
        int second;

        GetYearMonthDayUTC(year, month, day);
        GetHourMinuteSecondUTC(hour, minute, second);

        int days = 0;
        for (int y = 1970; y < year; y++)
        {
            if (IsLeapYear(y)) days += 366;
            else days += 365;
        }

        days += DaysBeforeMonth(year, month);
        days += day - 1;

        return (days * 86400) + (hour * 3600) + (minute * 60) + second;
    }

    static string FormatRemaining(int seconds)
    {
        if (seconds <= 0) return "ready now";

        int days = seconds / 86400;
        seconds = seconds % 86400;
        int hours = seconds / 3600;
        seconds = seconds % 3600;
        int minutes = seconds / 60;

        string output = "";

        if (days > 0) output += days.ToString() + "d ";
        if (hours > 0) output += hours.ToString() + "h ";
        if (minutes > 0) output += minutes.ToString() + "m";

        if (output == "") output = "less than 1m";
        return output;
    }
}
