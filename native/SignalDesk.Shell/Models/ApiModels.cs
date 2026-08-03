using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Media;

namespace SignalDesk.Shell.Models;

public sealed class BootstrapResponse
{
    public string Version { get; set; } = "";
    public List<CardItem> Cards { get; set; } = [];
    public CardCounts Counts { get; set; } = new();
    public Dictionary<string, JsonElement> Settings { get; set; } = [];
    public List<ConnectorItem> Connectors { get; set; } = [];
    public ModelStatus Model { get; set; } = new();
    public PrivacyStatus Privacy { get; set; } = new();
}

public sealed class CardListResponse
{
    public List<CardItem> Items { get; set; } = [];
    public CardCounts Counts { get; set; } = new();
}

public sealed class CardCounts
{
    public int Open { get; set; }
    public int Important { get; set; }
    public int Reply { get; set; }
    public int Done { get; set; }
}

public class CardItem : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    public string CardId { get; set; } = "";
    public string ThreadId { get; set; } = "";
    public string Source { get; set; } = "";
    public string? Sender { get; set; }
    public string? Title { get; set; }
    public string Summary { get; set; } = "";
    public string Priority { get; set; } = "normal";
    public string Category { get; set; } = "other";
    public string RequiresReply { get; set; } = "no";
    public string? DeadlineText { get; set; }
    public string? DeadlineAt { get; set; }
    public List<string> Actions { get; set; } = [];
    public string DisplayMode { get; set; } = "inbox";
    public List<string> WhyShown { get; set; } = [];
    public string ContentCompleteness { get; set; } = "full";
    public List<string> UncertaintyFlags { get; set; } = [];
    public MediaAssetData? MediaPreview { get; set; }
    public string CreatedAt { get; set; } = "";
    public string UpdatedAt { get; set; } = "";
    public string Status { get; set; } = "open";
    public string? SnoozedUntil { get; set; }
    public int ActionCount { get; set; }
    private ImageSource? _thumbnailSource;

    public ImageSource? ThumbnailSource
    {
        get => _thumbnailSource;
        private set
        {
            _thumbnailSource = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(ThumbnailVisibility));
        }
    }

    public Visibility ThumbnailVisibility => ThumbnailSource is not null
        ? Visibility.Visible
        : Visibility.Collapsed;
    public void SetThumbnail(ImageSource? source) => ThumbnailSource = source;

    public string SenderLabel => Sender ?? Title ?? "未知來源";
    public string TitleLabel => Title ?? Summary;
    public string SourceInitial => Source switch
    {
        "gmail" => "G",
        "line_notification" => "L",
        "messenger_notification" => "M",
        "windows_notification" => "W",
        "line_official_webhook" => "L",
        "messenger_page_webhook" => "M",
        _ => "S"
    };
    public string SourceLabel => Source switch
    {
        "gmail" => "Gmail",
        "line_notification" => "LINE",
        "messenger_notification" => "Messenger",
        "windows_notification" => "Windows",
        "line_official_webhook" => "LINE OA",
        "messenger_page_webhook" => "Messenger Page",
        _ => Source
    };
    public string PriorityLabel => Priority switch
    {
        "urgent" => "緊急",
        "high" => "重要",
        "normal" => "一般",
        "low" => "低優先",
        "noise" => "雜訊",
        _ => "待確認"
    };
    public DateTimeOffset UpdatedAtValue => DateTimeOffset.TryParse(UpdatedAt, out var value)
        ? value
        : DateTimeOffset.MinValue;
    public string TimeLabel => FormatRelative(UpdatedAt);
    public void RefreshRelativeTime() => OnPropertyChanged(nameof(TimeLabel));
    public bool NeedsReply => RequiresReply == "yes";
    public Visibility ReplyVisibility => NeedsReply ? Visibility.Visible : Visibility.Collapsed;
    public bool HasDeadline => !string.IsNullOrWhiteSpace(DeadlineText);
    public bool HasLimitation => UncertaintyFlags.Count > 0;

    private static string FormatRelative(string value)
    {
        if (!DateTimeOffset.TryParse(value, out var time)) return "";
        var localTime = time.ToLocalTime();
        var now = DateTimeOffset.Now;
        var elapsed = now - localTime;
        if (elapsed.TotalMinutes < -1) return localTime.ToString("M/d HH:mm");
        if (elapsed.TotalSeconds < 45) return "剛剛";
        if (elapsed.TotalMinutes < 60)
            return $"{Math.Max(1, (int)elapsed.TotalMinutes)} 分鐘前";
        if (elapsed.TotalHours < 24)
            return $"{Math.Max(1, (int)elapsed.TotalHours)} 小時前";
        if (localTime.Date == now.Date.AddDays(-1)) return $"昨天 {localTime:HH:mm}";
        if (elapsed.TotalDays < 7) return $"{Math.Max(1, (int)elapsed.TotalDays)} 天前";
        return localTime.ToString("M/d HH:mm");
    }

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
}

