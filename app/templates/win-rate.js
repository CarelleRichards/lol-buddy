google.charts.load('current', {packages: ['corechart', 'bar']});
google.charts.setOnLoadCallback(drawBasic);

function drawBasic() {
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Outcome');
    data.addColumn('number', 'Percentage');
    data.addRows([
        ['Win', {{ win_rate["win"] }}],
        ['Loss', {{ win_rate["loss"] }}],
    ]);

    var options = {
        colors: ['#6151a8', '#39335a'],
        enableInteractivity: false,
        pieSliceText: 'none',
        pieHole: 0.6,
        legend: 'none',
        backgroundColor: {
            fill: 'transparent'
        },
        width: '100%',
        chartArea: {
            height: '100%',
            width: '100%',
            bottom: 0,
            top: 1,
            left: 0,
            right: 0,
        },
        tooltip: {
            trigger: 'none',
        },
    };
    var chart = new google.visualization.PieChart(document.getElementById('win-rate-div'));
    chart.draw(data, options);
}