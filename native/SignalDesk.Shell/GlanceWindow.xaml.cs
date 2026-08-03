using System.Collections.ObjectModel;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using SignalDesk.Shell.Models;
using SignalDesk.Shell.Services;
using WinRT.Interop;

namespace SignalDesk.Shell;

public sealed partial class GlanceWindow : Window
{
    private readonly AppState _state;
    private readonly DispatcherTimer _contentRefreshTimer = new()
    {
        Interval = TimeSpan.FromSeconds(30)
    };
    private readonly DispatcherTimer _relativeTimeTimer = new()
    {
        Interval = TimeSpan.FromMinutes(1)
    };
    private AppWindow? _appWindow;
    private bool _allowClose;
    private bool _refreshing;

    public GlanceWindow(AppState state)
    {
        _state = state;
        InitializeComponent();
        SystemBackdrop = new DesktopAcrylicBackdrop();
        ConfigureWindow();
        ApplyTheme();
        _contentRefreshTimer.Tick += ContentRefreshTimer_Tick;
        _relativeTimeTimer.Tick += RelativeTimeTimer_Tick;
    }

    public ObservableCollection<CardItem> Cards { get; } = [];

    public async void ActivateAndRefresh()
    {
        Activate();
        _contentRefreshTimer.Start();
        _relativeTimeTimer.Start();
        await RefreshCardsAsync(reportError: true);
    }

    private async Task RefreshCardsAsync(bool reportError)
    {
        if (_refreshing) return;
        _refreshing = true;
        try
        {
            var response = await _state.Api.CardsAsync("latest");
            var usefulCards = response.Items
                .Where(IsUsefulGlanceCard)
                .OrderByDescending(item => item.UpdatedAtValue)
                .ToList();
            Cards.Clear();
            foreach (var card in usefulCards.Take(4))
                Cards.Add(card);
            await MediaImageLoader.LoadThumbnailsAsync(_state.Api, Cards, limit: 4);
            EmptyState.Visibility = Cards.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
            var remaining = Math.Max(0, usefulCards.Count - Cards.Count);
            ShowingText.Text = Cards.Count > 0 ? $"最新 {Cards.Count} 則" : "";
            RemainingText.Text = remaining > 0 ? $"另有 {remaining} 則" : "已是全部";
        }
        catch (Exception error)
        {
            if (reportError)
                ((App)Application.Current).ShowMessage(
                    "Glance 更新失敗", error.Message, InfoBarSeverity.Error);
        }
        finally { _refreshing = false; }
    }

    private async void ContentRefreshTimer_Tick(object? sender, object e) =>
        await RefreshCardsAsync(reportError: false);

    private void RelativeTimeTimer_Tick(object? sender, object e)
    {
        foreach (var card in Cards) card.RefreshRelativeTime();
    }

    private void ConfigureWindow()
    {
        var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(WindowNative.GetWindowHandle(this));
        _appWindow = AppWindow.GetFromWindowId(windowId);
        var display = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
        const int preferredWidth = 460;
        const int preferredHeight = 700;
        const int margin = 18;
        var width = Math.Min(preferredWidth, Math.Max(360, display.WorkArea.Width - margin * 2));
        var height = Math.Min(preferredHeight, Math.Max(500, display.WorkArea.Height - margin * 2));
        _appWindow.Resize(new Windows.Graphics.SizeInt32(width, height));
        if (_appWindow.Presenter is OverlappedPresenter presenter)
        {
            presenter.IsAlwaysOnTop = true;
            presenter.IsResizable = false;
            presenter.IsMaximizable = false;
            presenter.IsMinimizable = false;
            presenter.SetBorderAndTitleBar(false, false);
        }
        _appWindow.Move(new Windows.Graphics.PointInt32(
            display.WorkArea.X + display.WorkArea.Width - width - margin,
            display.WorkArea.Y + display.WorkArea.Height - height - margin));
        _appWindow.Closing += (_, args) =>
        {
            if (_allowClose) return;
            args.Cancel = true;
            _appWindow.Hide();
        };
    }

    public void ApplyTheme()
    {
        RootBorder.RequestedTheme = _state.Preferences.Theme switch
        {
            "light" => ElementTheme.Light,
            "dark" => ElementTheme.Dark,
            _ => ElementTheme.Default
        };
    }

    public void Hide()
    {
        _contentRefreshTimer.Stop();
        _relativeTimeTimer.Stop();
        _appWindow?.Hide();
    }

    public void CloseForExit()
    {
        _contentRefreshTimer.Stop();
        _relativeTimeTimer.Stop();
        _allowClose = true;
        Close();
    }

    private void Close_Click(object sender, RoutedEventArgs e) => Hide();

    private static bool IsUsefulGlanceCard(CardItem card)
    {
        var text = $"{card.Title} {card.Summary}";
        return !text.Contains("此網站已在背景更新", StringComparison.OrdinalIgnoreCase)
               && !text.Contains("這個網站已在背景更新", StringComparison.OrdinalIgnoreCase);
    }
    private void Dashboard_Click(object sender, RoutedEventArgs e)
    {
        Hide();
        ((App)Application.Current).ShowMessage("SignalDesk", "已開啟完整工作區。", InfoBarSeverity.Informational);
    }
    private async void Card_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string cardId }) await ((App)Application.Current).OpenCardAsync(cardId);
    }
    private async void Draft_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string cardId }) await ((App)Application.Current).OpenCardAsync(cardId);
    }
    private async void Snooze_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string cardId }) return;
        try
        {
            await _state.Api.CardActionAsync(
                cardId, "snooze", new { at = DateTimeOffset.Now.AddHours(1).ToString("O") });
            ActivateAndRefresh();
        }
        catch (Exception error)
        {
            ((App)Application.Current).ShowMessage("無法稍後提醒", error.Message, InfoBarSeverity.Error);
        }
    }
}
