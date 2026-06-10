static ref NDZKS_Manager g_NDZKS_Manager;

static NDZKS_Manager GetNDZKSManager()
{
    if (!g_NDZKS_Manager)
    {
        g_NDZKS_Manager = new NDZKS_Manager;
    }

    return g_NDZKS_Manager;
}

class NDZKS_Manager
{
    protected static const string ROOT_DIR = "$profile:DayZKitsPoints";
    protected static const string COOLDOWN_DIR = "$profile:DayZKitsPoints/Cooldowns";
    protected static const string CONFIG_PATH = "$profile:DayZKitsPoints/KitConfig.json";
    protected static const string DISCORD_QUEUE_PATH = "$profile:DayZKitsPoints/DiscordQueue.json";
    protected static const string DISCORD_RESPONSES_PATH = "$profile:DayZKitsPoints/DiscordResponses.json";

    protected ref NDZKS_Config m_Config;
    protected bool m_DiscordLoopStarted;

    void NDZKS_Manager()
    {
        EnsureFolders();
        LoadConfig();
        StartDiscordBridgeLoop();
    }

    void EnsureFolders()
    {
        if (!FileExist(ROOT_DIR)) MakeDirectory(ROOT_DIR);
        if (!FileExist(COOLDOWN_DIR)) MakeDirectory(COOLDOWN_DIR);
    }

    void LoadConfig()
    {
        m_Config = new NDZKS_Config;

        if (!FileExist(CONFIG_PATH))
        {
            BuildDefaultConfig();
            JsonFileLoader<NDZKS_Config>.JsonSaveFile(CONFIG_PATH, m_Config);
            CreateEmptyDiscordFilesIfMissing();
            Print("[DayZKitsPoints] Created default config: " + CONFIG_PATH);
            return;
        }

        JsonFileLoader<NDZKS_Config>.JsonLoadFile(CONFIG_PATH, m_Config);

        if (!m_Config)
        {
            m_Config = new NDZKS_Config;
            BuildDefaultConfig();
            JsonFileLoader<NDZKS_Config>.JsonSaveFile(CONFIG_PATH, m_Config);
            Print("[DayZKitsPoints] Config failed to load, regenerated default config.");
        }

        ApplyConfigDefaults();
        CreateEmptyDiscordFilesIfMissing();
    }

    void ReloadConfig()
    {
        LoadConfig();
    }

    protected void ApplyConfigDefaults()
    {
        if (!m_Config.Kits) m_Config.Kits = new array<ref NDZKS_Kit>;
        if (!m_Config.AdminSteamIds) m_Config.AdminSteamIds = new array<string>;
        if (m_Config.CommandPrefix == "") m_Config.CommandPrefix = "/kit";
        if (m_Config.ChatTag == "") m_Config.ChatTag = "[Kits]";
        if (m_Config.DiscordPollSeconds <= 0) m_Config.DiscordPollSeconds = 10;
        if (m_Config.DiscordResponseHistoryLimit <= 0) m_Config.DiscordResponseHistoryLimit = 250;
    }

    protected void CreateEmptyDiscordFilesIfMissing()
    {
        if (!FileExist(DISCORD_QUEUE_PATH))
        {
            NDZKS_DiscordQueue queue = new NDZKS_DiscordQueue;
            JsonFileLoader<NDZKS_DiscordQueue>.JsonSaveFile(DISCORD_QUEUE_PATH, queue);
        }

        if (!FileExist(DISCORD_RESPONSES_PATH))
        {
            NDZKS_DiscordResponseFile responses = new NDZKS_DiscordResponseFile;
            JsonFileLoader<NDZKS_DiscordResponseFile>.JsonSaveFile(DISCORD_RESPONSES_PATH, responses);
        }
    }

