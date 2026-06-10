class NDZKS_Item
{
    string ClassName;
    int Quantity;
    int AmmoCount;
    float Health01;
    ref array<ref NDZKS_Item> ItemAttachments;

    void NDZKS_Item()
    {
        ClassName = "";
        Quantity = -1;
        AmmoCount = -1;
        Health01 = -1.0;
        ItemAttachments = new array<ref NDZKS_Item>;
    }
}

class NDZKS_Kit
{
    string Name;
    string DisplayName;
    int CooldownSeconds;
    bool Enabled;
    ref array<ref NDZKS_Item> Items;

    void NDZKS_Kit()
    {
        Name = "";
        DisplayName = "";
        CooldownSeconds = 0;
        Enabled = true;
        Items = new array<ref NDZKS_Item>;
    }
}

class NDZKS_Config
{
    string CommandPrefix;
    bool ShowKitListWhenUsingKitOnly;
    bool SpawnOverflowOnGround;
    bool LogClaimsToServerRPT;
    string ChatTag;

    // Discord bridge settings. The Discord bot writes requests to DiscordQueue.json.
    // The DayZ server polls that file and gives the kit to the linked Steam64 player.
    bool DiscordBridgeEnabled;
    int DiscordPollSeconds;
    bool DiscordSendInGameMessage;
    int DiscordResponseHistoryLimit;

    ref array<ref NDZKS_Kit> Kits;
    ref array<string> AdminSteamIds;

    void NDZKS_Config()
    {
        CommandPrefix = "/kit";
        ShowKitListWhenUsingKitOnly = true;
        SpawnOverflowOnGround = true;
        LogClaimsToServerRPT = true;
        ChatTag = "[Kits]";

        DiscordBridgeEnabled = true;
        DiscordPollSeconds = 10;
        DiscordSendInGameMessage = true;
        DiscordResponseHistoryLimit = 250;

        Kits = new array<ref NDZKS_Kit>;
        AdminSteamIds = new array<string>;
    }
}

class NDZKS_CooldownRecord
{
    string KitName;
    int LastClaimUTC;

    void NDZKS_CooldownRecord()
    {
        KitName = "";
        LastClaimUTC = 0;
    }
}

class NDZKS_PlayerData
{
    string PlayerId;
    string PlayerName;
    ref array<ref NDZKS_CooldownRecord> Cooldowns;

    void NDZKS_PlayerData()
    {
        PlayerId = "";
        PlayerName = "";
        Cooldowns = new array<ref NDZKS_CooldownRecord>;
    }
}

class NDZKS_ClaimResult
{
    bool Success;
    string Status;
    string Message;

    void NDZKS_ClaimResult()
    {
        Success = false;
        Status = "error";
        Message = "Something went wrong.";
    }
}

class NDZKS_DiscordRequest
{
    string RequestId;
    string DiscordUserId;
    string DiscordUserName;
    string Steam64;
    string KitName;
    int CreatedUTC;
    string Status;
    string Message;

    void NDZKS_DiscordRequest()
    {
        RequestId = "";
        DiscordUserId = "";
        DiscordUserName = "";
        Steam64 = "";
        KitName = "";
        CreatedUTC = 0;
        Status = "pending";
        Message = "";
    }
}

class NDZKS_DiscordQueue
{
    ref array<ref NDZKS_DiscordRequest> Requests;

    void NDZKS_DiscordQueue()
    {
        Requests = new array<ref NDZKS_DiscordRequest>;
    }
}

class NDZKS_DiscordResponse
{
    string RequestId;
    string DiscordUserId;
    string DiscordUserName;
    string Steam64;
    string KitName;
    int ProcessedUTC;
    bool Success;
    string Status;
    string Message;

    void NDZKS_DiscordResponse()
    {
        RequestId = "";
        DiscordUserId = "";
        DiscordUserName = "";
        Steam64 = "";
        KitName = "";
        ProcessedUTC = 0;
        Success = false;
        Status = "error";
        Message = "";
    }
}

class NDZKS_DiscordResponseFile
{
    ref array<ref NDZKS_DiscordResponse> Responses;

    void NDZKS_DiscordResponseFile()
    {
        Responses = new array<ref NDZKS_DiscordResponse>;
    }
}
