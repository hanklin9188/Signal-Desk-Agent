using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
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
        var runtimeRoot = Path.Combine(localData, "model-runtime");
        var runtimePython = Path.Combine(runtimeRoot, ".venv", "Scripts", "python.exe");
        var runtimeConfig = ReadRuntimeConfig(Path.Combine(runtimeRoot, "runtime.json"));
        var useModelRuntime = File.Exists(runtimePython) && runtimeConfig.Count > 0;

        _process = StartService(
            useModelRuntime ? runtimePython : packagedService,
            useModelRuntime,
            token,
            localData,
            runtimeConfig);
        if (await WaitUntilHealthyAsync(client, _process))
            return new LocalSession(BaseUri, token);

        // A damaged optional model environment must never prevent the desktop app
        // from opening. Fall back to the signed packaged rule service and leave the
        // runtime files intact for diagnostics or repair.
        if (useModelRuntime)
        {
            StopProcess(_process);
            _process = StartService(
                packagedService,
                false,
                token,
                localData,
                new Dictionary<string, string>());
            if (await WaitUntilHealthyAsync(client, _process))
                return new LocalSession(BaseUri, token);
        }
        throw new InvalidOperationException("SignalDesk local service did not become ready.");
    }

    private static Process StartService(
        string executable,
        bool modelRuntime,
        string token,
        string localData,
        IReadOnlyDictionary<string, string> runtimeConfig)
    {
        ProcessStartInfo start;
        if (modelRuntime)
        {
            start = new ProcessStartInfo(executable);
            start.ArgumentList.Add("-m");
            start.ArgumentList.Add("signaldesk.main");
        }
        else if (File.Exists(executable))
        {
            start = new ProcessStartInfo(executable);
        }
        else
        {
            start = new ProcessStartInfo("python", "-m signaldesk.main");
        }
        start.UseShellExecute = false;
        start.CreateNoWindow = true;
        start.Environment["SIGNALDESK_AUTH_TOKEN"] = token;
        start.Environment["SIGNALDESK_DATABASE"] = Path.Combine(localData, "signaldesk.db");
        if (modelRuntime)
        {
            start.Environment["HF_HOME"] = Path.Combine(localData, "models");
            start.Environment["HF_HUB_DISABLE_TELEMETRY"] = "1";
            foreach (var (key, value) in runtimeConfig)
                start.Environment[key] = value;
        }
        return Process.Start(start) ?? throw new InvalidOperationException("Could not start service.");
    }

    private static async Task<bool> WaitUntilHealthyAsync(LocalApiClient client, Process process)
    {
        for (var attempt = 0; attempt < 80; attempt++)
        {
            await Task.Delay(250);
            if (await client.IsHealthyAsync()) return true;
            if (process.HasExited) break;
        }
        return false;
    }

    private static Dictionary<string, string> ReadRuntimeConfig(string path)
    {
        try
        {
            if (!File.Exists(path)) return [];
            return JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(path))
                   ?? [];
        }
        catch (JsonException)
        {
            return [];
        }
    }

    private static void StopProcess(Process process)
    {
        try
        {
            if (!process.HasExited) process.Kill(entireProcessTree: true);
        }
        catch (InvalidOperationException) { }
        finally { process.Dispose(); }
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
        StopProcess(_process);
    }
}
