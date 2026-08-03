using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SignalDesk.Shell.Services;
using Windows.Storage.Pickers;
using WinRT.Interop;

namespace SignalDesk.Shell;

public partial class App : Application
{
    private MainWindow? _mainWindow;
    private GlanceWindow? _glanceWindow;
    private OrbWindow? _orbWindow;
    private LocalServiceManager? _serviceManager;
    private NotificationBridge? _notificationBridge;
    private TrayIcon? _trayIcon;
    private AppState? _state;

    public App()
    {
        InitializeComponent();
        UnhandledException += (_, args) =>
        {
            System.Diagnostics.Debug.WriteLine(args.Exception);
            args.Handled = true;
        };
    }

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        try
        {
            _serviceManager = new LocalServiceManager();
            var session = await _serviceManager.EnsureRunningAsync();
            var api = new LocalApiClient(session.BaseUri, session.Token);
            _state = new AppState(api);
            await _state.InitializeAsync();

            ShowDashboard();
            _trayIcon = new TrayIcon(_mainWindow!, ShowDashboard, ExitApplication);
            _state.ReminderDue += (_, _) =>
                _trayIcon?.ShowNotification("SignalDesk 提醒", "有一則訊息需要處理。");
            _state.DigestReady += (_, message) =>
            {
                var kind = message.TryGetProperty("payload", out var payload) &&
                           payload.TryGetProperty("kind", out var value)
                    ? value.GetString() : "daily";
                _trayIcon?.ShowNotification(
                    kind == "focus" ? "專注摘要已準備好" : "每日 Digest 已準備好",
                    "點一下 SignalDesk 圖示查看重要事項與待回覆訊息。");
            };

            _orbWindow = new OrbWindow(_state, ShowGlance);
            _orbWindow.Activate();
            ShowDashboard();

            _notificationBridge = new NotificationBridge(api);
            await _notificationBridge.StartAsync();
            _state.StartWatcher();
            await _state.RefreshAsync();
        }
        catch (Exception error)
        {
            System.Diagnostics.Debug.WriteLine(error);
            ShowStartupError(error.Message);
        }
    }

    public async Task<string> RequestNotificationAccessAsync()
    {
        if (_notificationBridge is null || _state is null) return "error";
        var access = await _notificationBridge.StartAsync();
        await _state.RefreshAsync();
        var value = access switch
        {
            Windows.UI.Notifications.Management.UserNotificationListenerAccessStatus.Allowed =>
                "allowed",
            Windows.UI.Notifications.Management.UserNotificationListenerAccessStatus.Denied =>
                "denied",
            _ => "unspecified"
        };
        if (value == "denied")
            await Windows.System.Launcher.LaunchUriAsync(
                new Uri("ms-settings:privacy-notifications"));
        return value;
    }

    private void ShowDashboard()
    {
        if (_state is null) return;
        _mainWindow ??= new MainWindow(_state);
        _mainWindow.Activate();
    }

    private void ShowGlance()
    {
        if (_state is null) return;
        _glanceWindow ??= new GlanceWindow(_state);
        _glanceWindow.ActivateAndRefresh();
    }

    public void ShowMessage(
        string title, string message,
        InfoBarSeverity severity = InfoBarSeverity.Success)
    {
        ShowDashboard();
        _mainWindow?.ShowMessage(title, message, severity);
    }

    public async Task OpenCardAsync(string cardId)
    {
        ShowDashboard();
        if (_mainWindow is not null) await _mainWindow.OpenCardAsync(cardId);
        _glanceWindow?.Hide();
    }

    public void ApplyTheme()
    {
        _mainWindow?.ApplyTheme();
        _glanceWindow?.ApplyTheme();
    }

    public async Task<string?> PickGmailCredentialsAsync()
    {
        ShowDashboard();
        if (_mainWindow is null) return null;

        var picker = new FileOpenPicker
        {
            SuggestedStartLocation = PickerLocationId.Downloads,
            ViewMode = PickerViewMode.List,
            CommitButtonText = "使用這份 OAuth 設定"
        };
        picker.FileTypeFilter.Add(".json");
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(_mainWindow));
        var file = await picker.PickSingleFileAsync();
        return file?.Path;
    }

    public async Task<IReadOnlyList<string>> PickChatArchivesAsync(string source)
    {
        ShowDashboard();
        if (_mainWindow is null) return [];

        var line = source == "line";
        var picker = new FileOpenPicker
        {
            SuggestedStartLocation = PickerLocationId.Downloads,
            ViewMode = PickerViewMode.List,
            CommitButtonText = line ? "匯入 LINE 聊天記錄" : "匯入 Messenger 聊天記錄"
        };
        if (line)
        {
            picker.FileTypeFilter.Add(".txt");
        }
        else
        {
            picker.FileTypeFilter.Add(".zip");
            picker.FileTypeFilter.Add(".json");
        }
        InitializeWithWindow.Initialize(picker, WindowNative.GetWindowHandle(_mainWindow));
        var files = await picker.PickMultipleFilesAsync();
        return files.Select(file => file.Path).Where(path => !string.IsNullOrWhiteSpace(path)).ToList();
    }

    private static void ShowStartupError(string message)
    {
        var window = new Window { Title = "SignalDesk 啟動失敗" };
        window.Content = new Grid
        {
            Padding = new Thickness(32),
            Children =
            {
                new StackPanel
                {
                    Spacing = 12,
                    Children =
                    {
                        new TextBlock { Text = "SignalDesk 無法啟動本機服務", FontSize = 24 },
                        new TextBlock { Text = message, TextWrapping = TextWrapping.Wrap }
                    }
                }
            }
        };
        window.Activate();
    }

    private void ExitApplication()
    {
        _trayIcon?.Dispose();
        _notificationBridge?.Dispose();
        _state?.Dispose();
        _serviceManager?.Dispose();
        _glanceWindow?.CloseForExit();
        _orbWindow?.CloseForExit();
        _mainWindow?.CloseForExit();
    }
}
