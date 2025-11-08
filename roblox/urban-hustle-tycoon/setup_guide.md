# Urban Hustle Tycoon - Setup Guide

Welcome to Urban Hustle Tycoon! This guide will walk you through setting up the basic game in Roblox Studio. You'll create the necessary game objects, user interface, and place the provided Lua scripts.

## Prerequisites

*   Roblox Studio installed on your computer.
*   A basic understanding of Roblox Studio's interface (Explorer, Properties windows).

## Step 1: Open Roblox Studio & Create a New Project

1.  Open **Roblox Studio**.
2.  Select **New** from the top menu.
3.  Choose the **Baseplate** template to start with a blank canvas.

## Step 2: Basic World Setup

We need to create some essential parts in your game world.

1.  **Delete the default Baseplate** (optional, but good for custom maps): In the `Explorer` window, find `Workspace > Baseplate`, right-click it, and select `Delete`.
2.  **Add a SpawnLocation:**
    *   In the `Home` tab, click on `Part` and select `SpawnLocation`.
    *   Position it somewhere visible. This is where players will appear.
3.  **Create the "Hustle Spot" Part:**
    *   Click `Part` in the `Home` tab and insert a `Block`.
    *   In the `Explorer` window, rename this `Part` to `HustleSpot`.
    *   In the `Properties` window, set:
        *   `Anchored`: `True`
        *   `CanCollide`: `True`
        *   `Color`: Choose a vibrant color (e.g., Bright green).
        *   `Size`: `5, 1, 5` (or any size you prefer).
    *   **Add a ClickDetector:** Right-click `HustleSpot` in `Explorer`, hover over `Insert Object`, and search for `ClickDetector`. Insert it.
4.  **Create Business Plots (Parts):**
    *   Insert three more `Block` parts into `Workspace`.
    *   Rename them `Plot1`, `Plot2`, and `Plot3` respectively.
    *   For each plot, set:
        *   `Anchored`: `True`
        *   `CanCollide`: `True`
        *   `Transparency`: `0.5` (so they look like empty plots).
        *   `Color`: A neutral color like gray or light blue.
        *   Position them spaced out from each other and the `HustleSpot`.
5.  **Create Business Models in ServerStorage:**
    *   In the `Explorer` window, right-click `ServerStorage`, hover over `Insert Object`, and insert a `Folder`. Rename it `BusinessModels`.
    *   Inside `BusinessModels`, create three simple `Part` objects (e.g., `Block`s).
        *   Rename them: `FoodCartModel`, `SmallShopModel`, `LaundromatModel`.
        *   These will be cloned and placed on the plots when a player buys a business. You can make them more complex models later.
        *   Set `Anchored` to `True` for these models as well.
        *   `FoodCartModel`: A simple block, maybe `4, 6, 3` in size, light yellow color.
        *   `SmallShopModel`: A larger block, maybe `8, 10, 8` in size, light blue color.
        *   `LaundromatModel`: A block, maybe `12, 12, 10` in size, light purple color.

## Step 3: UI Setup (Client-Side)

We need a basic UI for players to interact with the game.

1.  **Create Main ScreenGui:**
    *   In `Explorer`, right-click `StarterGui`, hover over `Insert Object`, and insert a `ScreenGui`.
    *   Rename it `MainScreenGui`.
2.  **Add Shop Button:**
    *   Right-click `MainScreenGui`, hover over `Insert Object`, and insert a `TextButton`.
    *   Rename it `ShopButton`.
    *   In `Properties`, set:
        *   `Text`: `Shop`
        *   `Size`: `{0.1, 0}, {0.05, 0}` (example, position it top-right or bottom-left).
        *   `Position`: `{0.8, 0}, {0.05, 0}` (example).
3.  **Add Shop Frame:**
    *   Right-click `MainScreenGui`, hover over `Insert Object`, and insert a `Frame`.
    *   Rename it `ShopFrame`.
    *   In `Properties`, set:
        *   `Visible`: `False` (it will be toggled by the `ShopButton`).
        *   `Size`: `{0.4, 0}, {0.6, 0}` (example, center it).
        *   `Position`: `{0.3, 0}, {0.2, 0}` (example).
        *   `BackgroundColor3`: A light color.
4.  **Add Close Button to Shop Frame:**
    *   Right-click `ShopFrame`, hover over `Insert Object`, and insert a `TextButton`.
    *   Rename it `CloseButton`.
    *   In `Properties`, set:
        *   `Text`: `X`
        *   `Size`: `{0.1, 0}, {0.05, 0}` (top-right corner of the frame).
        *   `Position`: `{0.9, 0}, {0, 0}` (example).
