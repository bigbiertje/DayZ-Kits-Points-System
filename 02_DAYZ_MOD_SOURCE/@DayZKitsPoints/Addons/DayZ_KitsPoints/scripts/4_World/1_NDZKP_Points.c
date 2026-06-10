// DayZKitsPoints - standalone point event queue for website integration

class NDZKP_PointEvent
{
    string eventRef;
    string steam64;
    string playerName;
    string serverKey;
    string reason;
    int points;
    int wave;
    int createdTime;

    void NDZKP_PointEvent()
    {
        eventRef = "";
        steam64 = "";
        playerName = "";
        serverKey = "server1";
        reason = "normal_zombie_kill";
        points = 0;
        wave = 0;
        createdTime = 0;
    }
};

class NDZKP_PointEventQueue
{
    ref array<ref NDZKP_PointEvent> Events;

    void NDZKP_PointEventQueue()
    {
        Events = new array<ref NDZKP_PointEvent>();
    }
};

class NDZKP_Points
{
    static string QueuePath()
    {
        return "$profile:DayZKitsPoints\\PointEvents.json";
    }

    static void EnsureFolder()
    {
        if (!FileExist("$profile:DayZKitsPoints"))
        {
            MakeDirectory("$profile:DayZKitsPoints");
        }
    }

    static void Append(string steam64, string playerName, string serverKey, int points, int wave, string reason)
    {
        if (steam64 == "") return;
        if (points <= 0) return;

        EnsureFolder();

        NDZKP_PointEventQueue queue = new NDZKP_PointEventQueue();
        if (FileExist(QueuePath()))
        {
            JsonFileLoader<NDZKP_PointEventQueue>.JsonLoadFile(QueuePath(), queue);
        }
        if (!queue) queue = new NDZKP_PointEventQueue();
        if (!queue.Events) queue.Events = new array<ref NDZKP_PointEvent>();

        NDZKP_PointEvent ev = new NDZKP_PointEvent();
        ev.steam64 = steam64;
        ev.playerName = playerName;
        ev.serverKey = serverKey;
        ev.points = points;
        ev.wave = wave;
        ev.reason = reason;
        ev.createdTime = GetGame().GetTime();
        ev.eventRef = serverKey + "-" + steam64 + "-" + reason + "-" + ev.createdTime.ToString();

        queue.Events.Insert(ev);
        JsonFileLoader<NDZKP_PointEventQueue>.JsonSaveFile(QueuePath(), queue);
    }
};
