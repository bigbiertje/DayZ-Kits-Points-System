// DayZKitsPoints - normal open-world zombie kill points
// Lives in 4_World because ZombieBase is not visible from 5_Mission on DayZ 1.29.

class NDZKP_OpenWorldPointsConfig
{
    bool Enabled;
    string ServerKey;
    int PointsPerZombieKill;
    bool LogZombieKills;

    void NDZKP_OpenWorldPointsConfig()
    {
        Enabled = true;
        ServerKey = "server1";
        PointsPerZombieKill = 1;
        LogZombieKills = true;
    }

    static string ConfigPath()
    {
        return "$profile:DayZKitsPoints\\PointsConfig.json";
    }

    static NDZKP_OpenWorldPointsConfig Load()
    {
        NDZKP_OpenWorldPointsConfig cfg = new NDZKP_OpenWorldPointsConfig();
        if (FileExist(ConfigPath()))
        {
            JsonFileLoader<NDZKP_OpenWorldPointsConfig>.JsonLoadFile(ConfigPath(), cfg);
        }
        else
        {
            if (!FileExist("$profile:DayZKitsPoints")) MakeDirectory("$profile:DayZKitsPoints");
            JsonFileLoader<NDZKP_OpenWorldPointsConfig>.JsonSaveFile(ConfigPath(), cfg);
            Print("[DayZKitsPoints] Created default points config: " + ConfigPath());
        }
        if (!cfg) cfg = new NDZKP_OpenWorldPointsConfig();
        if (cfg.ServerKey == "") cfg.ServerKey = "server1";
        if (cfg.PointsPerZombieKill < 0) cfg.PointsPerZombieKill = 0;
        return cfg;
    }
};

class NDZKP_ZombieKillPoints
{
    static PlayerBase GetKillerPlayer(Object killer)
    {
        if (!killer) return null;

        PlayerBase player = PlayerBase.Cast(killer);
        if (player) return player;

        EntityAI killerEntity = EntityAI.Cast(killer);
        if (killerEntity)
        {
            Man rootMan = killerEntity.GetHierarchyRootPlayer();
            player = PlayerBase.Cast(rootMan);
            if (player) return player;
        }

        return null;
    }

    static void Award(Object zombie, Object killer)
    {
        if (!GetGame() || !GetGame().IsServer()) return;
        if (!zombie) return;

        PlayerBase player = GetKillerPlayer(killer);
        if (!player || !player.IsAlive()) return;

        PlayerIdentity identity = player.GetIdentity();
        if (!identity) return;

        NDZKP_OpenWorldPointsConfig cfg = NDZKP_OpenWorldPointsConfig.Load();
        if (!cfg || !cfg.Enabled) return;
        if (cfg.PointsPerZombieKill <= 0) return;

        NDZKP_Points.Append(identity.GetPlainId(), identity.GetName(), cfg.ServerKey, cfg.PointsPerZombieKill, 0, "normal_zombie_kill");
        if (cfg.LogZombieKills)
        {
            Print("[DayZKitsPoints] Awarded " + cfg.PointsPerZombieKill.ToString() + " point(s) to " + identity.GetName() + " for zombie kill.");
        }
    }
};

modded class ZombieBase
{
    override void EEKilled(Object killer)
    {
        super.EEKilled(killer);
        NDZKP_ZombieKillPoints.Award(this, killer);
    }
};
