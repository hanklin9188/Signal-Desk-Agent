using System.Collections.ObjectModel;
using System.Text.Json;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Automation;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Media.Imaging;
using SignalDesk.Shell.Models;
using SignalDesk.Shell.Services;
using Windows.Storage.Streams;
using Windows.System;

namespace SignalDesk.Shell.Views;

public sealed partial class InboxPage : UserControl, IAsyncPage
{
    private readonly AppState _state;
    private readonly string _view;
    private string _search = "";
    private string? _loadingDetailCardId;
    private bool _loaded;

    public InboxPage(AppState state, string view)
    {
        _state = state;
        _view = view;
        Cards = state.Cards;
        InitializeComponent();
        (ViewEyebrow.Text, ViewTitle.Text) = view switch
        {
            "today" => ("DUE & RECENT", "今天"),
            "reply" => ("WAITING ON YOU", "需要回覆"),
            "done" => ("ARCHIVE", "已完成"),
            _ => ("INBOX CENTER", "現在")
        };
    }

    public ObservableCollection<CardItem> Cards { get; }
    public CardDetail? Detail { get; private set; }

    public async Task LoadAsync()
    {
        await ApplyFilterAsync();
        _loaded = true;
        UpdateResponsiveLayout();
    }

    public async Task SearchAsync(string value)
    {
        _search = value;
        await ApplyFilterAsync();
    }

    public async Task SelectCardAsync(string cardId)
    {
        var card = Cards.FirstOrDefault(item => item.CardId == cardId);
        if (card is null)
        {
            await _state.LoadCardsAsync("now");
            card = Cards.FirstOrDefault(item => item.CardId == cardId);
        }
        if (card is not null)
        {
            CardList.SelectedItem = card;
            CardList.ScrollIntoView(card);
        }
    }

    private async Task ApplyFilterAsync()
    {
        var priority = (PriorityFilter.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "";
        var source = (SourceFilter.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "";
        var date = (DateFilter.SelectedItem as ComboBoxItem)?.Tag?.ToString() ?? "";
        await _state.LoadCardsAsync(_view, _search, source, priority, date);
        ViewCount.Text = Cards.Count.ToString();
        var isEmpty = Cards.Count == 0;
        ListEmptyState.Visibility = isEmpty ? Visibility.Visible : Visibility.Collapsed;
        BulkBar.IsEnabled = !isEmpty;
        EmptyTitle.Text = isEmpty ? "目前沒有需要處理的訊息" : "選擇一則訊息";
        EmptyMessage.Text = isEmpty
            ? "SignalDesk 會在背景整理允許的來源；重要訊息抵達時會出現在左側。"
            : "查看摘要、原文證據、待辦與安全的下一步。";
    }

    private async void Filter_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_loaded) await ApplyFilterAsync();
    }

