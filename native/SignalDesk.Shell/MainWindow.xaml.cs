using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using SignalDesk.Shell.Services;
using SignalDesk.Shell.Views;
using WinRT.Interop;

namespace SignalDesk.Shell;

public sealed partial class MainWindow : Window
{
    private readonly AppState _state;
    private readonly DispatcherTimer _searchTimer = new() { Interval = TimeSpan.FromMilliseconds(280) };
    private AppWindow? _appWindow;
    private bool _settingsReady;
    private bool _focusUpdateInProgress;
    private bool _allowClose;

    public MainWindow(AppState state)
    {
        _state = state;
        InitializeComponent();
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(TitleBarDragRegion);
        SystemBackdrop = new MicaBackdrop();
        ConfigureWindow();
        ApplyTheme();
        _searchTimer.Tick += SearchTimer_Tick;
        _state.Refreshed += State_Refreshed;
        _state.ReminderDue += State_ReminderDue;
        _state.DigestReady += State_DigestReady;
        Activated += MainWindow_Activated;
        RootNavigation.SelectedItem = NowItem;
        UpdateChrome();
    }

    private void ConfigureWindow()
    {
        var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(WindowNative.GetWindowHandle(this));
        _appWindow = AppWindow.GetFromWindowId(windowId);
        var display = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
        var width = Math.Min(1800, Math.Max(1200, display.WorkArea.Width - 80));
        var height = Math.Min(1000, Math.Max(760, display.WorkArea.Height - 80));
        _appWindow.Resize(new Windows.Graphics.SizeInt32(width, height));
        _appWindow.Closing += (_, args) =>
        {
            if (_allowClose) return;
            args.Cancel = true;
            _appWindow.Hide();
        };
    }

    private async void MainWindow_Activated(object sender, WindowActivatedEventArgs args)
    {
        Activated -= MainWindow_Activated;
        _settingsReady = true;
        FocusToggle.IsChecked = _state.Preferences.FocusMode;
        UpdateFocusVisual();
        if (!_state.Preferences.OnboardingComplete) await ShowOnboardingAsync();
    }

