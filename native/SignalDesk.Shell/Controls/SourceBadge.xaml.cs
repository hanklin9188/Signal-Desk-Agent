using Microsoft.UI;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Automation;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Windows.UI;

namespace SignalDesk.Shell.Controls;

public sealed partial class SourceBadge : UserControl
{
    public static readonly DependencyProperty SourceProperty = DependencyProperty.Register(
        nameof(Source), typeof(string), typeof(SourceBadge),
        new PropertyMetadata("", OnVisualPropertyChanged));

    public static readonly DependencyProperty BadgeSizeProperty = DependencyProperty.Register(
        nameof(BadgeSize), typeof(double), typeof(SourceBadge),
        new PropertyMetadata(40d, OnVisualPropertyChanged));

    public string Source
    {
        get => (string)GetValue(SourceProperty);
        set => SetValue(SourceProperty, value);
    }

    public double BadgeSize
    {
        get => (double)GetValue(BadgeSizeProperty);
        set => SetValue(BadgeSizeProperty, value);
    }

    public SourceBadge()
    {
        InitializeComponent();
        UpdateVisual();
    }

    private static void OnVisualPropertyChanged(
        DependencyObject sender, DependencyPropertyChangedEventArgs args)
    {
        if (sender is SourceBadge badge) badge.UpdateVisual();
    }

    private void UpdateVisual()
    {
        if (Badge is null || SourceIcon is null) return;
        var key = (Source ?? "").ToLowerInvariant();
        var (glyph, color, label) = key switch
        {
            "gmail" => ("\uE715", Color.FromArgb(255, 234, 67, 53), "Gmail"),
            "line_notification" or "line_official_webhook" =>
                ("\uE8BD", Color.FromArgb(255, 6, 199, 85), "LINE"),
            "messenger_notification" or "messenger_page_webhook" =>
                ("\uE724", Color.FromArgb(255, 22, 138, 255), "Messenger"),
            "windows_notification" =>
                ("\uE782", Color.FromArgb(255, 76, 194, 255), "Windows"),
            _ => ("\uE8A5", Colors.MediumPurple, "SignalDesk")
        };
        Badge.Width = BadgeSize;
        Badge.Height = BadgeSize;
        Badge.CornerRadius = new CornerRadius(Math.Max(9, BadgeSize * 0.31));
        Badge.Background = new SolidColorBrush(
            Color.FromArgb(31, color.R, color.G, color.B));
        Badge.BorderBrush = new SolidColorBrush(
            Color.FromArgb(42, color.R, color.G, color.B));
        Badge.BorderThickness = new Thickness(1);
        SourceIcon.Glyph = glyph;
        SourceIcon.FontSize = Math.Max(14, BadgeSize * 0.42);
        SourceIcon.Foreground = new SolidColorBrush(color);
        ToolTipService.SetToolTip(this, label);
        AutomationProperties.SetName(this, $"{label} 訊息來源");
    }
}
