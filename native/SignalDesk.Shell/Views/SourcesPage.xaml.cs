using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using SignalDesk.Shell.Models;
using SignalDesk.Shell.Services;
using Windows.System;

namespace SignalDesk.Shell.Views;

public sealed partial class SourcesPage : UserControl, IAsyncPage
{
    private readonly AppState _state;
    public ObservableCollection<ConnectorItem> Connectors => _state.Connectors;

    public SourcesPage(AppState state)
    {
        _state = state;
        InitializeComponent();
    }

    public Task LoadAsync() => Task.CompletedTask;

    private async void PersonalChatGuide_Click(object sender, RoutedEventArgs e)
    {
        var content = new StackPanel { Spacing = 10, MaxWidth = 590 };
        content.Children.Add(GuideStep(
            "1", "LINE Windows：設定 → 通知；取消靜音，通知樣式選擇 Windows。"));
        content.Children.Add(GuideStep(
            "2", "Messenger：使用 Windows App，或將 messenger.com 安裝成獨立瀏覽器 App，並允許訊息通知與文字預覽。"));
        content.Children.Add(GuideStep(
            "3", "Windows：設定 → 系統 → 通知；開啟 LINE、Messenger（或所用瀏覽器）的通知。"));
        content.Children.Add(GuideStep(
            "4", "回到 SignalDesk 重新檢查通知權限；顯示已連線後，請從另一個帳號各傳一則測試文字。"));
        content.Children.Add(new InfoBar
        {
            IsOpen = true,
            IsClosable = false,
            Severity = InfoBarSeverity.Success,
            Title = "不用設定企業 Token",
            Message = "LINE Channel Secret 與 Meta App Secret 都不會讓個人聊天同步得更完整。"
        });
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = "個人 LINE／Messenger 最新訊息同步",
            Content = content,
            PrimaryButtonText = "重新檢查權限",
            SecondaryButtonText = "Windows 通知設定",
            CloseButtonText = "關閉",
            DefaultButton = ContentDialogButton.Primary
        };
        var result = await dialog.ShowAsync();
        if (result == ContentDialogResult.Secondary)
        {
            await Launcher.LaunchUriAsync(new Uri("ms-settings:notifications"));
            return;
        }
        if (result != ContentDialogResult.Primary) return;

