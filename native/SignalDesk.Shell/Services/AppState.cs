using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using SignalDesk.Shell.Models;

namespace SignalDesk.Shell.Services;

public sealed class AppState : INotifyPropertyChanged, IDisposable
{
    private readonly SemaphoreSlim _refreshLock = new(1, 1);
    private readonly CancellationTokenSource _watcher = new();
    private CardCounts _counts = new();
    private UserPreferences _preferences = new();
    private ModelStatus _model = new();

    public AppState(LocalApiClient api) => Api = api;

    public LocalApiClient Api { get; }
    public ObservableCollection<CardItem> Cards { get; } = [];
    public ObservableCollection<ConnectorItem> Connectors { get; } = [];
    public CardCounts Counts { get => _counts; private set => Set(ref _counts, value); }
    public UserPreferences Preferences { get => _preferences; private set => Set(ref _preferences, value); }
    public ModelStatus Model { get => _model; private set => Set(ref _model, value); }
    public string CurrentView { get; private set; } = "now";
    public string Search { get; private set; } = "";
    public string CurrentSource { get; private set; } = "";
    public string CurrentPriority { get; private set; } = "";
    public string CurrentDate { get; private set; } = "";
    public event PropertyChangedEventHandler? PropertyChanged;
    public event EventHandler? Refreshed;
    public event EventHandler<JsonElement>? ReminderDue;
    public event EventHandler<JsonElement>? DigestReady;

    public async Task InitializeAsync()
    {
        var data = await Api.BootstrapAsync();
        ApplyBootstrap(data);
    }

    public async Task LoadCardsAsync(
        string view, string search = "", string source = "", string priority = "",
        string date = "")
    {
        await _refreshLock.WaitAsync();
        try
        {
            CurrentView = view;
            Search = search;
            CurrentSource = source;
            CurrentPriority = priority;
            CurrentDate = date;
            var response = await Api.CardsAsync(view, search, source, priority, date);
            Replace(Cards, response.Items);
            Counts = response.Counts;
        }
        finally { _refreshLock.Release(); }
        Refreshed?.Invoke(this, EventArgs.Empty);
    }

    public async Task RefreshAsync()
    {
        var data = await Api.BootstrapAsync();
        Counts = data.Counts;
        Preferences = UserPreferences.From(data.Settings);
        Model = data.Model;
        Replace(Connectors, data.Connectors);
        await LoadCardsAsync(
            CurrentView, Search, CurrentSource, CurrentPriority, CurrentDate);
    }

    public void StartWatcher() => _ = Api.WatchEventsAsync(OnServerEventAsync, _watcher.Token);

    public async Task UpdateSettingsAsync(object patch)
    {
        var values = await Api.UpdateSettingsAsync(patch);
        Preferences = UserPreferences.From(values);
        Refreshed?.Invoke(this, EventArgs.Empty);
    }

    private Task OnServerEventAsync(string eventName, JsonElement message)
    {
        if (eventName == "reminder_due") ReminderDue?.Invoke(this, message);
        else if (eventName == "digest_ready") DigestReady?.Invoke(this, message);
        else if (eventName is "card_updated" or "connector_health" or "settings_updated" or "data_deleted")
            _ = RefreshAsync();
        return Task.CompletedTask;
    }

    private void ApplyBootstrap(BootstrapResponse data)
    {
        Replace(Cards, data.Cards);
        Replace(Connectors, data.Connectors);
        Counts = data.Counts;
        Preferences = UserPreferences.From(data.Settings);
        Model = data.Model;
    }

    private static void Replace<T>(ObservableCollection<T> target, IEnumerable<T> source)
    {
        target.Clear();
        foreach (var item in source) target.Add(item);
    }

    private void Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }

    public void Dispose()
    {
        _watcher.Cancel();
        _watcher.Dispose();
        _refreshLock.Dispose();
    }
}
