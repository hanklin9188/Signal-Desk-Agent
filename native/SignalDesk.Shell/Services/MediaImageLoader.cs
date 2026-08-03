using Microsoft.UI.Xaml.Media.Imaging;
using Windows.Storage.Streams;

namespace SignalDesk.Shell.Services;

public static class MediaImageLoader
{
    public static async Task<BitmapImage> FromBytesAsync(byte[] bytes)
    {
        using var stream = new InMemoryRandomAccessStream();
        using (var writer = new DataWriter(stream))
        {
            writer.WriteBytes(bytes);
            await writer.StoreAsync();
            writer.DetachStream();
        }
        stream.Seek(0);
        var bitmap = new BitmapImage();
        await bitmap.SetSourceAsync(stream);
        return bitmap;
    }

    public static async Task LoadThumbnailsAsync(
        LocalApiClient api,
        IEnumerable<Models.CardItem> cards,
        int limit,
        CancellationToken token = default)
    {
        foreach (var card in cards.Where(item => item.MediaPreview?.IsAvailable == true).Take(limit))
        {
            try
            {
                var bytes = await api.MediaThumbnailAsync(card.MediaPreview!.AssetId, token);
                card.SetThumbnail(await FromBytesAsync(bytes));
            }
            catch
            {
                card.SetThumbnail(null);
            }
        }
    }
}
