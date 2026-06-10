class CfgPatches
{
    class DayZ_KitsPoints
    {
        units[] = {};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data"};
    };
};

class CfgMods
{
    class DayZ_KitsPoints
    {
        dir = "DayZ_KitsPoints";
        picture = "";
        action = "";
        hideName = 1;
        hidePicture = 1;
        name = "DayZ Kits & Points";
        credits = "Public community release";
        author = "Community Release";
        authorID = "0";
        version = "1.2.0-public";
        extra = 0;
        type = "mod";
        dependencies[] = {"Game", "World", "Mission"};

        class defs
        {
            class worldScriptModule
            {
                value = "";
                files[] = {"DayZ_KitsPoints/scripts/4_World"};
            };
            class missionScriptModule
            {
                value = "";
                files[] = {"DayZ_KitsPoints/scripts/5_Mission"};
            };
        };
    };
};
