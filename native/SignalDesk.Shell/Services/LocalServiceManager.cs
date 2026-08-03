using System.Diagnostics;
using System.Security.Cryptography;
using Windows.Security.Credentials;

namespace SignalDesk.Shell.Services;

public sealed record LocalSession(Uri BaseUri, string Token);

public sealed class LocalServiceManager : IDisposable
{
    private static readonly Uri BaseUri = new("http://127.0.0.1:8765/");
    private const string VaultResource = "SignalDesk.LocalApi";
    private Process? _process;

    public async Task<LocalSession> EnsureRunningAsync()
    {
        var token = GetOrCreateToken();
        var client = new LocalApiClient(BaseUri, token);
        if (await client.IsHealthyAsync()) return new LocalSession(BaseUri, token);

        var localData = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SignalDesk");
        Directory.CreateDirectory(localData);

        var packagedService = Path.Combine(AppContext.BaseDirectory, "service", "signaldesk.exe");
        var start = File.Exists(packagedService)
            ? new ProcessStartInfo(packagedService)
            : new ProcessStartInfo("python", "-m signaldesk.main");
        start.UseShellExecute = false;
        start.CreateNoWindow = true;
        start.Environment["SIGNALDESK_AUTH_TOKEN"] = token;
        start.Environment["SIGNALDESK_DATABASE"] = Path.Combine(localData, "signaldesk.db");
        _process = Process.Start(start) ?? throw new InvalidOperationException("Could not start service.");

        for (var attempt = 0; attempt < 40; attempt++)
        {
            await Task.Delay(250);
            if (await client.IsHealthyAsync()) return new LocalSession(BaseUri, token);
            if (_process.HasExited) break;
        }
        throw new InvalidOperationException("SignalDesk local service did not become ready.");
    }

    private static string GetOrCreateToken()
    {
        var vault = new PasswordVault();
        try
        {
            var existing = vault.Retrieve(VaultResource, "loopback");
            existing.RetrievePassword();
            return existing.Password;
        }
        catch
        {
            var token = Convert.ToBase64String(RandomNumberGenerator.GetBytes(48));
            vault.Add(new PasswordCredential(VaultResource, "loopback", token));
            return token;
        }
    }

    public void Dispose()
    {
        if (_process is null || _process.HasExited) return;
        try { _process.Kill(entireProcessTree: true); }
        catch (InvalidOperationException) { }
        _process.Dispose();
    }
}
