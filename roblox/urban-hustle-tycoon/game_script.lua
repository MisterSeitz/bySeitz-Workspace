-- game_script.lua
--[[
    Urban Hustle Tycoon - Core Game Script
    Developed by Google AI Studio
    
    This script manages the core gameplay loop for "Urban Hustle Tycoon,"
    including player data (cash, owned businesses), a basic click-to-earn
    hustle system, a business purchase and passive income system, and a
    global leaderboard.
    
    Features:
    -   DataStore for saving/loading player cash and owned businesses.
    -   Leaderstats for displaying player's cash.
    -   Basic "Hustle Spot" mini-game (click to earn cash with cooldown).
    -   Shop system for buying businesses (e.g., Food Cart, Small Shop).
    -   Passive income generation from owned businesses.
    -   Global leaderboard for "Richest Player."
    -   Simple day/night cycle.
    
    How it works:
    1.  When a player joins, their data is loaded. If new, default data is created.
    2.  Leaderstats are created for the player to display their cash.
    3.  A "Hustle Spot" (a Part with a ClickDetector) allows players to earn initial cash.
    4.  Players can buy businesses through a GUI. Upon purchase, a model appears on a designated plot,
        and the player starts earning passive income from it.
    5.  Player data is saved when they leave the game.
    6.  A "Richest Player" leaderboard updates periodically.
    7.  The game world experiences a basic day/night cycle.
]]