5.  **Add Business Buttons to Shop Frame:**
    *   Right-click `ShopFrame`, hover over `Insert Object`, and insert three `TextButton`s.
    *   Rename them: `FoodCartButton`, `SmallShopButton`, `LaundromatButton`.
    *   For each button, set:
        *   `Text`: `Buy Food Cart ($100)`, `Buy Small Shop ($500)`, `Buy Laundromat ($2000)` respectively.
        *   `Size`: `{0.8, 0}, {0.1, 0}`.
        *   Arrange them vertically within the `ShopFrame` using `Position` (e.g., `Y` values of `0.2`, `0.4`, `0.6`).
6.  **Add Leaderboard Display (Optional but Recommended):**
    *   Right-click `MainScreenGui`, hover over `Insert Object`, and insert a `TextLabel`.
    *   Rename it `LeaderboardDisplay`.
    *   In `Properties`, set:
        *   `Text`: `Richest Player: N/A (0 Cash)`
        *   `Size`: `{0.3, 0}, {0.05, 0}` (example, position it top-center).
        *   `Position`: `{0.35, 0}, {0, 0}`.
        *   `BackgroundColor3`: A semi-transparent color.
        *   `TextScaled`: `True`.
        *   `TextXAlignment`: `Center`.

7.  **Create Client-Side UI Handler Script:**
    *   In `Explorer`, find `StarterPlayer > StarterPlayerScripts`.
    *   Right-click `StarterPlayerScripts`, hover over `Insert Object`, and insert a `LocalScript`.
    *   Rename it `Client_UI_Handler`.
    *   **Paste the following code into the `Client_UI_Handler` script:**

    ```lua
    -- Client_UI_Handler.lua
    -- This local script handles all client-side UI interactions and communicates with the server.

    -- SERVICES --
    local Players = game:GetService("Players")
    local ReplicatedStorage = game:GetService("ReplicatedStorage")
    local Workspace = game:GetService("Workspace")

    -- PLAYER --
    local player = Players.LocalPlayer
    local playerGui = player:WaitForChild("PlayerGui")

    -- REMOTE EVENTS --
    -- Ensure these RemoteEvents exist in ReplicatedStorage
    local purchaseBusinessEvent = ReplicatedStorage:WaitForChild("PurchaseBusiness")
    local performHustleEvent = ReplicatedStorage:WaitForChild("PerformHustle")

    -- UI ELEMENTS --
    -- Make sure these UI elements are set up exactly as described in the setup guide.
    local mainScreenGui = playerGui:WaitForChild("MainScreenGui")
    local shopButton = mainScreenGui:WaitForChild("ShopButton")
    local shopFrame = mainScreenGui:WaitForChild("ShopFrame")
    local closeShopButton = shopFrame:WaitForChild("CloseButton")

    -- Business Buttons inside the ShopFrame
    local foodCartButton = shopFrame:WaitForChild("FoodCartButton")
    local smallShopButton = shopFrame:WaitForChild("SmallShopButton")
    local laundromatButton = shopFrame:WaitForChild("LaundromatButton")

    -- Hustle Spot Part (the clickable object in the world)
    local hustleSpotPart = Workspace:WaitForChild("HustleSpot")
    local hustleClickDetector = hustleSpotPart:FindFirstChildOfClass("ClickDetector")

    -- Leaderboard Display (Conceptual - you'll need a TextLabel for this)
    local leaderboardDisplay = mainScreenGui:FindFirstChild("LeaderboardDisplay") -- A TextLabel or similar

    -- FUNCTIONS --

    --- Toggles the visibility of the shop UI frame.
    shopButton.MouseButton1Click:Connect(function()
        shopFrame.Visible = not shopFrame.Visible
    end)

    --- Closes the shop UI frame.
    closeShopButton.MouseButton1Click:Connect(function()
        shopFrame.Visible = false
    end)

    --- Fires a RemoteEvent to the server to request a business purchase.
    -- @param businessName The name of the business to purchase (e.g., "Food Cart").
    local function onPurchaseButtonClicked(businessName)
        purchaseBusinessEvent:FireServer(businessName)
        print("Client: Attempting to buy:", businessName)
        -- You might want to add client-side feedback here (e.g., "Buying...")
    end

    -- Connect business buttons to the purchase function
    foodCartButton.MouseButton1Click:Connect(function()
        onPurchaseButtonClicked("Food Cart")
    end)

    smallShopButton.MouseButton1Click:Connect(function()
        onPurchaseButtonClicked("Small Shop")
    end)

    laundromatButton.MouseButton1Click:Connect(function()
        onPurchaseButtonClicked("Laundromat")
    end)

    -- Connect the Hustle Spot's ClickDetector to fire the performHustleEvent
    if hustleClickDetector then
        hustleClickDetector.MouseClick:Connect(function()
            performHustleEvent:FireServer()
            print("Client: Performed a hustle!")
            -- You can add client-side visual feedback here (e.g., temporary text, animation)
        end)
    else
        warn("Client_UI_Handler: HustleSpot or its ClickDetector not found! Make sure 'HustleSpot' exists in Workspace with a ClickDetector.")
    end

    -- Leaderboard Display Update (Optional, requires a TextLabel named "LeaderboardDisplay")
    -- This part assumes the server script places the leaderboard in Workspace.
    if leaderboardDisplay and Workspace:FindFirstChild("Leaderboards") then
        local leaderboardFolder = Workspace.Leaderboards
        local richestPlayerValue = leaderboardFolder:WaitForChild("RichestPlayer")
        local richestPlayerNameValue = leaderboardFolder:WaitForChild("RichestPlayerName")

        local function updateLeaderboardText()
            leaderboardDisplay.Text = "Richest Player: " .. richestPlayerNameValue.Value .. " (" .. richestPlayerValue.Value .. " Cash)"
        end

        -- Update initially
        updateLeaderboardText()

        -- Update whenever the values change
        richestPlayerValue.Changed:Connect(updateLeaderboardText)
        richestPlayerNameValue.Changed:Connect(updateLeaderboardText)
    end

    print("Client_UI_Handler: Script Initialized!")

    ```