    protected void StartDiscordBridgeLoop()
    {
        if (m_DiscordLoopStarted) return;

        int pollMs = 10000;
        if (m_Config && m_Config.DiscordPollSeconds > 0)
        {
            pollMs = m_Config.DiscordPollSeconds * 1000;
        }

        GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ProcessDiscordQueue, pollMs, true);
        m_DiscordLoopStarted = true;
        Print("[DayZKitsPoints] Discord bridge polling enabled every " + (pollMs / 1000).ToString() + " seconds.");
    }

    protected NDZKS_Item MakeItem(string className, int quantity = -1, int ammoCount = -1, float health01 = -1.0)
    {
        NDZKS_Item item = new NDZKS_Item;
        item.ClassName = className;
        item.Quantity = quantity;
        item.AmmoCount = ammoCount;
        item.Health01 = health01;
        return item;
    }

    protected NDZKS_Kit MakeKit(string name, string displayName, int cooldownSeconds)
    {
        NDZKS_Kit kit = new NDZKS_Kit;
        kit.Name = name;
        kit.DisplayName = displayName;
        kit.CooldownSeconds = cooldownSeconds;
        kit.Enabled = true;
        return kit;
    }

    protected void BuildDefaultConfig()
    {
        m_Config.CommandPrefix = "/kit";
        m_Config.ShowKitListWhenUsingKitOnly = true;
        m_Config.SpawnOverflowOnGround = true;
        m_Config.LogClaimsToServerRPT = true;
        m_Config.ChatTag = "[Kits]";
        m_Config.DiscordBridgeEnabled = true;
        m_Config.DiscordPollSeconds = 10;
        m_Config.DiscordSendInGameMessage = true;
        m_Config.DiscordResponseHistoryLimit = 250;

        m_Config.Kits.Clear();
        if (!m_Config.AdminSteamIds) m_Config.AdminSteamIds = new array<string>;
        m_Config.AdminSteamIds.Clear();

        NDZKS_Kit medical = MakeKit("medical", "Medical Kit", 28800);
        medical.Items.Insert(MakeItem("BandageDressing", 2));
        medical.Items.Insert(MakeItem("Morphine", 1));
        medical.Items.Insert(MakeItem("TetracyclineAntibiotics", 12));
        medical.Items.Insert(MakeItem("CharcoalTablets", 12));
        medical.Items.Insert(MakeItem("SalineBagIV", 1));
        medical.Items.Insert(MakeItem("BloodTestKit", 1));
        m_Config.Kits.Insert(medical);

        NDZKS_Kit food = MakeKit("food", "Food Kit", 43200);
        food.Items.Insert(MakeItem("BakedBeansCan", 1));
        food.Items.Insert(MakeItem("TunaCan", 1));
        food.Items.Insert(MakeItem("SardinesCan", 1));
        food.Items.Insert(MakeItem("SodaCan_Cola", 1));
        food.Items.Insert(MakeItem("Canteen", 100));
        food.Items.Insert(MakeItem("KitchenKnife", 1));
        m_Config.Kits.Insert(food);

        NDZKS_Kit weapon = MakeKit("weapon", "Weapon Kit", 86400);
        NDZKS_Item ak = MakeItem("AK74", 1);
        ak.ItemAttachments.Insert(MakeItem("Mag_AK74_30Rnd", -1, 30));
        weapon.Items.Insert(ak);
        weapon.Items.Insert(MakeItem("Ammo_545x39", 40));
        weapon.Items.Insert(MakeItem("CombatKnife", 1));
        weapon.Items.Insert(MakeItem("Mag_AK74_30Rnd", -1, 30));
        m_Config.Kits.Insert(weapon);

        NDZKS_Kit building = MakeKit("building", "Building Supply Kit", 604800);
        building.Items.Insert(MakeItem("NailBox", 2));
        building.Items.Insert(MakeItem("WoodenPlank", 20));
        building.Items.Insert(MakeItem("MetalWire", 1));
        building.Items.Insert(MakeItem("Rope", 1));
        building.Items.Insert(MakeItem("Handsaw", 1));
        building.Items.Insert(MakeItem("Hatchet", 1));
        building.Items.Insert(MakeItem("CombinationLock", 1));
        m_Config.Kits.Insert(building);
    }

    bool HandleChatCommand(PlayerBase player, string message)
    {
        if (!player || !player.GetIdentity()) return false;
        if (!m_Config) LoadConfig();
        if (!m_Config) return false;

        string parts[10];
        message.ParseString(parts);

        string command = parts[0];
        string argument = parts[1];
        string extra = parts[2];

        if (parts[0] == "/")
        {
            command = "/" + parts[1];
            argument = parts[2];
            extra = parts[3];
        }

        command.ToLower();
        string prefix = m_Config.CommandPrefix;
        prefix.ToLower();

        if (command != prefix && command != "/kits") return false;

        argument.ToLower();
        extra.ToLower();

        if (command == "/kits" || argument == "" || argument == "list")
        {
            SendKitList(player);
            return true;
        }

        if (argument == "reload")
        {
            if (IsServerAdmin(player))
            {
                ReloadConfig();
                SendMessage(player, "Config reloaded.");
            }
            else
            {
                SendMessage(player, "You are not allowed to reload the kit config.");
            }
            return true;
        }

        if (argument == "info" && extra != "")
        {
            SendKitInfo(player, extra);
            return true;
        }

        ClaimKitFromGame(player, argument);
        return true;
    }

    protected bool IsServerAdmin(PlayerBase player)
    {
        if (!player || !player.GetIdentity()) return false;
        if (!m_Config || !m_Config.AdminSteamIds) return false;

        string playerId = GetPlayerId(player);
        for (int i = 0; i < m_Config.AdminSteamIds.Count(); i++)
        {
            if (m_Config.AdminSteamIds.Get(i) == playerId) return true;
        }

        return false;
    }

    protected void SendKitList(PlayerBase player)
    {
        string list = "Available kits:";

        for (int i = 0; i < m_Config.Kits.Count(); i++)
        {
            NDZKS_Kit kit = m_Config.Kits.Get(i);
            if (!kit || !kit.Enabled) continue;

            list += " " + kit.Name + "(" + NDZKS_Time.FormatRemaining(kit.CooldownSeconds) + ")";
        }

        SendMessage(player, list);
        SendMessage(player, "Use " + m_Config.CommandPrefix + " medical, food, weapon, or building.");
    }

    protected void SendKitInfo(PlayerBase player, string kitName)
    {
        NDZKS_Kit kit = FindKit(kitName);
        if (!kit)
        {
            SendMessage(player, "That kit does not exist.");
            return;
        }

        NDZKS_PlayerData data = LoadPlayerData(player);
        int lastClaim = GetLastClaim(data, kit.Name);
        int now = NDZKS_Time.GetNowUTC();
        int remaining = (lastClaim + kit.CooldownSeconds) - now;

        if (remaining <= 0) SendMessage(player, kit.DisplayName + " is ready now.");
        else SendMessage(player, kit.DisplayName + " cooldown left: " + NDZKS_Time.FormatRemaining(remaining) + ".");
    }

    protected void ClaimKitFromGame(PlayerBase player, string kitName)
    {
        ClaimKitInternal(player, kitName, true, "game", "");
    }

    protected NDZKS_ClaimResult ClaimKitInternal(PlayerBase player, string kitName, bool sendPlayerMessage, string source, string discordUserName)
    {
        NDZKS_ClaimResult result = new NDZKS_ClaimResult;

        if (!player || !player.GetIdentity())
        {
            result.Status = "player_error";
            result.Message = "Player was not found.";
            return result;
        }

        NDZKS_Kit kit = FindKit(kitName);
        if (!kit || !kit.Enabled)
        {
            result.Status = "unknown_kit";
            result.Message = "Unknown kit. Type /kits to see available kits.";
            if (sendPlayerMessage) SendMessage(player, result.Message);
            return result;
        }

        NDZKS_PlayerData data = LoadPlayerData(player);
        int now = NDZKS_Time.GetNowUTC();
        int lastClaim = GetLastClaim(data, kit.Name);
        int nextClaim = lastClaim + kit.CooldownSeconds;

        if (lastClaim > 0 && now < nextClaim)
        {
            int remaining = nextClaim - now;
            result.Status = "cooldown";
            result.Message = kit.DisplayName + " is still on cooldown. Time left: " + NDZKS_Time.FormatRemaining(remaining) + ".";
            if (sendPlayerMessage) SendMessage(player, result.Message);
            return result;
        }

        for (int i = 0; i < kit.Items.Count(); i++)
        {
            SpawnConfiguredItem(player, kit.Items.Get(i), null);
        }

        SetLastClaim(data, kit.Name, now);
        SavePlayerData(data);

        result.Success = true;
        result.Status = "success";
        result.Message = "You claimed: " + kit.DisplayName + ".";

        if (sendPlayerMessage)
        {
            if (source == "discord") SendMessage(player, "Discord redeemed: " + kit.DisplayName + ".");
            else SendMessage(player, result.Message);
        }

        if (m_Config.LogClaimsToServerRPT)
        {
            string extra = "";
            if (source == "discord") extra = " through Discord by " + discordUserName;
            Print("[DayZKitsPoints] " + player.GetIdentity().GetName() + " (" + GetPlayerId(player) + ") claimed kit: " + kit.Name + " via " + source + extra);
        }

        return result;
    }

    protected NDZKS_Kit FindKit(string kitName)
    {
        kitName.ToLower();

        for (int i = 0; i < m_Config.Kits.Count(); i++)
        {
            NDZKS_Kit kit = m_Config.Kits.Get(i);
            if (!kit) continue;

            string current = kit.Name;
            current.ToLower();

            if (current == kitName) return kit;
        }

        return null;
    }

    protected string GetPlayerId(PlayerBase player)
    {
        if (!player || !player.GetIdentity()) return "unknown";

        string plainId = player.GetIdentity().GetPlainId();
        if (plainId != "") return plainId;

        string id = player.GetIdentity().GetId();
        if (id != "") return id;

        return player.GetIdentity().GetName();
    }

    protected string GetPlayerDataPath(PlayerBase player)
    {
        return COOLDOWN_DIR + "/" + GetPlayerId(player) + ".json";
    }

    protected NDZKS_PlayerData LoadPlayerData(PlayerBase player)
    {
        NDZKS_PlayerData data = new NDZKS_PlayerData;
        string path = GetPlayerDataPath(player);

        if (FileExist(path))
        {
            JsonFileLoader<NDZKS_PlayerData>.JsonLoadFile(path, data);
        }

        if (!data)
        {
            data = new NDZKS_PlayerData;
        }

        data.PlayerId = GetPlayerId(player);
        data.PlayerName = player.GetIdentity().GetName();

        if (!data.Cooldowns)
        {
            data.Cooldowns = new array<ref NDZKS_CooldownRecord>;
        }

        return data;
    }

    protected void SavePlayerData(NDZKS_PlayerData data)
    {
        if (!data || data.PlayerId == "") return;
        string path = COOLDOWN_DIR + "/" + data.PlayerId + ".json";
        JsonFileLoader<NDZKS_PlayerData>.JsonSaveFile(path, data);
    }

    protected int GetLastClaim(NDZKS_PlayerData data, string kitName)
    {
        if (!data || !data.Cooldowns) return 0;
        kitName.ToLower();

        for (int i = 0; i < data.Cooldowns.Count(); i++)
        {
            NDZKS_CooldownRecord record = data.Cooldowns.Get(i);
            if (!record) continue;

            string current = record.KitName;
            current.ToLower();

            if (current == kitName) return record.LastClaimUTC;
        }

        return 0;
    }

    protected void SetLastClaim(NDZKS_PlayerData data, string kitName, int timestamp)
    {
        if (!data.Cooldowns)
        {
            data.Cooldowns = new array<ref NDZKS_CooldownRecord>;
        }

        kitName.ToLower();

        for (int i = 0; i < data.Cooldowns.Count(); i++)
        {
            NDZKS_CooldownRecord record = data.Cooldowns.Get(i);
            if (!record) continue;

            string current = record.KitName;
            current.ToLower();

            if (current == kitName)
            {
                record.LastClaimUTC = timestamp;
                return;
            }
        }

        NDZKS_CooldownRecord newRecord = new NDZKS_CooldownRecord;
        newRecord.KitName = kitName;
        newRecord.LastClaimUTC = timestamp;
        data.Cooldowns.Insert(newRecord);
    }

    protected EntityAI SpawnConfiguredItem(PlayerBase player, NDZKS_Item itemConfig, EntityAI parent)
    {
        if (!player || !itemConfig || itemConfig.ClassName == "") return null;

        EntityAI entity;

        if (parent)
        {
            if (GetGame().ConfigIsExisting(CFG_MAGAZINESPATH + " " + itemConfig.ClassName) && parent.IsWeapon())
            {
                Weapon_Base weapon;
                if (Class.CastTo(weapon, parent))
                {
                    entity = EntityAI.Cast(weapon.SpawnAttachedMagazine(itemConfig.ClassName));
                }
            }

            if (!entity)
            {
                entity = EntityAI.Cast(parent.GetInventory().CreateAttachment(itemConfig.ClassName));
            }

            if (!entity)
            {
                entity = EntityAI.Cast(parent.GetInventory().CreateInInventory(itemConfig.ClassName));
            }
        }
        else
        {
            entity = EntityAI.Cast(player.GetInventory().CreateInInventory(itemConfig.ClassName));
        }

        if (!entity && m_Config.SpawnOverflowOnGround)
        {
            vector pos = player.GetPosition();
            entity = EntityAI.Cast(GetGame().CreateObjectEx(itemConfig.ClassName, pos, ECE_PLACE_ON_SURFACE));
        }

        if (!entity)
        {
            Print("[DayZKitsPoints] Failed to spawn item: " + itemConfig.ClassName);
            return null;
        }

        ApplyItemValues(entity, itemConfig);

        if (itemConfig.ItemAttachments)
        {
            for (int i = 0; i < itemConfig.ItemAttachments.Count(); i++)
            {
                SpawnConfiguredItem(player, itemConfig.ItemAttachments.Get(i), entity);
            }
        }

        return entity;
    }

    protected void ApplyItemValues(EntityAI entity, NDZKS_Item itemConfig)
    {
        if (!entity || !itemConfig) return;

        if (itemConfig.Health01 >= 0.0)
        {
            entity.SetHealth01("", "", itemConfig.Health01);
        }

        Magazine mag = Magazine.Cast(entity);
        if (mag && itemConfig.AmmoCount >= 0)
        {
            mag.ServerSetAmmoCount(itemConfig.AmmoCount);
            return;
        }

        ItemBase itemBase = ItemBase.Cast(entity);
        if (itemBase && itemConfig.Quantity >= 0)
        {
            itemBase.SetQuantity(itemConfig.Quantity);
        }
    }

    protected void SendMessage(PlayerBase player, string text)
    {
        if (!player || !player.GetIdentity()) return;

        Param1<string> msg = new Param1<string>(m_Config.ChatTag + " " + text);
        GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, player.GetIdentity());
    }

    protected PlayerBase FindOnlinePlayerById(string steam64)
    {
        array<Man> players = new array<Man>;
        GetGame().GetPlayers(players);

        for (int i = 0; i < players.Count(); i++)
        {
            PlayerBase player = PlayerBase.Cast(players.Get(i));
            if (!player || !player.GetIdentity()) continue;

            if (GetPlayerId(player) == steam64)
            {
                return player;
            }
        }

        return null;
    }

    void ProcessDiscordQueue()
    {
        if (!m_Config) LoadConfig();
        if (!m_Config || !m_Config.DiscordBridgeEnabled) return;

        CreateEmptyDiscordFilesIfMissing();

        NDZKS_DiscordQueue queue = new NDZKS_DiscordQueue;
        JsonFileLoader<NDZKS_DiscordQueue>.JsonLoadFile(DISCORD_QUEUE_PATH, queue);

        if (!queue || !queue.Requests || queue.Requests.Count() == 0) return;

        NDZKS_DiscordQueue remaining = new NDZKS_DiscordQueue;

        for (int i = 0; i < queue.Requests.Count(); i++)
        {
            NDZKS_DiscordRequest request = queue.Requests.Get(i);
            if (!request) continue;

            string status = request.Status;
            status.ToLower();

            if (status != "pending")
            {
                continue;
            }

            NDZKS_DiscordResponse response = new NDZKS_DiscordResponse;
            response.RequestId = request.RequestId;
            response.DiscordUserId = request.DiscordUserId;
            response.DiscordUserName = request.DiscordUserName;
            response.Steam64 = request.Steam64;
            response.KitName = request.KitName;
            response.ProcessedUTC = NDZKS_Time.GetNowUTC();

            if (request.Steam64 == "")
            {
                response.Success = false;
                response.Status = "missing_steam64";
                response.Message = "No Steam64 ID was sent with this Discord kit request.";
                AppendDiscordResponse(response);
                continue;
            }

            PlayerBase player = FindOnlinePlayerById(request.Steam64);
            if (!player)
            {
                response.Success = false;
                response.Status = "offline";
                response.Message = "You are not online on this server. Join the server first, then redeem the kit again from Discord.";
                AppendDiscordResponse(response);
                continue;
            }

            NDZKS_ClaimResult claim = ClaimKitInternal(player, request.KitName, m_Config.DiscordSendInGameMessage, "discord", request.DiscordUserName);
            response.Success = claim.Success;
            response.Status = claim.Status;
            response.Message = claim.Message;
            AppendDiscordResponse(response);
        }

        JsonFileLoader<NDZKS_DiscordQueue>.JsonSaveFile(DISCORD_QUEUE_PATH, remaining);
    }

    protected void AppendDiscordResponse(NDZKS_DiscordResponse response)
    {
        if (!response) return;

        NDZKS_DiscordResponseFile responseFile = new NDZKS_DiscordResponseFile;
        if (FileExist(DISCORD_RESPONSES_PATH))
        {
            JsonFileLoader<NDZKS_DiscordResponseFile>.JsonLoadFile(DISCORD_RESPONSES_PATH, responseFile);
        }

        if (!responseFile)
        {
            responseFile = new NDZKS_DiscordResponseFile;
        }

        if (!responseFile.Responses)
        {
            responseFile.Responses = new array<ref NDZKS_DiscordResponse>;
        }

        responseFile.Responses.Insert(response);

        int limit = 250;
        if (m_Config && m_Config.DiscordResponseHistoryLimit > 0) limit = m_Config.DiscordResponseHistoryLimit;

        while (responseFile.Responses.Count() > limit)
        {
            responseFile.Responses.Remove(0);
        }

        JsonFileLoader<NDZKS_DiscordResponseFile>.JsonSaveFile(DISCORD_RESPONSES_PATH, responseFile);
    }
}
