using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Input;
using SignalDesk.Shell.Services;
using WinRT.Interop;
using System.Runtime.InteropServices;

namespace SignalDesk.Shell;

public sealed partial class OrbWindow : Window
{
    private readonly Action _openGlance;
    private readonly AppState _state;
    private readonly IntPtr _windowHandle;
    private bool _allowClose;

    public OrbWindow(AppState state, Action openGlance)
    {
        _state = state;
        _openGlance = openGlance;
        InitializeComponent();
        _windowHandle = WindowNative.GetWindowHandle(this);
        ExtendsContentIntoTitleBar = true;
        ConfigureOverlay();
        _state.Refreshed += State_Refreshed;
        UpdateCount();
    }

    private void ConfigureOverlay()
    {
        var windowId = Microsoft.UI.Win32Interop.GetWindowIdFromWindow(WindowNative.GetWindowHandle(this));
        var appWindow = AppWindow.GetFromWindowId(windowId);
        appWindow.Resize(new Windows.Graphics.SizeInt32(58, 58));
        if (appWindow.Presenter is OverlappedPresenter presenter)
        {
            presenter.IsAlwaysOnTop = true;
            presenter.IsResizable = false;
            presenter.IsMaximizable = false;
            presenter.IsMinimizable = false;
            presenter.SetBorderAndTitleBar(false, false);
        }

        var display = DisplayArea.GetFromWindowId(windowId, DisplayAreaFallback.Primary);
        var x = display.WorkArea.X + display.WorkArea.Width - 82;
        var y = display.WorkArea.Y + display.WorkArea.Height - 82;
        appWindow.Move(new Windows.Graphics.PointInt32(x, y));
        appWindow.Closing += (_, args) =>
        {
            if (!_allowClose) args.Cancel = true;
        };
    }

    private void OpenButton_Click(object sender, RoutedEventArgs e) => _openGlance();

    private void State_Refreshed(object? sender, EventArgs e) =>
        DispatcherQueue.TryEnqueue(UpdateCount);

    private void UpdateCount()
    {
        var count = _state.Counts.Important;
        CountText.Text = count > 99 ? "99+" : count.ToString();
        CountBadge.Visibility = count > 0 ? Visibility.Visible : Visibility.Collapsed;
    }

    private void DragSurface_PointerPressed(object sender, PointerRoutedEventArgs e)
    {
        if (!e.GetCurrentPoint(null).Properties.IsLeftButtonPressed) return;
        ReleaseCapture();
        SendMessage(_windowHandle, 0x00A1, new IntPtr(2), IntPtr.Zero);
    }

    [DllImport("user32.dll")]
    private static extern bool ReleaseCapture();
    [DllImport("user32.dll")]
    private static extern IntPtr SendMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);

    public void CloseForExit()
    {
        _allowClose = true;
        Close();
    }
}
