using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using SignalDesk.Shell.Models;

namespace SignalDesk.Shell.Services;

public sealed class LocalApiClient
{
    private readonly HttpClient _client;
    private readonly JsonSerializerOptions _json = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true
    };

    public LocalApiClient(Uri baseUri, string token)
    {
        if (!baseUri.IsLoopback) throw new ArgumentException("SignalDesk API must be loopback-only.");
        _client = new HttpClient { BaseAddress = baseUri, Timeout = TimeSpan.FromMinutes(20) };
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
    }

    public Task<BootstrapResponse> BootstrapAsync(CancellationToken token = default) =>
        GetAsync<BootstrapResponse>("api/v1/bootstrap", token);

    public Task<CardListResponse> CardsAsync(
        string view, string search = "", string source = "", string priority = "",
        string date = "",
        CancellationToken token = default)
    {
        var query = $"view={Uri.EscapeDataString(view)}&search={Uri.EscapeDataString(search)}" +
                    $"&source={Uri.EscapeDataString(source)}&priority={Uri.EscapeDataString(priority)}" +
                    $"&date={Uri.EscapeDataString(date)}&limit=500";
        return GetAsync<CardListResponse>($"api/v1/cards?{query}", token);
    }

    public Task<CardDetail> CardAsync(string cardId, CancellationToken token = default) =>
        GetAsync<CardDetail>($"api/v1/cards/{Uri.EscapeDataString(cardId)}", token);

    public async Task<byte[]> MediaAsync(string assetId, CancellationToken token = default)
    {
        using var response = await _client.GetAsync(
            $"api/v1/media/{Uri.EscapeDataString(assetId)}", token);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsByteArrayAsync(token);
    }

    public Task<JsonElement> CardActionAsync(
        string cardId, string action, object? value = null, CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post, $"api/v1/cards/{Uri.EscapeDataString(cardId)}/actions",
            new { action, value }, token);

    public Task<DigestResponse> DigestAsync(CancellationToken token = default) =>
        GetAsync<DigestResponse>("api/v1/digest", token);

    public Task<RuleListResponse> RulesAsync(CancellationToken token = default) =>
        GetAsync<RuleListResponse>("api/v1/rules", token);

    public Task<JsonElement> CreateRuleAsync(
        string kind, string pattern, CancellationToken token = default) =>
        SendAsync<JsonElement>(HttpMethod.Post, "api/v1/rules", new { kind, pattern }, token);

    public async Task DeleteRuleAsync(string ruleId, CancellationToken token = default) =>
        await SendAsync<JsonElement>(
            HttpMethod.Delete, $"api/v1/rules/{Uri.EscapeDataString(ruleId)}", null, token);

    public Task<Dictionary<string, JsonElement>> UpdateSettingsAsync(
        object patch, CancellationToken token = default) =>
        SendAsync<Dictionary<string, JsonElement>>(
            HttpMethod.Patch, "api/v1/settings", patch, token);

    public Task<JsonElement> AddGmailAccountAsync(
        string accountId, string? credentialsPath, bool draftScope,
        CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post, "api/v1/connectors/gmail/accounts",
            new { account_id = accountId, credentials_path = credentialsPath, draft_scope = draftScope },
            token);

    public Task<JsonElement> ConfigureGmailAccountAsync(
        string accountId, string? credentialsPath, bool draftScope,
        CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Patch,
            $"api/v1/connectors/gmail/accounts/{Uri.EscapeDataString(accountId)}",
            new { credentials_path = credentialsPath, draft_scope = draftScope },
            token);

    public Task<JsonElement> ConnectGmailAsync(
        string accountId = "personal", CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post,
            $"api/v1/connectors/gmail/connect?account_id={Uri.EscapeDataString(accountId)}",
            null, token);

    public Task<JsonElement> SyncGmailAsync(
        string accountId = "personal", CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post,
            $"api/v1/connectors/gmail/sync?account_id={Uri.EscapeDataString(accountId)}",
            null, token);

    public Task<JsonElement> DisconnectGmailAsync(
        string accountId, CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Delete,
            $"api/v1/connectors/gmail?account_id={Uri.EscapeDataString(accountId)}",
            null, token);

    public Task<JsonElement> RemoveGmailAccountAsync(
        string accountId, CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Delete,
            $"api/v1/connectors/gmail/accounts/{Uri.EscapeDataString(accountId)}",
            null, token);

    public Task<ChatArchiveImportResult> ImportChatArchivesAsync(
        string source, IReadOnlyList<string> paths, CancellationToken token = default) =>
        SendAsync<ChatArchiveImportResult>(
            HttpMethod.Post,
            "api/v1/connectors/chat-archives/import",
            new { source, paths },
            token);

    public Task<JsonElement> CreateGmailDraftAsync(
        string draftId, CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post, $"api/v1/drafts/{Uri.EscapeDataString(draftId)}/gmail",
            new { confirmation = "CREATE GMAIL DRAFT" }, token);

    public Task<JsonElement> ResetPreferencesAsync(CancellationToken token = default) =>
        SendAsync<JsonElement>(HttpMethod.Post, "api/v1/preferences/reset", null, token);

    public Task<JsonElement> SeedDemoAsync(CancellationToken token = default) =>
        SendAsync<JsonElement>(HttpMethod.Post, "api/v1/demo/seed", null, token);

    public Task<JsonElement> PrivacyExportAsync(CancellationToken token = default) =>
        GetAsync<JsonElement>("api/v1/privacy/export", token);

    public Task<JsonElement> DeletePrivateDataAsync(CancellationToken token = default) =>
        SendAsync<JsonElement>(
            HttpMethod.Post, "api/v1/privacy/delete",
            new { confirmation = "DELETE MY SIGNALDESK DATA" }, token);

    public async Task PostNotificationAsync(
        object payload, CancellationToken cancellationToken = default) =>
        await SendAsync<JsonElement>(
            HttpMethod.Post, "api/v1/connectors/windows/notifications", payload, cancellationToken);

    public async Task PostNotificationStatusAsync(
        string status, string? detail = null,
        CancellationToken cancellationToken = default) =>
        await SendAsync<JsonElement>(
            HttpMethod.Post, "api/v1/connectors/windows/status",
            new { status, detail }, cancellationToken);

    public async Task<bool> IsHealthyAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            // Use an authenticated endpoint so another process on the fixed loopback
            // port cannot be mistaken for this user's SignalDesk service.
            using var response = await _client.GetAsync("api/v1/bootstrap", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch (HttpRequestException)
        {
            return false;
        }
    }

    public async Task WatchEventsAsync(
        Func<string, JsonElement, Task> handler, CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Get, "api/v1/events/stream");
                using var response = await _client.SendAsync(
                    request, HttpCompletionOption.ResponseHeadersRead, token);
                response.EnsureSuccessStatusCode();
                await using var stream = await response.Content.ReadAsStreamAsync(token);
                using var reader = new StreamReader(stream);
                string eventName = "message";
                while (!token.IsCancellationRequested)
                {
                    var line = await reader.ReadLineAsync(token);
                    if (line is null) break;
                    if (line.StartsWith("event: ")) eventName = line[7..];
                    if (line.StartsWith("data: "))
                    {
                        using var document = JsonDocument.Parse(line[6..]);
                        await handler(eventName, document.RootElement.Clone());
                    }
                }
            }
            catch (Exception) when (!token.IsCancellationRequested)
            {
                await Task.Delay(TimeSpan.FromSeconds(2), token);
            }
        }
    }

    private async Task<T> GetAsync<T>(string path, CancellationToken token)
    {
        using var response = await _client.GetAsync(path, token);
        return await ReadAsync<T>(response, token);
    }

    private async Task<T> SendAsync<T>(
        HttpMethod method, string path, object? body, CancellationToken token)
    {
        using var request = new HttpRequestMessage(method, path);
        if (body is not null)
        {
            var content = JsonSerializer.Serialize(body, _json);
            request.Content = new StringContent(content, Encoding.UTF8, "application/json");
        }
        using var response = await _client.SendAsync(request, token);
        return await ReadAsync<T>(response, token);
    }

    private async Task<T> ReadAsync<T>(HttpResponseMessage response, CancellationToken token)
    {
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync(token);
            try
            {
                using var parsed = JsonDocument.Parse(error);
                error = parsed.RootElement.GetProperty("detail").GetString() ?? error;
            }
            catch (JsonException) { }
            throw new InvalidOperationException(error);
        }
        var result = await response.Content.ReadFromJsonAsync<T>(_json, token);
        return result ?? throw new InvalidOperationException("SignalDesk returned an empty response.");
    }
}