public sealed class CardDetail : CardItem
{
    public List<SourceEvent> Events { get; set; } = [];
    public TriageData? Triage { get; set; }
    public ValidationData? Validation { get; set; }
    public DecisionData? Decision { get; set; }
    public string? ModelBackend { get; set; }
    public List<ActionItemData> ActionItems { get; set; } = [];
    public List<DeadlineData> Deadlines { get; set; } = [];
    public List<ReminderData> Reminders { get; set; } = [];
    public List<DraftData> Drafts { get; set; } = [];
    public List<TraceData> Traces { get; set; } = [];
    public string CompletenessLabel => ContentCompleteness switch
    {
        "full" => "完整郵件",
        "thread_delta" => "對話增量",
        "notification_preview" => "通知預覽",
        "metadata_only" => "只有來源資訊",
        _ => "混合內容"
    };
}

public sealed class SourceEvent
{
    public string EventId { get; set; } = "";
    public string Source { get; set; } = "";
    public string AccountId { get; set; } = "";
    public string Sender { get; set; } = "";
    public string? Title { get; set; }
    public string Content { get; set; } = "";
    public string ContentLabel => string.IsNullOrWhiteSpace(Content)
        ? "Windows 通知沒有提供可讀取的文字內容。"
        : Content;
    public string ContentCompleteness { get; set; } = "";
    public string ReceivedAt { get; set; } = "";
    public string? SourceUrl { get; set; }
    public List<MediaAssetData> Media { get; set; } = [];
}

public sealed class MediaAssetData
{
    public string AssetId { get; set; } = "";
    public string Kind { get; set; } = "image";
    public string? MimeType { get; set; }
    public string? OriginalName { get; set; }
    public long? ByteSize { get; set; }
    public int? Width { get; set; }
    public int? Height { get; set; }
    public string Availability { get; set; } = "metadata_only";
    public string? AltText { get; set; }
    public bool IsAvailable => Availability == "available";
    public string DisplayLabel => IsAvailable
        ? $"查看圖片 · {OriginalName ?? "圖片"}"
        : Availability switch
        {
            "blocked" => "圖片因安全規則未載入",
            "missing" => "找不到匯入的圖片",
            _ => "來源只提供圖片通知，沒有圖片內容"
        };
}

public sealed class TriageData
{
    public string Summary { get; set; } = "";
    public string Category { get; set; } = "";
    public string Priority { get; set; } = "";
    public string RequiresReply { get; set; } = "";
    public List<string> SupportingSpans { get; set; } = [];
    public List<string> UncertaintyFlags { get; set; } = [];
}

public sealed class ValidationData
{
    public bool Valid { get; set; }
    public List<string> Errors { get; set; } = [];
    public List<string> Warnings { get; set; } = [];
}

public sealed class DecisionData
{
    public string Decision { get; set; } = "";
    public List<string> ReasonCodes { get; set; } = [];
    public double? CalibratedScore { get; set; }
}

public sealed class ActionItemData
{
    public string Text { get; set; } = "";
    public string? Owner { get; set; }
    public string SupportingSpan { get; set; } = "";
    public string Status { get; set; } = "open";
}