-- SERVICES --
local Players = game:GetService("Players")
local DataStoreService = game:GetService("DataStoreService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage = game:GetService("ServerStorage")
local Workspace = game:GetService("Workspace")
local Lighting = game:GetService("Lighting")
local RunService = game:GetService("RunService")

-- DATASTORE --
local playerDataStore = DataStoreService:GetDataStore("UrbanHustleTycoonData_V1")

-- CONFIGURATION --
-- Default player data for new players
local DEFAULT_PLAYER_DATA = {
    Cash = 0,
    OwnedBusinesses = {}, -- Table to store names of owned businesses
}

-- Hustle Spot configuration
local HUSTLE_SPOT_NAME = "HustleSpot"
local HUSTLE_REWARD = 10
local HUSTLE_COOLDOWN = 3 -- seconds

-- Business configurations
-- Each business has a name, cost, passive income per second, and the name of its model in ServerStorage
local BUSINESSES = {
    ["Food Cart"] = {
        Cost = 100,
        IncomePerSecond = 1,
        ModelName = "FoodCartModel",
        PlotName = "Plot1" -- The name of the part in Workspace where this business will appear
    },
    ["Small Shop"] = {
        Cost = 500,
        IncomePerSecond = 5,
        ModelName = "SmallShopModel",
        PlotName = "Plot2"
    },
    ["Laundromat"] = {
        Cost = 2000,
        IncomePerSecond = 20,
        ModelName = "LaundromatModel",
        PlotName = "Plot3"
    }
    -- Add more businesses here following the same structure
}

-- Leaderboard configuration
local LEADERBOARD_UPDATE_INTERVAL = 30 -- seconds
local RICHEST_PLAYER_LEADERBOARD_NAME = "RichestPlayer"

-- Day/Night cycle configuration
local DAY_NIGHT_CYCLE_SPEED = 0.05 -- How fast the clock time changes (e.g., 0.05 makes a full cycle in about 8 minutes)

-- REMOTE EVENTS --
-- Ensure these RemoteEvents exist in ReplicatedStorage and are named correctly.
local purchaseBusinessEvent = ReplicatedStorage:WaitForChild("PurchaseBusiness")
local performHustleEvent = ReplicatedStorage:WaitForChild("PerformHustle") -- For the client to tell the server a hustle was performed

-- TABLES FOR PLAYER DATA AND COOLDOWNS --
local playersData = {} -- Stores loaded player data in memory
local hustleCooldowns = {} -- Stores the last time a player performed a hustle

-- HELPER FUNCTIONS --

--- Safely gets a player's data from the in-memory table.
-- @param player The player instance.
-- @return The player's data table.
local function getPlayerData(player)
    return playersData[player.UserId]
end

--- Adds cash to a player's balance.
-- @param player The player instance.
-- @param amount The amount of cash to add.
local function addCash(player, amount)
    local data = getPlayerData(player)
    if data then
        data.Cash = data.Cash + amount
        -- Update leaderstat
        local leaderstats = player:FindFirstChild("leaderstats")
        if leaderstats and leaderstats:FindFirstChild("Cash") then
            leaderstats.Cash.Value = data.Cash
        end
    end
end

--- Removes cash from a player's balance.
-- @param player The player instance.
-- @param amount The amount of cash to remove.
-- @return boolean True if cash was successfully removed, false otherwise (e.g., not enough cash).
local function removeCash(player, amount)
    local data = getPlayerData(player)
    if data and data.Cash >= amount then
        data.Cash = data.Cash - amount
        -- Update leaderstat
        local leaderstats = player:FindFirstChild("leaderstats")
        if leaderstats and leaderstats:FindFirstChild("Cash") then
            leaderstats.Cash.Value = data.Cash
        end
        return true
    end
    return false
end

--- Checks if a player owns a specific business.
-- @param player The player instance.
-- @param businessName The name of the business to check.
-- @return boolean True if the player owns the business, false otherwise.
local function ownsBusiness(player, businessName)
    local data = getPlayerData(player)
    if data then
        for _, ownedBiz in pairs(data.OwnedBusinesses) do
            if ownedBiz == businessName then
                return true
            end
        end
    end
    return false
end

--- Grants a player ownership of a business.
-- @param player The player instance.
-- @param businessName The name of the business to grant.
local function grantBusiness(player, businessName)
    local data = getPlayerData(player)
    if data then
        table.insert(data.OwnedBusinesses, businessName)
    end
end

--- Spawns a business model onto its designated plot.
-- The model is cloned from ServerStorage and parented to the plot in Workspace.
-- @param player The player who owns the business.
-- @param businessConfig The configuration table for the business.
local function spawnBusinessModel(player, businessConfig)
    local plot = Workspace:FindFirstChild(businessConfig.PlotName)
    local businessModel = ServerStorage:FindFirstChild(businessConfig.ModelName)

    if plot and businessModel then
        -- Check if a model for this business and player already exists on the plot
        local existingModelName = businessConfig.ModelName .. "_" .. player.UserId
        if plot:FindFirstChild(existingModelName) then
            -- Model already exists, no need to spawn again (e.g., on player rejoin)
            return
        end

        local clonedModel = businessModel:Clone()
        clonedModel.Name = existingModelName -- Unique name for the instance
        clonedModel.Parent = plot
        clonedModel:SetPrimaryPartCFrame(plot.CFrame) -- Position the model at the plot
        
        -- Optionally, make the plot invisible or change its material once a business is built
        plot.Transparency = 1
        plot.CanCollide = false
    else
        warn("Failed to spawn business model:", businessConfig.ModelName, "on plot:", businessConfig.PlotName, ". Check if plot or model exists.")
    end
end

-- CORE GAME LOGIC --

--- Handles player joining the game.
-- Loads player data or creates new data, sets up leaderstats, and spawns owned businesses.
-- @param player The player instance.
local function onPlayerAdded(player)
    print("Player joined:", player.Name)

    -- Initialize data for player
    local data = DEFAULT_PLAYER_DATA
    local success, loadedData = pcall(function()
        return playerDataStore:GetAsync(player.UserId)
    end)

    if success and loadedData then
        data = loadedData
        print("Loaded data for", player.Name)
    else
        warn("Failed to load data for", player.Name, ":", loadedData, ". Creating new data.")
        -- Ensure new players always have a fresh copy of DEFAULT_PLAYER_DATA
        data = table.clone(DEFAULT_PLAYER_DATA) 
    end

    playersData[player.UserId] = data

    -- Create leaderstats
    local leaderstats = Instance.new("Folder")
    leaderstats.Name = "leaderstats"
    leaderstats.Parent = player

    local cash = Instance.new("IntValue")
    cash.Name = "Cash"
    cash.Value = data.Cash
    cash.Parent = leaderstats

    -- Spawn already owned businesses for the player
    for _, businessName in pairs(data.OwnedBusinesses) do
        local config = BUSINESSES[businessName]
        if config then
            spawnBusinessModel(player, config)
        end
    end
end

--- Handles player leaving the game.
-- Saves player data.
-- @param player The player instance.
local function onPlayerRemoving(player)
    print("Player leaving:", player.Name)

    local data = getPlayerData(player)
    if data then
        local success, err = pcall(function()
            playerDataStore:SetAsync(player.UserId, data)
        end)

        if success then
            print("Saved data for", player.Name)
        else
            warn("Failed to save data for", player.Name, ":", err)
        end
    end

    -- Clean up in-memory data
    playersData[player.UserId] = nil
    hustleCooldowns[player.UserId] = nil
end

--- Handles a player performing a hustle (e.g., clicking the HustleSpot).
-- @param player The player instance who performed the hustle.
local function onPerformHustle(player)
    local currentTime = os.time()
    local lastHustleTime = hustleCooldowns[player.UserId] or 0

    if currentTime - lastHustleTime >= HUSTLE_COOLDOWN then
        addCash(player, HUSTLE_REWARD)
        hustleCooldowns[player.UserId] = currentTime
        print(player.Name, "hustled for", HUSTLE_REWARD, "cash!")
    else
        -- Optionally, send a message to the client about cooldown
        -- For this basic script, we'll just print to console.
        print(player.Name, "is on hustle cooldown.")
    end
end

--- Handles a player attempting to purchase a business.
-- @param player The player instance attempting the purchase.
-- @param businessName The name of the business to purchase.
local function onPurchaseBusiness(player, businessName)
    local businessConfig = BUSINESSES[businessName]
    local data = getPlayerData(player)

    if not businessConfig then
        warn(player.Name, "attempted to buy unknown business:", businessName)
        return
    end

    if ownsBusiness(player, businessName) then
        -- Player already owns this business
        print(player.Name, "already owns", businessName)
        -- Optionally, send feedback to client (e.g., "You already own this!")
        return
    end

    if data.Cash >= businessConfig.Cost then
        if removeCash(player, businessConfig.Cost) then
            grantBusiness(player, businessName)
            spawnBusinessModel(player, businessConfig)
            print(player.Name, "successfully bought", businessName, "for", businessConfig.Cost, "cash!")
            -- Optionally, send success feedback to client
        else
            warn("Error removing cash for", player.Name, "for business:", businessName, ". This should not happen if cash check passed.")
        end
    else
        -- Not enough cash
        print(player.Name, "does not have enough cash to buy", businessName, ". Needs:", businessConfig.Cost, ", Has:", data.Cash)
        -- Optionally, send feedback to client (e.g., "Not enough cash!")
    end
end

-- PASSIVE INCOME LOOP --
-- This loop runs constantly and gives passive income to players with businesses.
local function startPassiveIncomeLoop()
    while RunService.Heartbeat:Wait() do
        for _, player in ipairs(Players:GetPlayers()) do
            local data = getPlayerData(player)
            if data then
                local totalPassiveIncome = 0
                for _, ownedBizName in pairs(data.OwnedBusinesses) do
                    local businessConfig = BUSINESSES[ownedBizName]
                    if businessConfig then
                        totalPassiveIncome = totalPassiveIncome + businessConfig.IncomePerSecond
                    end
                end
                if totalPassiveIncome > 0 then
                    addCash(player, totalPassiveIncome)
                end
            end
        end
        task.wait(1) -- Give passive income every second
    end
end

-- LEADERBOARD SYSTEM --

-- Create the leaderboard folder and values in Workspace for client visibility.
local function setupLeaderboard()
    local leaderboardFolder = Workspace:FindFirstChild("Leaderboards") 
    if not leaderboardFolder then
        leaderboardFolder = Instance.new("Folder")
        leaderboardFolder.Name = "Leaderboards"
        leaderboardFolder.Parent = Workspace -- Placed in Workspace for client scripts to easily read.
    end

    local richestPlayerValue = leaderboardFolder:FindFirstChild(RICHEST_PLAYER_LEADERBOARD_NAME)
    if not richestPlayerValue then
        richestPlayerValue = Instance.new("IntValue")
        richestPlayerValue.Name = RICHEST_PLAYER_LEADERBOARD_NAME
        richestPlayerValue.Value = 0
        richestPlayerValue.Parent = leaderboardFolder
    end
    
    -- An optional StringValue to store the richest player's name for display.
    local richestPlayerNameValue = leaderboardFolder:FindFirstChild(RICHEST_PLAYER_LEADERBOARD_NAME .. "Name")
    if not richestPlayerNameValue then
        richestPlayerNameValue = Instance.new("StringValue")
        richestPlayerNameValue.Name = RICHEST_PLAYER_LEADERBOARD_NAME .. "Name"
        richestPlayerNameValue.Value = "N/A"
        richestPlayerNameValue.Parent = leaderboardFolder
    end
end

-- Updates the "Richest Player" leaderboard values.
local function updateLeaderboard()
    local leaderboardFolder = Workspace:FindFirstChild("Leaderboards")
    if not leaderboardFolder then return end

    local richestPlayerValue = leaderboardFolder:FindFirstChild(RICHEST_PLAYER_LEADERBOARD_NAME)
    local richestPlayerNameValue = leaderboardFolder:FindFirstChild(RICHEST_PLAYER_LEADERBOARD_NAME .. "Name")
    
    if not richestPlayerValue or not richestPlayerNameValue then return end

    local highestCash = 0
    local richestPlayerName = "N/A"

    for _, player in ipairs(Players:GetPlayers()) do
        local data = getPlayerData(player)
        if data and data.Cash > highestCash then
            highestCash = data.Cash
            richestPlayerName = player.Name
        end
    end
    
    richestPlayerValue.Value = highestCash
    richestPlayerNameValue.Value = richestPlayerName
    print("Leaderboard updated: Richest Player - ", richestPlayerName, " with ", highestCash, " cash.")
end

-- Day/Night Cycle --
-- Continuously adjusts the game's lighting ClockTime to simulate a day/night cycle.
local function startDayNightCycle()
    local currentClockTime = Lighting.ClockTime
    while true do
        currentClockTime = (currentClockTime + DAY_NIGHT_CYCLE_SPEED) % 24 -- Loop from 0 to 24 (full day)
        Lighting.ClockTime = currentClockTime
        task.wait(0.1) -- Update frequently for smooth transition
    end
end

-- CONNECTIONS --
Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(onPlayerRemoving)

purchaseBusinessEvent.OnServerEvent:Connect(onPurchaseBusiness)
performHustleEvent.OnServerEvent:Connect(onPerformHustle)

-- INITIAL SETUP & START LOOPS --
setupLeaderboard()

-- Initial setup for any players already in the game (e.g., if the script reloads in Studio).
for _, player in ipairs(Players:GetPlayers()) do
    onPlayerAdded(player)
end

-- Start game loops in separate threads to run concurrently.
task.spawn(startPassiveIncomeLoop)
task.spawn(startDayNightCycle)

-- Leaderboard update loop
task.spawn(function()
    while true do
        updateLeaderboard()
        task.wait(LEADERBOARD_UPDATE_INTERVAL)
    end
end)

print("Urban Hustle Tycoon - Server Script Initialized!")