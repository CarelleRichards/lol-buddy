google.charts.load('current', {packages: ['corechart', 'bar']});
google.charts.setOnLoadCallback(drawBasic);

function setColour(value, max) {
    var colour = "#39335a";
    if (value == max) {
        colour = "#6151a8";
    }
    return colour;
}

function drawBasic() {
    var middle = {{ role_stats["middle"] }};
    var top = {{ role_stats["top"] }};
    var jungle = {{ role_stats["jungle"] }};
    var bottom = {{ role_stats["bottom"] }};
    var support = {{ role_stats["support"] }};
    var total = middle + top + jungle + bottom + support;
    var highest = Math.max(middle, top, jungle, bottom, support);

    var data = google.visualization.arrayToDataTable([
        ['Role', 'Played', { role: 'style' }],
        ['Top\n' + String((top / total) * 100) + "%", top, setColour(top, highest)],
        ['Jungle\n' + String((jungle / total) * 100) + "%", jungle, setColour(jungle, highest)],
        ['Middle\n' + String((middle / total) * 100) + "%", middle, setColour(middle, highest)],
        ['Bottom\n' + String((bottom / total) * 100) + "%", bottom, setColour(bottom, highest)],
        ['Support\n' + String((support / total) * 100) + "%", support, setColour(support, highest)]

    ]);


    var options = {
        enableInteractivity: false,
        width: '100%',
        chartArea: {
            height: '100%',
            width: '100%',
            bottom: 54,
            top: 0,
            left: 0,
            right: 0,
        },
        bar: {
            groupWidth: '50%',
        },
        tooltip: {
            trigger: 'none',
        },
        vAxis: {
        viewWindow: {
            min: 0,
            max: highest,
          },
            textPosition: 'none',
            gridlines: {
                color: 'transparent'
            },
            baselineColor: "transparent",
            gridlineColor: 'transparent',
        },
        legend: 'none',
        backgroundColor: {
            fill: 'transparent'
        },
        hAxis: {
           textStyle: {
                color: '#ffffff',
                fontName: 'Ubuntu, 300',
                fontSize: 17,
           },
        },
    };

    var chart = new google.visualization.ColumnChart(document.getElementById('role-stats-div'));
    chart.draw(data, options);
}