        var access = await ((App)Application.Current).RequestNotificationAccessAsync();
        await _state.RefreshAsync();
        Show(
            access == "allowed" ? "個人聊天同步已準備好" : "仍需開啟通知權限",
            access == "allowed"
                ? "SignalDesk 已可讀取 Windows 實際顯示的通知預覽。請各傳一則新的 LINE／Messenger 測試文字。"
                : "請在 Windows 通知設定允許 SignalDesk，再回來重新檢查。",
            access == "allowed" ? InfoBarSeverity.Success : InfoBarSeverity.Warning);
    }

    private async void ImportLine_Click(object sender, RoutedEventArgs e) =>
        await ImportArchivesAsync("line");

    private async void ImportMessenger_Click(object sender, RoutedEventArgs e) =>
        await ImportArchivesAsync("messenger");

    private async Task ImportArchivesAsync(string source)
    {
        var paths = await ((App)Application.Current).PickChatArchivesAsync(source);
        if (paths.Count == 0) return;
        var label = source == "line" ? "LINE" : "Messenger";
        var description = new StackPanel { Spacing = 8, MaxWidth = 520 };
        description.Children.Add(new TextBlock
        {
            Text = $"將從 {paths.Count} 個檔案匯入 {label} 歷史聊天。檔案只在本機讀取；已存在的訊息會自動略過。",
            TextWrapping = TextWrapping.Wrap
        });
        description.Children.Add(new InfoBar
        {
            IsOpen = true,
            IsClosable = false,
            Severity = InfoBarSeverity.Informational,
            Title = "匯入不會傳送或刪除訊息",
            Message = "歷史內容只用於本機搜尋、分組與摘要；匯入後的新訊息仍由 Windows 通知補上。"
        });
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = $"匯入 {label} 聊天記錄？",
            Content = description,
            PrimaryButtonText = "開始匯入",
            CloseButtonText = "取消",
            DefaultButton = ContentDialogButton.Primary
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;

        ImportLineButton.IsEnabled = false;
        ImportMessengerButton.IsEnabled = false;
        ImportProgressPanel.Visibility = Visibility.Visible;
        ImportProgressText.Text = $"正在本機解析與整理 {label} 聊天記錄…";
        try
        {
            var result = await _state.Api.ImportChatArchivesAsync(source, paths);
            await _state.RefreshAsync();
            var warning = result.Warnings.Count > 0
                ? $"；另有 {result.Warnings.Count} 個格式提醒"
                : "";
            Show(
                $"{label} 歷史已更新",
                $"{result.Conversations} 個對話、{result.Imported:N0} 則新訊息；略過 {result.Duplicates:N0} 則重複與 {result.Skipped:N0} 則無文字項目{warning}。",
                result.Warnings.Count > 0 ? InfoBarSeverity.Warning : InfoBarSeverity.Success);
        }
        catch (Exception error)
        {
            Show("匯入失敗", error.Message, InfoBarSeverity.Error);
        }
        finally
        {
            ImportProgressPanel.Visibility = Visibility.Collapsed;
            ImportLineButton.IsEnabled = true;
            ImportMessengerButton.IsEnabled = true;
        }
    }

    private async void OAuthGuide_Click(object sender, RoutedEventArgs e)
    {
        var content = new StackPanel { Spacing = 10, MaxWidth = 560 };
        content.Children.Add(GuideStep("1", "在 Google Cloud 建立專案，啟用 Gmail API。"));
        content.Children.Add(GuideStep(
            "2", "在 Google Auth Platform 設定 External／Testing，將要連接的兩個帳號加入 Test users。"));
        content.Children.Add(GuideStep(
            "3", "建立「Desktop app」OAuth client，下載 JSON。這不是 Gmail 密碼。"));
        content.Children.Add(GuideStep(
            "4", "新增第一個帳號時用原生檔案選擇器挑選 JSON；第二個帳號可沿用同一檔案。"));
        content.Children.Add(GuideStep(
            "5", "瀏覽器開啟後，依別名選對 Google 帳號並核對權限。預設只讀；草稿權限需另外勾選。"));
        content.Children.Add(new InfoBar
        {
            IsOpen = true,
            IsClosable = false,
            Severity = InfoBarSeverity.Warning,
            Title = "不要輸入帳號密碼",
            Message = "SignalDesk 沒有 Gmail 密碼欄位；Google 登入只會發生在 Google 的瀏覽器頁面。"
        });
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = "設定 Gmail OAuth",
            Content = content,
            PrimaryButtonText = "開啟 Gmail API 設定",
            CloseButtonText = "稍後處理",
            DefaultButton = ContentDialogButton.Primary
        };
        if (await dialog.ShowAsync() == ContentDialogResult.Primary)
            await Launcher.LaunchUriAsync(
                new Uri("https://console.cloud.google.com/apis/library/gmail.googleapis.com"));
    }

    private async void AddGmail_Click(object sender, RoutedEventArgs e)
    {
        var alias = new TextBox
        {
            Header = "帳號別名", PlaceholderText = "例如 work 或 personal",
            Description = "只可使用英文字母、數字、句點、底線或連字號。"
        };
        var credentials = new TextBox
        {
            Header = "credentials.json 路徑（留空使用預設路徑）",
            PlaceholderText = @"C:\Users\you\Downloads\credentials.json",
            Description = "這是 Google Cloud 下載的 Desktop OAuth JSON，不是帳號密碼。"
        };
        var browse = new Button { Content = "瀏覽…", VerticalAlignment = VerticalAlignment.Bottom };
        browse.Click += async (_, _) =>
        {
            var selected = await ((App)Application.Current).PickGmailCredentialsAsync();
            if (!string.IsNullOrWhiteSpace(selected)) credentials.Text = selected;
        };
        var credentialsRow = new Grid { ColumnSpacing = 8 };
        credentialsRow.ColumnDefinitions.Add(new ColumnDefinition());
        credentialsRow.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        Grid.SetColumn(browse, 1);
        credentialsRow.Children.Add(credentials);
        credentialsRow.Children.Add(browse);
        var draftScope = new CheckBox
        {
            Content = "允許在確認後建立 Gmail 雲端草稿（App 沒有寄送端點）"
        };
        var panel = new StackPanel { Spacing = 10 };
        panel.Children.Add(alias); panel.Children.Add(credentialsRow); panel.Children.Add(draftScope);
        panel.Children.Add(new TextBlock
        {
            Text = "個人帳號建議使用 personal，學校帳號可用 nycu。別名只用來區分本機 token，不必填完整 Email。",
            FontSize = 11,
            TextWrapping = TextWrapping.Wrap,
            Foreground = (Brush)Application.Current.Resources["TextFillColorSecondaryBrush"]
        });
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot, Title = "新增 Gmail 帳號", Content = panel,
            PrimaryButtonText = "新增並開始 OAuth", CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        try
        {
            await _state.Api.AddGmailAccountAsync(
                alias.Text.Trim(),
                string.IsNullOrWhiteSpace(credentials.Text) ? null : credentials.Text.Trim(),
                draftScope.IsChecked == true);
            await _state.Api.ConnectGmailAsync(alias.Text.Trim());
            await _state.RefreshAsync();
            Show("Gmail 已連接", $"帳號 {alias.Text.Trim()} 已完成初次同步。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("新增失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void Connect_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string id }) return;
        try
        {
            if (id.StartsWith("gmail"))
            {
                var item = _state.Connectors.First(value => value.ConnectorId == id);
                var credentials = new TextBox
                {
                    Header = "更換 credentials.json（不更換可留空）",
                    PlaceholderText = @"C:\Users\you\Downloads\credentials.json",
                    Description = "只接受 Google Cloud 的 Desktop app OAuth JSON。"
                };
                var browse = new Button
                {
                    Content = "瀏覽…",
                    VerticalAlignment = VerticalAlignment.Bottom
                };
                browse.Click += async (_, _) =>
                {
                    var selected = await ((App)Application.Current).PickGmailCredentialsAsync();
                    if (!string.IsNullOrWhiteSpace(selected)) credentials.Text = selected;
                };
                var credentialsRow = new Grid { ColumnSpacing = 8 };
                credentialsRow.ColumnDefinitions.Add(new ColumnDefinition());
                credentialsRow.ColumnDefinitions.Add(
                    new ColumnDefinition { Width = GridLength.Auto });
                Grid.SetColumn(browse, 1);
                credentialsRow.Children.Add(credentials);
                credentialsRow.Children.Add(browse);
                var draftScope = new CheckBox
                {
                    Content = "允許在確認後建立 Gmail 雲端草稿（App 沒有寄送端點）",
                    IsChecked = item.Capabilities.Contains("create_draft")
                };
                var content = new StackPanel { Spacing = 10 };
                content.Children.Add(new TextBlock
                {
                    Text = "繼續後只會開啟 Google 官方 OAuth 網頁。請依帳號別名選對 Google 帳號；SignalDesk 不會要求或讀取 Gmail 密碼。",
                    TextWrapping = TextWrapping.Wrap
                });
                content.Children.Add(credentialsRow);
                content.Children.Add(draftScope);
                var dialog = new ContentDialog
                {
                    XamlRoot = XamlRoot, Title = "連接 Gmail",
                    Content = content,
                    PrimaryButtonText = "開始 OAuth", CloseButtonText = "取消"
                };
                if (await dialog.ShowAsync() == ContentDialogResult.Primary)
                {
                    await _state.Api.ConfigureGmailAccountAsync(
                        id[6..],
                        string.IsNullOrWhiteSpace(credentials.Text) ? null : credentials.Text.Trim(),
                        draftScope.IsChecked == true);
                    await _state.Api.ConnectGmailAsync(id[6..]);
                    await _state.RefreshAsync();
                    Show("Gmail 已連接", "初次同步已完成。", InfoBarSeverity.Success);
                }
            }
            else
            {
                var item = _state.Connectors.FirstOrDefault(value => value.ConnectorId == id);
                if (item?.Capabilities.Contains("receive_webhook") == true)
                    Show(
                        item.DisplayName,
                        "請在服務環境設定官方 channel/app secret 與公開 HTTPS webhook URL；SignalDesk 會驗證每一筆簽章。",
                        InfoBarSeverity.Informational);
                else
                {
                    var access = await ((App)Application.Current)
                        .RequestNotificationAccessAsync();
                    await _state.RefreshAsync();
                    if (access == "allowed")
                        Show(
                            "通知同步已啟用",
                            "SignalDesk 現在會整理通知中心內既有的預覽，以及之後收到的 LINE／Messenger 通知。",
                            InfoBarSeverity.Success);
                    else if (access == "denied")
                        Show(
                            "需要通知存取權限",
                            "已為你開啟 Windows 的「通知隱私權」頁面；請允許 SignalDesk，再回來按一次檢查。",
                            InfoBarSeverity.Warning);
                    else
                        Show(
                            "尚未取得通知權限",
                            "Windows 沒有回傳允許狀態，請再按一次；若仍未出現授權視窗，請開啟通知隱私權設定。",
                            InfoBarSeverity.Warning);
                }
            }
        }
        catch (Exception error) { Show("連接失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void Sync_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string id } || !id.StartsWith("gmail")) return;
        try
        {
            await _state.Api.SyncGmailAsync(id[6..]);
            await _state.RefreshAsync();
            Show("同步完成", "Gmail 已更新。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("同步失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void Disconnect_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string id } || !id.StartsWith("gmail:")) return;
        var alias = id[6..];
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = $"中斷 Gmail · {alias}？",
            Content = "這會刪除 Windows Credential Manager 內這個別名的 OAuth token；既有 SignalDesk 卡片不會被刪除。",
            PrimaryButtonText = "中斷連線",
            CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        try
        {
            await _state.Api.DisconnectGmailAsync(alias);
            await _state.RefreshAsync();
            Show("Gmail 已中斷", $"帳號別名 {alias} 的 OAuth token 已移除。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("中斷失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async void Remove_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string id } || !id.StartsWith("gmail:")) return;
        var alias = id[6..];
        var dialog = new ContentDialog
        {
            XamlRoot = XamlRoot,
            Title = $"移除 Gmail · {alias}？",
            Content = "這會撤銷本機 token 並移除來源設定；已整理的訊息仍依資料保存設定保留。",
            PrimaryButtonText = "移除帳號",
            CloseButtonText = "取消"
        };
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        try
        {
            await _state.Api.RemoveGmailAccountAsync(alias);
            await _state.RefreshAsync();
            Show("Gmail 帳號已移除", $"來源 {alias} 已從 SignalDesk 移除。", InfoBarSeverity.Success);
        }
        catch (Exception error) { Show("移除失敗", error.Message, InfoBarSeverity.Error); }
    }

    private static Grid GuideStep(string number, string message)
    {
        var grid = new Grid { ColumnSpacing = 10 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) });
        grid.ColumnDefinitions.Add(new ColumnDefinition());
        var badge = new Border
        {
            Width = 28,
            Height = 28,
            CornerRadius = new CornerRadius(9),
            Background = (Brush)Application.Current.Resources["SignalAccentSoftBrush"],
            Child = new TextBlock
            {
                Text = number,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = (Brush)Application.Current.Resources["SignalAccentBrush"],
                FontWeight = Microsoft.UI.Text.FontWeights.SemiBold
            }
        };
        var text = new TextBlock
        {
            Text = message,
            TextWrapping = TextWrapping.Wrap,
            VerticalAlignment = VerticalAlignment.Center
        };
        Grid.SetColumn(text, 1);
        grid.Children.Add(badge);
        grid.Children.Add(text);
        return grid;
    }

    private static void Show(string title, string message, InfoBarSeverity severity) =>
        ((App)Application.Current).ShowMessage(title, message, severity);
}
