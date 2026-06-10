modded class MissionServer
{
    override void OnInit()
    {
        super.OnInit();
        GetNDZKSManager();
        Print("[DayZKitsPoints] Loaded.");
    }

    override void OnEvent(EventType eventTypeId, Param params)
    {
        super.OnEvent(eventTypeId, params);

        if (eventTypeId != ChatMessageEventTypeID) return;

        ChatMessageEventParams chatParams = ChatMessageEventParams.Cast(params);
        if (!chatParams) return;

        string senderName = chatParams.param2;
        string message = chatParams.param3;

        if (message == "") return;

        PlayerBase player = FindPlayerByName(senderName);
        if (!player) return;

        GetNDZKSManager().HandleChatCommand(player, message);
    }

    protected PlayerBase FindPlayerByName(string playerName)
    {
        array<Man> players = new array<Man>;
        GetGame().GetPlayers(players);

        for (int i = 0; i < players.Count(); i++)
        {
            PlayerBase player = PlayerBase.Cast(players.Get(i));
            if (!player || !player.GetIdentity()) continue;

            if (player.GetIdentity().GetName() == playerName)
            {
                return player;
            }
        }

        return null;
    }
}
