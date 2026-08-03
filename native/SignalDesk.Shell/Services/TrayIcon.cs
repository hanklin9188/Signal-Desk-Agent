using System.Runtime.InteropServices;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using WinRT.Interop;

namespace SignalDesk.Shell.Services;

public sealed class TrayIcon : IDisposable
{
    private const uint NimAdd = 0x00000000;
    private const uint NimDelete = 0x00000002;
    private const uint NimModify = 0x00000001;
    private const uint NifMessage = 0x00000001;
    private const uint NifIcon = 0x00000002;
    private const uint NifTip = 0x00000004;
    private const uint NifInfo = 0x00000010;
    private const uint WmApp = 0x8000;
    private const uint WmLeftButtonUp = 0x0202;
    private const uint WmRightButtonUp = 0x0205;
    private const uint IdiApplication = 32512;

    private readonly IntPtr _window;
    private readonly DispatcherQueue _dispatcher;
    private readonly Action _activate;
    private readonly Action _exit;
    private readonly SubclassProc _subclass;
    private NotifyIconData _data;

    public TrayIcon(Window window, Action activate, Action exit)
    {
        _window = WindowNative.GetWindowHandle(window);
        _dispatcher = window.DispatcherQueue;
        _activate = activate;
        _exit = exit;
        _subclass = WindowSubclass;
        SetWindowSubclass(_window, _subclass, 1, UIntPtr.Zero);
        _data = new NotifyIconData
        {
            cbSize = Marshal.SizeOf<NotifyIconData>(),
            hWnd = _window,
            uID = 1,
            uFlags = NifMessage | NifIcon | NifTip,
            uCallbackMessage = WmApp + 1,
            hIcon = LoadIcon(IntPtr.Zero, new IntPtr(IdiApplication)),
            szTip = "SignalDesk — 本機訊息重點",
            szInfo = string.Empty,
            szInfoTitle = string.Empty
        };
        ShellNotifyIcon(NimAdd, ref _data);
    }

    private IntPtr WindowSubclass(
        IntPtr window, uint message, IntPtr wParam, IntPtr lParam, UIntPtr id, UIntPtr data)
    {
        if (message == WmApp + 1 && (uint)lParam.ToInt64() == WmLeftButtonUp)
            _dispatcher.TryEnqueue(() => _activate());
        else if (message == WmApp + 1 && (uint)lParam.ToInt64() == WmRightButtonUp)
            ShowContextMenu();
        return DefSubclassProc(window, message, wParam, lParam);
    }

    private void ShowContextMenu()
    {
        if (!GetCursorPos(out var point)) return;
        var menu = CreatePopupMenu();
        if (menu == IntPtr.Zero) return;
        try
        {
            AppendMenu(menu, 0, 1, "開啟 SignalDesk");
            AppendMenu(menu, 0, 2, "結束 SignalDesk");
            SetForegroundWindow(_window);
            var command = TrackPopupMenu(menu, 0x0102, point.X, point.Y, 0, _window, IntPtr.Zero);
            if (command == 1) _dispatcher.TryEnqueue(() => _activate());
            if (command == 2) _dispatcher.TryEnqueue(() => _exit());
        }
        finally { DestroyMenu(menu); }
    }

    public void ShowNotification(string title, string message) => _dispatcher.TryEnqueue(() =>
    {
        _data.uFlags = NifMessage | NifIcon | NifTip | NifInfo;
        _data.szInfoTitle = title.Length > 63 ? title[..63] : title;
        _data.szInfo = message.Length > 255 ? message[..255] : message;
        _data.dwInfoFlags = 1;
        ShellNotifyIcon(NimModify, ref _data);
        _data.uFlags = NifMessage | NifIcon | NifTip;
    });

    public void Dispose()
    {
        ShellNotifyIcon(NimDelete, ref _data);
        RemoveWindowSubclass(_window, _subclass, 1);
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct NotifyIconData
    {
        public int cbSize;
        public IntPtr hWnd;
        public uint uID;
        public uint uFlags;
        public uint uCallbackMessage;
        public IntPtr hIcon;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string szTip;
        public uint dwState;
        public uint dwStateMask;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)] public string szInfo;
        public uint uTimeoutOrVersion;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string szInfoTitle;
        public uint dwInfoFlags;
        public Guid guidItem;
        public IntPtr hBalloonIcon;
    }

    private delegate IntPtr SubclassProc(
        IntPtr window, uint message, IntPtr wParam, IntPtr lParam, UIntPtr id, UIntPtr data);

    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    private static extern bool Shell_NotifyIcon(uint message, ref NotifyIconData data);
    private static bool ShellNotifyIcon(uint message, ref NotifyIconData data) =>
        Shell_NotifyIcon(message, ref data);

    [DllImport("user32.dll")]
    private static extern IntPtr LoadIcon(IntPtr instance, IntPtr iconName);
    [DllImport("comctl32.dll")]
    private static extern bool SetWindowSubclass(
        IntPtr window, SubclassProc callback, uint id, UIntPtr data);
    [DllImport("comctl32.dll")]
    private static extern bool RemoveWindowSubclass(IntPtr window, SubclassProc callback, uint id);
    [DllImport("comctl32.dll")]
    private static extern IntPtr DefSubclassProc(
        IntPtr window, uint message, IntPtr wParam, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    private struct Point { public int X; public int Y; }
    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out Point point);
    [DllImport("user32.dll")]
    private static extern IntPtr CreatePopupMenu();
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern bool AppendMenu(IntPtr menu, uint flags, nuint id, string text);
    [DllImport("user32.dll")]
    private static extern uint TrackPopupMenu(
        IntPtr menu, uint flags, int x, int y, int reserved, IntPtr window, IntPtr rectangle);
    [DllImport("user32.dll")]
    private static extern bool DestroyMenu(IntPtr menu);
    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr window);
}
