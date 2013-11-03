// Helper utilities used during development.

function logSymbolWidth()
{
    var texts = document.getElementsByTagName("text");
    var symbolWidths = [];
    var count = texts.length;
    for (var i = 0; i < count; i++)
    {
        var element = texts[i];
        var symbolWidth = element.offsetWidth / element.textContent.length;
        symbolWidths[i] = symbolWidth;
    }
    console.log(average(symbolWidths));
}

function average(values)
{
    var sum = 0.0;
    var length = values.length;
    if (length === 0)
    {
        return 0.0;
    }
    for (var i = 0; i < length; i++)
    {
        sum += values[i];
    }
    return sum / length;
}
