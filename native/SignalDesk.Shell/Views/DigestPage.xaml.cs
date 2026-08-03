using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using SignalDesk.Shell.Models;
using SignalDesk.Shell.Services;

namespace SignalDesk.Shell.Views;

public sealed partial class DigestPage : UserControl, IAsyncPage
{
    private readonly AppState _state;
    public DigestResponse Digest { get; private set; } = new();

    public DigestPage(AppState state)
    {
        _state = state;
        InitializeComponent();
    }

    public async Task LoadAsync()
    {
        Digest = await _state.Api.DigestAsync();
        Bindings.Update();
        UrgentEmpty.Visibility = Digest.Urgent.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        UrgentList.Visibility = Digest.Urgent.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
        ImportantEmpty.Visibility = Digest.Important.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        ImportantList.Visibility = Digest.Important.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
        DueEmpty.Visibility = Digest.DueToday.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        DueList.Visibility = Digest.DueToday.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
        ReplyEmpty.Visibility = Digest.NeedsReply.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        ReplyList.Visibility = Digest.NeedsReply.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
        InformationEmpty.Visibility = Digest.ForInformation.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        InformationList.Visibility = Digest.ForInformation.Count == 0 ? Visibility.Collapsed : Visibility.Visible;
        DigestScroll.UpdateLayout();
        DigestScroll.ChangeView(null, 0, null, true);
    }

    private async void Refresh_Click(object sender, RoutedEventArgs e) => await LoadAsync();

    private async void DigestItem_Click(object sender, ItemClickEventArgs e)
    {
        if (e.ClickedItem is CardItem card) await ((App)Application.Current).OpenCardAsync(card.CardId);
    }
}
