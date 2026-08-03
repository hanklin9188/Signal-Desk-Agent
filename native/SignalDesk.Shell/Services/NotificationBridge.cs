using Windows.UI.Notifications;
using Windows.UI.Notifications.Management;

namespace SignalDesk.Shell.Services;

public sealed class NotificationBridge : IDisposable
{
    private readonly LocalApiClient _api;
    private readonly UserNotificationListener _listener = UserNotificationListener.Current;
    private readonly Dictionary<uint, string> _observed = new();
    private readonly SemaphoreSlim _reconcileGate = new(1, 1);
    private CancellationTokenSource? _pollCancellation;
    private Task? _pollTask;
    private bool _listening;

    public NotificationBridge(LocalApiClient api) => _api = api;

    public async Task<UserNotificationListenerAccessStatus> StartAsync()
    {
        try
        {
            var access = await _listener.RequestAccessAsync();
            await _api.PostNotificationStatusAsync(access switch
            {
                UserNotificationListenerAccessStatus.Allowed => "allowed",
                UserNotificationListenerAccessStatus.Denied => "denied",
                _ => "unspecified"
            });
            if (access != UserNotificationListenerAccessStatus.Allowed) return access;
            if (!_listening)
            {
                _listener.NotificationChanged += OnNotificationChanged;
                _listening = true;
            }
            await ReconcileAsync("startup_reconcile");
            EnsurePolling();
            return access;
        }
        catch (Exception error)
        {
            await _api.PostNotificationStatusAsync("error", error.Message);
            throw;
        }
    }

    private async void OnNotificationChanged(
        UserNotificationListener sender, UserNotificationChangedEventArgs args)
    {
        if (args.ChangeKind == UserNotificationChangedKind.Removed)
        {
            _observed.Remove(args.UserNotificationId);
            return;
        }
        if (args.ChangeKind != UserNotificationChangedKind.Added) return;
        try
        {
            // Some apps publish the notification shell before its ToastGeneric text is
            // available. A short delay plus reconciliation avoids permanently missing it.
            await Task.Delay(TimeSpan.FromMilliseconds(350));
            var notifications = await sender.GetNotificationsAsync(NotificationKinds.Toast);
            var notification = notifications.FirstOrDefault(item => item.Id == args.UserNotificationId);
            if (notification is not null)
                await ForwardAsync(notification, "live");
            else
                await ReconcileAsync("event_reconcile");
        }
        catch (Exception error)
        {
            System.Diagnostics.Debug.WriteLine($"Notification bridge: {error}");
        }
    }

    private void EnsurePolling()
    {
        if (_pollTask is { IsCompleted: false }) return;
        _pollCancellation?.Dispose();
        _pollCancellation = new CancellationTokenSource();
        _pollTask = PollNotificationsAsync(_pollCancellation.Token);
    }

    private async Task PollNotificationsAsync(CancellationToken cancellationToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(15));
        try
        {
            while (await timer.WaitForNextTickAsync(cancellationToken))
            {
                try { await ReconcileAsync("poll", cancellationToken); }
                catch (Exception error) when (error is not OperationCanceledException)
                {
                    System.Diagnostics.Debug.WriteLine($"Notification bridge poll: {error}");
                }
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { }
    }

    private async Task ReconcileAsync(
        string captureReason, CancellationToken cancellationToken = default)
    {
        await _reconcileGate.WaitAsync(cancellationToken);
        try
        {
            var notifications = await _listener.GetNotificationsAsync(NotificationKinds.Toast);
            foreach (var notification in notifications.OrderBy(item => item.CreationTime))
                await ForwardAsync(notification, captureReason);
        }
        finally { _reconcileGate.Release(); }
    }

    private async Task ForwardAsync(UserNotification notification, string captureReason)
    {
        var binding = notification.Notification.Visual.GetBinding(KnownNotificationBindings.ToastGeneric);
        var text = binding?.GetTextElements().Select(item => item.Text).ToArray() ?? Array.Empty<string>();
        var appName = notification.AppInfo?.DisplayInfo?.DisplayName ?? "Unknown app";
        var appId = notification.AppInfo?.AppUserModelId ?? appName;
        var fingerprint = string.Join("\u001f", appId, string.Join("\u001e", text));
        if (_observed.TryGetValue(notification.Id, out var previous) && previous == fingerprint) return;
        var attribution = text.FirstOrDefault(item =>
            item.Contains("messenger.com", StringComparison.OrdinalIgnoreCase) ||
            item.Contains("facebook.com", StringComparison.OrdinalIgnoreCase) ||
            item.Contains("line.me", StringComparison.OrdinalIgnoreCase));
        await _api.PostNotificationAsync(new
        {
            notification_id = notification.Id.ToString(),
            app_id = appId,
            app_name = appName,
            title = text.ElementAtOrDefault(0),
            sender = text.ElementAtOrDefault(0),
            body = string.Join("\n", text.Skip(1)),
            received_at = notification.CreationTime.ToString("O"),
            origin = attribution,
            metadata = new
            {
                visual_binding = "ToastGeneric",
                browser_origin_detected = attribution is not null,
                capture_reason = captureReason
            }
        });
        // Mark it only after forwarding succeeds, so a temporary failure can be retried.
        _observed[notification.Id] = fingerprint;
    }

    public void Dispose()
    {
        _pollCancellation?.Cancel();
        if (_listening) _listener.NotificationChanged -= OnNotificationChanged;
        _listening = false;
    }
}
