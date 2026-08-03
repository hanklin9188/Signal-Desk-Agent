using System.Text.Json;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SignalDesk.Shell.Services;
using Windows.ApplicationModel;

namespace SignalDesk.Shell.Views;

public sealed partial class SettingsPage : UserControl, IAsyncPage
{
    private const string StartupTaskId = "SignalDeskStartup";
    private readonly AppState _state;
    private StartupTask? _startupTask;
    private bool _ready;

    public SettingsPage(AppState state)
    {
        _state = state;
        InitializeComponent();
    }

    public async Task LoadAsync()
    {
        var prefs = _state.Preferences;
        FocusModeToggle.IsOn = prefs.FocusMode;
        ShadowModeToggle.IsOn = prefs.ShadowMode;
        QuietStartPicker.Time = ParseTime(prefs.QuietStart, new TimeSpan(23, 0, 0));
        QuietEndPicker.Time = ParseTime(prefs.QuietEnd, new TimeSpan(8, 0, 0));
        DigestTimePicker.Time = ParseTime(prefs.DigestTime, new TimeSpan(18, 0, 0));
        FocusDigestBox.Value = prefs.FocusDigestMinutes;
        RetentionDaysBox.Value = prefs.RawRetentionDays;
        AllowlistBox.Text = string.Join(", ", prefs.NotificationAllowlist);
        SelectByTag(ThemeCombo, prefs.Theme);
        SelectByTag(ModelResidencyCombo, prefs.ModelResidency);
        ModelRuntimeStatusText.Text = _state.Model.Backend == "rule"
            ? "目前使用規則引擎，不占用模型 VRAM。"
            : $"{_state.Model.Id} · {_state.Model.Quantization.ToUpperInvariant()}。建議使用『需要時載入』，閒置時不占用模型 VRAM。";

        try
        {
            _startupTask = await StartupTask.GetAsync(StartupTaskId);
            StartupToggle.IsOn = _startupTask.State == StartupTaskState.Enabled;
            StartupStatusText.Text = StartupLabel(_startupTask.State);
        }
        catch (Exception error)
        {
            StartupToggle.IsEnabled = false;
            StartupStatusText.Text = $"目前無法設定開機啟動：{error.Message}";
        }
        _ready = true;
    }

    private async void Save_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            await _state.UpdateSettingsAsync(new
            {
                focus_mode = FocusModeToggle.IsOn,
                shadow_mode = ShadowModeToggle.IsOn,
                quiet_start = FormatTime(QuietStartPicker.Time),
                quiet_end = FormatTime(QuietEndPicker.Time),
                digest_time = FormatTime(DigestTimePicker.Time),
                focus_digest_minutes = (int)FocusDigestBox.Value,
                theme = SelectedTag(ThemeCombo, "system"),
                model_residency = SelectedTag(ModelResidencyCombo, "on_demand"),
                raw_retention_days = (int)RetentionDaysBox.Value,
                notification_allowlist = AllowlistBox.Text
                    .Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries)
            });
            ((App)Application.Current).ApplyTheme();
            Show("設定已儲存", "新的桌面與提醒偏好已立即生效。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("無法儲存", error.Message, InfoBarSeverity.Error); }
    }

    private async void StartupToggle_Toggled(object sender, RoutedEventArgs e)
    {
        if (!_ready || _startupTask is null) return;
        try
        {
            if (StartupToggle.IsOn && _startupTask.State != StartupTaskState.Enabled)
                await _startupTask.RequestEnableAsync();
            else if (!StartupToggle.IsOn && _startupTask.State == StartupTaskState.Enabled)
                _startupTask.Disable();

            StartupToggle.IsOn = _startupTask.State == StartupTaskState.Enabled;
            StartupStatusText.Text = StartupLabel(_startupTask.State);
        }
        catch (Exception error)
        {
            StartupToggle.IsOn = _startupTask.State == StartupTaskState.Enabled;
            Show("無法變更開機啟動", error.Message, InfoBarSeverity.Error);
        }
    }

    private async void Export_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var data = await _state.Api.PrivacyExportAsync();
            var folder = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "SignalDesk", "exports");
            Directory.CreateDirectory(folder);
            var path = Path.Combine(folder, $"signaldesk-export-{DateTime.Now:yyyyMMdd-HHmmss}.json");
            await File.WriteAllTextAsync(path, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }));
            Show("資料已匯出", path, InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("匯出失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void DeleteData_Click(object sender, RoutedEventArgs e)
    {
        var confirmation = new TextBox { Header = "輸入 DELETE 確認", PlaceholderText = "DELETE" };
        var panel = new StackPanel { Spacing = 10 };
        panel.Children.Add(new TextBlock
        {
            Text = "這會清除本機的私人訊息、卡片、草稿、提醒與學習偏好。此操作無法復原。",
            TextWrapping = TextWrapping.Wrap
        });
        panel.Children.Add(confirmation);
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot, Title = "清除 SignalDesk 私人資料", Content = panel,
            PrimaryButtonText = "永久清除", CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        if (confirmation.Text != "DELETE")
        {
            Show("未清除資料", "確認文字不正確。", InfoBarSeverity.Warning);
            return;
        }
        try
        {
            await _state.Api.DeletePrivateDataAsync();
            await _state.RefreshAsync();
            Show("私人資料已清除", "設定本身與應用程式仍保留，可重新開始使用。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("清除失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void ResetPersonalization_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot, Title = "重設個人化學習？",
            Content = "這會清除本機 preference ranker 的匿名特徵與權重；你手動建立的重要／靜音規則不受影響。",
            PrimaryButtonText = "重設", CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        try
        {
            await _state.Api.ResetPreferencesAsync();
            Show("個人化已重設", "SignalDesk 會從之後的操作重新學習。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("重設失敗", error.Message, InfoBarSeverity.Error); }
    }

    private static TimeSpan ParseTime(string value, TimeSpan fallback) =>
        TimeSpan.TryParse(value, out var parsed) ? parsed : fallback;
    private static string FormatTime(TimeSpan value) => $"{value.Hours:00}:{value.Minutes:00}";
    private static string SelectedTag(ComboBox combo, string fallback) =>
        (combo.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? fallback;
    private static void SelectByTag(ComboBox combo, string tag) => combo.SelectedItem =
        combo.Items.OfType<ComboBoxItem>().FirstOrDefault(item => item.Tag?.ToString() == tag) ?? combo.Items[0];
    private static string StartupLabel(StartupTaskState state) => state switch
    {
        StartupTaskState.Enabled => "SignalDesk 會在登入 Windows 後自動啟動。",
        StartupTaskState.DisabledByUser => "Windows 已阻止此 App 自動啟動；可在 Windows 設定的『啟動應用程式』重新開啟。",
        StartupTaskState.DisabledByPolicy => "此裝置的系統管理原則不允許自動啟動。",
        _ => "目前不會隨 Windows 自動啟動。"
    };
    private static void Show(string title, string message, InfoBarSeverity severity) =>
        ((App)Application.Current).ShowMessage(title, message, severity);
}