public sealed class DeadlineData
{
    public string OriginalText { get; set; } = "";
    public string? NormalizedAt { get; set; }
    public string Precision { get; set; } = "unknown";
    public string SupportingSpan { get; set; } = "";
    public string DisplayTime => DateTimeOffset.TryParse(NormalizedAt, out var value)
        ? value.ToLocalTime().ToString("M/d ddd HH:mm")
        : "時間尚未確認";
}

public sealed class ReminderData
{
    public string ReminderId { get; set; } = "";
    public string RemindAt { get; set; } = "";
    public string? Note { get; set; }
    public string Status { get; set; } = "";
}

public sealed class DraftData
{
    public string DraftId { get; set; } = "";
    public string? Recipient { get; set; }
    public string? Subject { get; set; }
    public string Body { get; set; } = "";
    public string Status { get; set; } = "";
}

public sealed class TraceData
{
    public string TraceId { get; set; } = "";
    public string Stage { get; set; } = "";
    public string Status { get; set; } = "";
    public string CreatedAt { get; set; } = "";
}

public sealed class ConnectorItem
{
    public string ConnectorId { get; set; } = "";
    public string Source { get; set; } = "";
    public string Status { get; set; } = "";
    public string? Detail { get; set; }
    public List<string> Capabilities { get; set; } = [];
    public string? LastSyncAt { get; set; }
    public string AccountId => ConnectorId.StartsWith("gmail:") ? ConnectorId[6..] : "";
    public string DisplayName => ConnectorId.StartsWith("gmail:")
        ? $"Gmail · {AccountId}"
        : Source switch
        {
            "line_official_webhook" => "LINE 官方帳號（企業）",
            "messenger_page_webhook" => "Messenger 粉絲專頁（企業）",
            _ => "Windows 通知"
        };
    public string Initial => ConnectorId.StartsWith("gmail") ? "G" : Source switch
    {
        "line_official_webhook" => "L",
        "messenger_page_webhook" => "M",
        _ => "W"
    };
    public string BadgeSource => ConnectorId.StartsWith("gmail") ? "gmail" : Source switch
    {
        "line_official_webhook" => "line_notification",
        "messenger_page_webhook" => "messenger_notification",
        _ => "windows_notification"
    };
    public bool IsHealthy => Status == "healthy";
    public bool IsGmail => ConnectorId.StartsWith("gmail:");
    public bool IsBusinessWebhook => Capabilities.Contains("receive_webhook");
    public bool CanSync => IsGmail && IsHealthy;
    public string ConfigureLabel => IsGmail
        ? "連接 / 設定"
        : ConnectorId == "windows-notifications" ? "檢查通知權限" : "企業整合說明";
    public string StatusLabel => IsBusinessWebhook && Status == "not_configured"
        ? "企業選用"
        : Status switch
        {
            "healthy" => "已連線",
            "not_configured" => "未設定",
            "degraded" => "需要處理",
            "denied" => "權限未開啟",
            "error" => "發生錯誤",
            _ => Status
        };
    public string DetailLabel => Detail switch
    {
        "Add Google Desktop OAuth credentials.json to connect" =>
            "尚未提供 Google Desktop OAuth credentials.json。",
        "Add LINE channel secret" =>
            "只有經營 LINE 官方帳號才需要 Channel Secret；個人 LINE 聊天不必設定。",
        "Add Meta app secret and verify token" =>
            "只有經營 Messenger 粉絲專頁才需要 Meta Token；個人聊天不必設定。",
        "Waiting for Windows shell permission and bridge" =>
            "等待 Windows 通知權限與本機訊息橋接完成。",
        "Windows notification bridge connected" =>
            "通知同步已啟用；新的 LINE／Messenger 通知會自動整理。",
        "Windows notification access denied" =>
            "通知存取已被拒絕；請按下方按鈕重新檢查或開啟 Windows 設定。",
        "Windows notification permission not decided" =>
            "尚未決定通知存取權限；請按下方按鈕讓 Windows 顯示授權要求。",
        "Windows notification bridge failed" =>
            "通知橋接啟動失敗；請重新檢查權限。",
        "OAuth not completed" => "尚未完成 Google OAuth 授權。",
        "Gmail connected" => "Gmail 已完成安全連線。",
        _ => Detail ?? "等待設定"
    };
}