    private async void RootNavigation_SelectionChanged(
        NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItemContainer?.Tag is not string tag) return;
        LoadingRing.IsActive = true;
        try
        {
            ContentHost.Content = tag switch
            {
                "digest" => new DigestPage(_state),
                "sources" => new SourcesPage(_state),
                "rules" => new RulesPage(_state),
                "settings" => new SettingsPage(_state),
                _ => new InboxPage(_state, tag)
            };
            if (ContentHost.Content is IAsyncPage page) await page.LoadAsync();
        }
        catch (Exception error) { ShowError(error.Message); }
        finally { LoadingRing.IsActive = false; }
    }

    private void SearchBox_TextChanged(AutoSuggestBox sender, AutoSuggestBoxTextChangedEventArgs args)
    {
        if (args.Reason != AutoSuggestionBoxTextChangeReason.UserInput) return;
        _searchTimer.Stop();
        _searchTimer.Start();
    }

    private async void SearchTimer_Tick(object? sender, object e)
    {
        _searchTimer.Stop();
        if (ContentHost.Content is InboxPage inbox)
            await inbox.SearchAsync(SearchBox.Text);
    }

    private async void FocusToggle_Click(object sender, RoutedEventArgs e)
    {
        if (!_settingsReady || _focusUpdateInProgress) return;
        _focusUpdateInProgress = true;
        FocusToggle.IsEnabled = false;
        var enabled = FocusToggle.IsChecked == true;
        UpdateFocusVisual();
        try
        {
            await _state.UpdateSettingsAsync(new { focus_mode = enabled });
            ShowMessage(
                enabled ? "專注模式已開啟" : "專注模式已關閉",
                enabled
                    ? "一般訊息會安靜留在收件匣；只有高信心的重要事項能即時提醒。"
                    : "SignalDesk 已恢復標準提醒門檻。",
                enabled ? InfoBarSeverity.Informational : InfoBarSeverity.Success);
        }
        catch (Exception error)
        {
            FocusToggle.IsChecked = _state.Preferences.FocusMode;
            UpdateFocusVisual();
            ShowError(error.Message);
        }
        finally
        {
            FocusToggle.IsEnabled = true;
            _focusUpdateInProgress = false;
        }
    }

    private void State_Refreshed(object? sender, EventArgs e) => DispatcherQueue.TryEnqueue(UpdateChrome);

    private void State_ReminderDue(object? sender, System.Text.Json.JsonElement e) =>
        DispatcherQueue.TryEnqueue(() =>
        {
            AppInfoBar.Title = "SignalDesk 提醒";
            AppInfoBar.Message = "有一則訊息需要處理。";
            AppInfoBar.Severity = InfoBarSeverity.Informational;
            AppInfoBar.IsOpen = true;
        });

    private void State_DigestReady(object? sender, System.Text.Json.JsonElement e) =>
        DispatcherQueue.TryEnqueue(() =>
        {
            var kind = e.TryGetProperty("payload", out var payload) &&
                       payload.TryGetProperty("kind", out var value)
                ? value.GetString() : "daily";
            ShowMessage(
                kind == "focus" ? "專注摘要已準備好" : "每日 Digest 已準備好",
                "打開『每日摘要』即可查看目前的重要事項與待回覆訊息。",
                InfoBarSeverity.Informational);
        });

    private void UpdateChrome()
    {
        NowBadge.Value = _state.Counts.Open;
        ReplyBadge.Value = _state.Counts.Reply;
        ServiceStateText.Text = _state.Model.Backend == "rule" ? "本機規則引擎" : "本機 AI 引擎";
        ServiceStateHint.Text = _state.Model.Backend == "rule"
            ? "可檢查 · 不連雲端"
            : $"{_state.Model.Id} · {_state.Model.Quantization.ToUpperInvariant()} · 按需載入";
        if (!_focusUpdateInProgress)
            FocusToggle.IsChecked = _state.Preferences.FocusMode;
        UpdateFocusVisual();
    }

    private void UpdateFocusVisual()
    {
        var enabled = FocusToggle.IsChecked == true;
        FocusLabel.Text = enabled ? "專注中" : "專注模式";
        FocusHint.Text = enabled ? "僅即時提醒重要事項" : "一般提醒正常顯示";
        FocusIcon.Glyph = enabled ? "\uE73D" : "\uE708";
    }

    public void ApplyTheme()
    {
        if (Content is not FrameworkElement root) return;
        root.RequestedTheme = _state.Preferences.Theme switch
        {
            "light" => ElementTheme.Light,
            "dark" => ElementTheme.Dark,
            _ => ElementTheme.Default
        };
    }

    private async Task ShowOnboardingAsync()
    {
        var content = new StackPanel { Spacing = 14, MaxWidth = 520 };
        content.Children.Add(new TextBlock
        {
            Text = "少一點打斷，多一點真正重要的事。",
            FontFamily = new FontFamily("Segoe UI Variable Display"), FontSize = 27,
            FontWeight = Microsoft.UI.Text.FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap
        });
        content.Children.Add(new TextBlock
        {
            Text = "SignalDesk 是原生 Windows 桌面 Agent。Gmail 使用官方 OAuth；個人 LINE 與 Messenger 只讀取 Windows 實際顯示的通知預覽。",
            TextWrapping = TextWrapping.Wrap,
            Foreground = (Brush)Application.Current.Resources["TextFillColorSecondaryBrush"]
        });
        content.Children.Add(new InfoBar
        {
            IsOpen = true, IsClosable = false, Severity = InfoBarSeverity.Success,
            Title = "你永遠保有控制權",
            Message = "系統不會自動傳送、刪除或回覆任何來源訊息。Shadow Mode 預設開啟。"
        });
        content.Children.Add(new TextBlock
        {
            Text = $"分類引擎：{(_state.Model.Backend == "rule" ? "安全規則模式（之後可安裝本機 Qwen）" : _state.Model.Id)}",
            FontWeight = Microsoft.UI.Text.FontWeights.SemiBold,
            TextWrapping = TextWrapping.Wrap
        });
        var allowlist = new TextBox
        {
            Header = "允許讀取通知預覽的 App",
            Text = string.Join(", ", _state.Preferences.NotificationAllowlist),
            Description = "只有這些 App 在 Windows 通知中實際顯示的文字會被處理。"
        };
        content.Children.Add(allowlist);
        var timeGrid = new Grid { ColumnSpacing = 12 };
        timeGrid.ColumnDefinitions.Add(new ColumnDefinition());
        timeGrid.ColumnDefinitions.Add(new ColumnDefinition());
        var quietStart = new TimePicker
        {
            Header = "勿擾開始", ClockIdentifier = "24HourClock",
            Time = TimeSpan.TryParse(_state.Preferences.QuietStart, out var start)
                ? start : new TimeSpan(23, 0, 0)
        };
        var quietEnd = new TimePicker
        {
            Header = "勿擾結束", ClockIdentifier = "24HourClock",
            Time = TimeSpan.TryParse(_state.Preferences.QuietEnd, out var end)
                ? end : new TimeSpan(8, 0, 0)
        };
        Grid.SetColumn(quietEnd, 1);
        timeGrid.Children.Add(quietStart); timeGrid.Children.Add(quietEnd);
        content.Children.Add(timeGrid);
        var shadow = new CheckBox
        {
            Content = "先以 Shadow Mode 安靜觀察 7–14 天（建議）", IsChecked = true
        };
        var connectGmail = new CheckBox
        {
            Content = "完成後前往連接 Gmail（可連接兩個以上帳號）", IsChecked = true
        };
        content.Children.Add(shadow); content.Children.Add(connectGmail);
        content.Children.Add(new TextBlock
        {
            Text = "完成後 Windows 會顯示通知存取權限。若拒絕，Gmail 仍可正常使用，LINE／Messenger 預覽則不會被讀取。",
            FontSize = 11, TextWrapping = TextWrapping.Wrap,
            Foreground = (Brush)Application.Current.Resources["TextFillColorSecondaryBrush"]
        });
        var dialog = new ContentDialog
        {
            XamlRoot = Content.XamlRoot,
            Title = "歡迎使用 SignalDesk",
            Content = content,
            PrimaryButtonText = "開始使用",
            SecondaryButtonText = "載入虛構示範資料",
            DefaultButton = ContentDialogButton.Primary
        };
        var result = await dialog.ShowAsync();
        if (result == ContentDialogResult.Secondary) await _state.Api.SeedDemoAsync();
        await _state.UpdateSettingsAsync(new
        {
            onboarding_complete = true,
            shadow_mode = shadow.IsChecked == true,
            quiet_start = $"{quietStart.Time.Hours:00}:{quietStart.Time.Minutes:00}",
            quiet_end = $"{quietEnd.Time.Hours:00}:{quietEnd.Time.Minutes:00}",
            notification_allowlist = allowlist.Text
                .Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
        });
        await _state.RefreshAsync();
        if (connectGmail.IsChecked == true) RootNavigation.SelectedItem = SourcesItem;
    }

    public void ShowMessage(string title, string message, InfoBarSeverity severity = InfoBarSeverity.Success)
    {
        AppInfoBar.Title = title;
        AppInfoBar.Message = message;
        AppInfoBar.Severity = severity;
        AppInfoBar.IsOpen = true;
    }

    public async Task OpenCardAsync(string cardId)
    {
        RootNavigation.SelectedItem = NowItem;
        var inbox = new InboxPage(_state, "now");
        ContentHost.Content = inbox;
        await inbox.LoadAsync();
        await inbox.SelectCardAsync(cardId);
    }

    private void ShowError(string message) => ShowMessage("操作失敗", message, InfoBarSeverity.Error);

    public void CloseForExit()
    {
        _allowClose = true;
        Close();
    }
}
