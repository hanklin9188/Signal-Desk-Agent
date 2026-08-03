using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SignalDesk.Shell.Models;
using SignalDesk.Shell.Services;

namespace SignalDesk.Shell.Views;

public sealed partial class RulesPage : UserControl, IAsyncPage
{
    private readonly AppState _state;
    public ObservableCollection<RuleItem> Rules { get; } = [];
    public RulesPage(AppState state) { _state = state; InitializeComponent(); }

    public async Task LoadAsync()
    {
        var response = await _state.Api.RulesAsync();
        Rules.Clear(); foreach (var item in response.Items) Rules.Add(item);
        RuleEmptyState.Visibility = Rules.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        RuleList.Visibility = Rules.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
    }

    private async void Create_Click(object sender, RoutedEventArgs e)
    {
        var pattern = RulePattern.Text.Trim();
        var kind = (RuleKind.SelectedItem as ComboBoxItem)?.Tag?.ToString();
        if (string.IsNullOrEmpty(pattern) || string.IsNullOrEmpty(kind)) return;
        try { await _state.Api.CreateRuleAsync(kind, pattern); RulePattern.Text = ""; await LoadAsync(); }
        catch (Exception error) { Show(error.Message); }
    }

    private async void Delete_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: string id }) return;
        try { await _state.Api.DeleteRuleAsync(id); await LoadAsync(); }
        catch (Exception error) { Show(error.Message); }
    }

    private static void Show(string message) =>
        ((App)Application.Current).ShowMessage("規則操作失敗", message, InfoBarSeverity.Error);
}