public sealed class ModelStatus
{
    public string Backend { get; set; } = "rule";
    public string Id { get; set; } = "";
    public string Status { get; set; } = "";
}

public sealed class ChatArchiveImportResult
{
    public string Source { get; set; } = "";
    public int Files { get; set; }
    public int Parsed { get; set; }
    public int Imported { get; set; }
    public int Duplicates { get; set; }
    public int Skipped { get; set; }
    public int Conversations { get; set; }
    public int CardsUpdated { get; set; }
    public List<string> Warnings { get; set; } = [];
}

public sealed class PrivacyStatus
{
    public bool LocalOnly { get; set; }
    public bool AutoSend { get; set; }
}

public sealed class RuleListResponse
{
    public List<RuleItem> Items { get; set; } = [];
}

public sealed class RuleItem
{
    public string RuleId { get; set; } = "";
    public string Kind { get; set; } = "";
    public string Pattern { get; set; } = "";
    public string? Value { get; set; }
    public bool Enabled { get; set; }
    public string KindLabel => Kind switch
    {
        "vip_sender" => "重要寄件者",
        "mute_sender" => "靜音寄件者",
        "mute_category" => "靜音類別",
        _ => "提高優先"
    };
}

public sealed class DigestResponse
{
    public List<CardItem> Urgent { get; set; } = [];
    public List<CardItem> DueToday { get; set; } = [];
    public List<CardItem> NeedsReply { get; set; } = [];
    public List<CardItem> ForInformation { get; set; } = [];
    public List<ConnectorItem> ConnectorIssues { get; set; } = [];
    public DigestCounts Counts { get; set; } = new();
    public string GeneratedAt { get; set; } = "";
}

public sealed class DigestCounts
{
    public int Urgent { get; set; }
    public int DueToday { get; set; }
    public int NeedsReply { get; set; }
    public int ForInformation { get; set; }
}

public sealed class UserPreferences
{
    public string Theme { get; set; } = "system";
    public bool FocusMode { get; set; }
    public bool ShadowMode { get; set; } = true;
    public bool OnboardingComplete { get; set; }
    public string QuietStart { get; set; } = "23:00";
    public string QuietEnd { get; set; } = "08:00";
    public string ModelResidency { get; set; } = "always_on";
    public int RawRetentionDays { get; set; } = 7;
    public string DigestTime { get; set; } = "18:00";
    public int FocusDigestMinutes { get; set; } = 60;
    public List<string> NotificationAllowlist { get; set; } = [];

    public static UserPreferences From(Dictionary<string, JsonElement> values) => new()
    {
        Theme = Text(values, "theme", "system"),
        FocusMode = Flag(values, "focus_mode"),
        ShadowMode = Flag(values, "shadow_mode", true),
        OnboardingComplete = Flag(values, "onboarding_complete"),
        QuietStart = Text(values, "quiet_start", "23:00"),
        QuietEnd = Text(values, "quiet_end", "08:00"),
        ModelResidency = Text(values, "model_residency", "always_on"),
        RawRetentionDays = Number(values, "raw_retention_days", 7),
        DigestTime = Text(values, "digest_time", "18:00"),
        FocusDigestMinutes = Number(values, "focus_digest_minutes", 60),
        NotificationAllowlist = TextList(values, "notification_allowlist")
    };

    private static string Text(Dictionary<string, JsonElement> values, string key, string fallback) =>
        values.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? fallback : fallback;
    private static bool Flag(Dictionary<string, JsonElement> values, string key, bool fallback = false) =>
        values.TryGetValue(key, out var value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? value.GetBoolean() : fallback;
    private static int Number(Dictionary<string, JsonElement> values, string key, int fallback) =>
        values.TryGetValue(key, out var value) && value.TryGetInt32(out var number) ? number : fallback;
    private static List<string> TextList(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.Array
            ? value.EnumerateArray()
                .Where(item => item.ValueKind == JsonValueKind.String)
                .Select(item => item.GetString() ?? "")
                .Where(item => item.Length > 0)
                .ToList()
            : [];
}