## Step 4: RemoteEvents Setup

RemoteEvents are crucial for communication between the client (UI) and the server (game logic).

1.  **Create RemoteEvents:**
    *   In the `Explorer` window, right-click `ReplicatedStorage`, hover over `Insert Object`, and insert a `RemoteEvent`.
    *   Rename it `PurchaseBusiness`.
    *   Repeat the process to create another `RemoteEvent` named `PerformHustle`.

## Step 5: Server Script Setup

This is the core logic of your game.

1.  **Create Server Script:**
    *   In the `Explorer` window, right-click `ServerScriptService`, hover over `Insert Object`, and insert a `Script`.
    *   Rename it `UrbanHustleTycoon_ServerScript`.
    *   **Paste the complete Lua script provided previously into this script.** (The `luaScript` content from the JSON output).

## Step 6: Test the Game

1.  In Roblox Studio, click the **Play** button (or `F5`) to start a test session.
2.  **Check Leaderstats:** You should see a `Cash` leaderboard on the right side of your screen (default Roblox UI).
3.  **Perform a Hustle:** Walk up to the `HustleSpot` part and click it. You should see your cash increase in the leaderstats and a message in the `Output` window.
4.  **Open the Shop:** Click the `Shop` button on your screen. The `ShopFrame` should appear.
5.  **Buy a Business:** Click one of the "Buy" buttons (e.g., `Buy Food Cart`). If you have enough cash, the business model should appear on its designated `Plot` part, and your cash should decrease.
6.  **Observe Passive Income:** After buying a business, wait a few seconds. You should see your cash slowly increase due to passive income from your business.
7.  **Check Leaderboard Display:** If you set up the `LeaderboardDisplay` `TextLabel`, it should show the richest player's cash (which will be your own if you're the only one playing).
8.  Stop the game (Shift + F5 or Stop button). Your progress (cash and owned businesses) should be saved and loaded the next time you play.

## Step 7: Customization & Expansion

*   **Add More Businesses:** Expand the `BUSINESSES` table in the server script and create corresponding `Plot` parts and `Model`s in `ServerStorage`.
*   **Improve Models:** Replace the simple `Part` models in `ServerStorage/BusinessModels` with more detailed 3D models.
*   **Adjust Values:** Experiment with `HUSTLE_REWARD`, `HUSTLE_COOLDOWN`, `Cost`, and `IncomePerSecond` values to balance your game.
*   **Enhance UI:** Improve the look and feel of your `ScreenGui` elements.
*   **NPCs:** For more advanced development, implement AI NPCs that walk around and interact with player businesses.

Congratulations! You've set up the basic framework for Urban Hustle Tycoon. Now you can expand and customize it to make it your own!