    private async void CardList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CardList.SelectedItem is not CardItem card) return;
        await ShowCardDetailAsync(card);
    }

    private async void CardList_ItemClick(object sender, ItemClickEventArgs e)
    {
        if (e.ClickedItem is CardItem card) await ShowCardDetailAsync(card);
    }

    private async Task ShowCardDetailAsync(CardItem card)
    {
        if (_loadingDetailCardId == card.CardId) return;
        _loadingDetailCardId = card.CardId;
        try
        {
            Detail = await _state.Api.CardAsync(card.CardId);
            Bindings.Update();
            DetailScroll.Visibility = Visibility.Visible;
            EmptyState.Visibility = Visibility.Collapsed;
            LimitationBar.Visibility = Detail.HasLimitation ? Visibility.Visible : Visibility.Collapsed;
            NoActionsText.Visibility = Detail.ActionItems.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
            NoDeadlinesText.Visibility = Detail.Deadlines.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
            DraftButton.Visibility = Detail.Actions.Contains("draft_reply") ? Visibility.Visible : Visibility.Collapsed;
            ReminderButton.Visibility = Detail.Actions.Contains("create_reminder") ? Visibility.Visible : Visibility.Collapsed;
            OpenButton.IsEnabled = Detail.Actions.Contains("open_source");
            DetailScroll.ChangeView(null, 0, null, true);
            UpdateResponsiveLayout();
        }
        catch (Exception error) { ShowMessage("無法載入訊息", error.Message, InfoBarSeverity.Error); }
        finally { _loadingDetailCardId = null; }
    }

    private void BulkToggle_Changed(object sender, RoutedEventArgs e)
    {
        CardList.SelectionMode = BulkToggle.IsChecked == true
            ? ListViewSelectionMode.Multiple : ListViewSelectionMode.Single;
        if (BulkToggle.IsChecked != true && CardList.SelectedItems.Count > 1)
            CardList.SelectedItems.Clear();
    }

    private async void BulkDone_Click(object sender, RoutedEventArgs e) =>
        await RunBulkAsync("mark_done", null, "選取的項目已完成");

    private async void BulkSnooze_Click(object sender, RoutedEventArgs e) =>
        await RunBulkAsync(
            "snooze", new { at = DateTimeOffset.Now.AddHours(1).ToString("O") },
            "選取的項目已延後 1 小時");

    private async Task RunBulkAsync(string action, object? value, string message)
    {
        var selected = CardList.SelectedItems.OfType<CardItem>().ToList();
        if (selected.Count == 0)
        {
            ShowMessage("尚未選取", "請先開啟批次選取並勾選至少一則訊息。", InfoBarSeverity.Warning);
            return;
        }
        try
        {
            foreach (var card in selected)
                await _state.Api.CardActionAsync(card.CardId, action, value);
            ShowMessage("批次操作完成", message);
            await ApplyFilterAsync();
        }
        catch (Exception error) { ShowMessage("批次操作未完成", error.Message, InfoBarSeverity.Error); }
    }

    private async void CardAction_Click(object sender, RoutedEventArgs e)
    {
        if (Detail is null || sender is not Button button || button.Tag is not string action) return;
        try
        {
            switch (action)
            {
                case "open": await OpenSourceAsync(); break;
                case "mark_done": await ExecuteAsync("mark_done", null, "已標示完成"); break;
                case "snooze": await SnoozeAsync(); break;
                case "create_reminder": await ReminderAsync(); break;
                case "draft_reply": await DraftAsync(); break;
            }
        }
        catch (Exception error) { ShowMessage("操作失敗", error.Message, InfoBarSeverity.Error); }
    }

    private async Task OpenSourceAsync()
    {
        if (Detail is null) return;
        var result = await _state.Api.CardActionAsync(Detail.CardId, "open");
        if (result.TryGetProperty("source_url", out var source) &&
            Uri.TryCreate(source.GetString(), UriKind.Absolute, out var uri))
            await Launcher.LaunchUriAsync(uri);
        else ShowMessage("無法開啟", "來源沒有提供安全的連結。", InfoBarSeverity.Warning);
    }

    private async void Media_Click(object sender, RoutedEventArgs e)
    {
        if (Detail is null || sender is not Button { Tag: string assetId }) return;
        var media = Detail.Events
            .SelectMany(item => item.Media)
            .FirstOrDefault(item => item.AssetId == assetId);
        if (media is null || !media.IsAvailable) return;
        try
        {
            var bytes = await _state.Api.MediaAsync(assetId);
            using var stream = new InMemoryRandomAccessStream();
            using (var writer = new DataWriter(stream))
            {
                writer.WriteBytes(bytes);
                await writer.StoreAsync();
                writer.DetachStream();
            }
            stream.Seek(0);
            var bitmap = new BitmapImage();
            await bitmap.SetSourceAsync(stream);
            var image = new Image
            {
                Source = bitmap,
                Stretch = Stretch.Uniform,
                MaxHeight = 660,
                MaxWidth = 920,
                HorizontalAlignment = HorizontalAlignment.Center
            };
            AutomationProperties.SetName(
                image,
                media.AltText ?? media.OriginalName ?? "訊息圖片");
            var dialog = new ContentDialog
            {
                XamlRoot = XamlRoot,
                Title = media.OriginalName ?? "訊息圖片",
                Content = new ScrollViewer
                {
                    Content = image,
                    MaxHeight = 700,
                    HorizontalScrollMode = ScrollMode.Auto,
                    VerticalScrollMode = ScrollMode.Auto,
                    ZoomMode = ZoomMode.Enabled
                },
                CloseButtonText = "關閉",
                DefaultButton = ContentDialogButton.Close
            };
            await dialog.ShowAsync();
        }
        catch (Exception error)
        {
            ShowMessage("圖片無法開啟", error.Message, InfoBarSeverity.Error);
        }
    }

    private async Task SnoozeAsync()
    {
        if (Detail is null) return;
        var choices = new ComboBox { ItemsSource = new[] { "1 小時", "3 小時", "明天早上 9 點" }, SelectedIndex = 0 };
        var dialog = NewDialog("稍後提醒", choices, "確認");
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        var at = choices.SelectedIndex switch
        {
            1 => DateTimeOffset.Now.AddHours(3),
            2 => new DateTimeOffset(DateTime.Today.AddDays(1).AddHours(9)),
            _ => DateTimeOffset.Now.AddHours(1)
        };
        await ExecuteAsync("snooze", new { at = at.ToString("O") }, "已稍後提醒");
    }

    private async Task ReminderAsync()
    {
        if (Detail is null) return;
        var date = new CalendarDatePicker { Header = "日期", Date = DateTimeOffset.Now.AddDays(1) };
        var time = new TimePicker { Header = "時間", Time = new TimeSpan(9, 0, 0) };
        var note = new TextBox { Header = "備註（選填）", PlaceholderText = "例如：先整理圖表" };
        var panel = new StackPanel { Spacing = 10 };
        panel.Children.Add(date); panel.Children.Add(time); panel.Children.Add(note);
        var dialog = NewDialog("建立本機提醒", panel, "建立提醒");
        if (await dialog.ShowAsync() != ContentDialogResult.Primary || date.Date is null) return;
        var at = date.Date.Value.Date + time.Time;
        await ExecuteAsync(
            "create_reminder", new { at = at.ToString("O"), note = note.Text }, "提醒已建立");
    }

    private async Task DraftAsync()
    {
        if (Detail is null) return;
        var editor = new TextBox
        {
            Header = "回覆內容", AcceptsReturn = true, TextWrapping = TextWrapping.Wrap,
            MinHeight = 170,
            Text = "您好，\n\n謝謝您的訊息，我已收到。我確認內容後會再回覆您。\n\n謝謝。"
        };
        var panel = new StackPanel { Spacing = 10 };
        panel.Children.Add(new InfoBar
        {
            IsOpen = true, IsClosable = false, Severity = InfoBarSeverity.Success,
            Title = "只建立草稿", Message = "SignalDesk 不會自動送出訊息。"
        });
        panel.Children.Add(editor);
        var dialog = NewDialog("建立 Gmail 回覆草稿", panel, "儲存草稿");
        if (await dialog.ShowAsync() != ContentDialogResult.Primary) return;
        var result = await _state.Api.CardActionAsync(
            Detail.CardId, "draft_reply", new { body = editor.Text });
        ShowMessage("本機草稿已建立", "內容尚未送出，你可以繼續檢查與修改。");

        var accountId = Detail.Events.LastOrDefault()?.AccountId ?? "personal";
        var supportsCloudDraft = _state.Connectors.Any(
            connector => connector.ConnectorId == $"gmail:{accountId}" &&
                         connector.Capabilities.Contains("create_draft"));
        if (supportsCloudDraft && result.TryGetProperty("draft_id", out var draftValue))
        {
            var confirm = new ContentDialog
            {
                XamlRoot = XamlRoot,
                Title = "同步到 Gmail 草稿匣？",
                Content = "這只會建立 Gmail Draft，不會送出郵件。收件者、主旨與內容會使用你剛剛確認的版本。",
                PrimaryButtonText = "建立 Gmail 草稿",
                CloseButtonText = "只保留本機草稿",
                DefaultButton = ContentDialogButton.Close
            };
            if (await confirm.ShowAsync() == ContentDialogResult.Primary)
            {
                await _state.Api.CreateGmailDraftAsync(draftValue.GetString() ?? "");
                ShowMessage("Gmail 草稿已建立", "郵件仍未送出，請在 Gmail 中做最後確認。");
            }
        }
        Detail = null;
        DetailScroll.Visibility = Visibility.Collapsed;
        EmptyState.Visibility = Visibility.Visible;
        UpdateResponsiveLayout();
        await ApplyFilterAsync();
    }

    private void MoreButton_Click(object sender, RoutedEventArgs e)
    {
        if (Detail is null || sender is not Button button) return;
        var flyout = new MenuFlyout();
        var important = new MenuFlyoutItem { Text = "總是重視此寄件者", Icon = new FontIcon { Glyph = "\uE8D7" } };
        important.Click += async (_, _) => await ExecuteAsync("mark_important", null, "已加入重要寄件者");
        var mute = new MenuFlyoutItem { Text = "不要打斷此寄件者", Icon = new FontIcon { Glyph = "\uE74F" } };
        mute.Click += async (_, _) => await ExecuteAsync("mark_not_important", null, "已建立靜音規則");
        flyout.Items.Add(important); flyout.Items.Add(mute);
        flyout.ShowAt(button);
    }

    private async Task ExecuteAsync(string action, object? value, string success)
    {
        if (Detail is null) return;
        await _state.Api.CardActionAsync(Detail.CardId, action, value);
        ShowMessage("已完成", success);
        Detail = null;
        DetailScroll.Visibility = Visibility.Collapsed;
        EmptyState.Visibility = Visibility.Visible;
        UpdateResponsiveLayout();
        await ApplyFilterAsync();
    }

    private void InboxPage_SizeChanged(object sender, SizeChangedEventArgs e) =>
        UpdateResponsiveLayout();

    private void BackToList_Click(object sender, RoutedEventArgs e)
    {
        CardList.SelectedItem = null;
        Detail = null;
        DetailScroll.Visibility = Visibility.Collapsed;
        EmptyState.Visibility = Visibility.Visible;
        UpdateResponsiveLayout();
    }

    private void UpdateResponsiveLayout()
    {
        var compact = ActualWidth > 0 && ActualWidth < 860;
        // A StackPanel hosted directly by ScrollViewer is measured at its desired
        // width instead of the viewport width on some DPI/layout combinations.
        // Give the detail content an explicit viewport-relative width so compact
        // desktop windows never collapse the message into a narrow right column.
        DetailContent.Width = compact
            ? ActualWidth
            : Math.Min(920, Math.Max(0, ActualWidth - 460));
        BackToListButton.Visibility = compact && Detail is not null
            ? Visibility.Visible
            : Visibility.Collapsed;
        if (!compact)
        {
            ListPane.Visibility = Visibility.Visible;
            DetailPane.Visibility = Visibility.Visible;
            ListColumn.MinWidth = 380;
            ListColumn.Width = new GridLength(460);
            DetailColumn.Width = new GridLength(1, GridUnitType.Star);
            return;
        }

        var showingDetail = Detail is not null;
        ListPane.Visibility = showingDetail ? Visibility.Collapsed : Visibility.Visible;
        DetailPane.Visibility = showingDetail ? Visibility.Visible : Visibility.Collapsed;
        ListColumn.MinWidth = showingDetail ? 0 : 380;
        ListColumn.Width = showingDetail
            ? new GridLength(0)
            : new GridLength(1, GridUnitType.Star);
        DetailColumn.Width = showingDetail
            ? new GridLength(1, GridUnitType.Star)
            : new GridLength(0);
    }

    private ContentDialog NewDialog(string title, object content, string primary) => new()
    {
        XamlRoot = XamlRoot, Title = title, Content = content,
        PrimaryButtonText = primary, CloseButtonText = "取消",
        DefaultButton = ContentDialogButton.Primary
    };

    private void ShowMessage(string title, string message, InfoBarSeverity severity = InfoBarSeverity.Success) =>
        ((App)Application.Current).ShowMessage(title, message, severity);
}
