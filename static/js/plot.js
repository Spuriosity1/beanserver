async function get_csv_data(url) {
  const res = await fetch(url);

  const rows = [];
  let curr_row = '';
  for await (const chunk_bytes of res.body) {
		chunk = String.fromCharCode(...chunk_bytes);
		for (c of chunk){
      if (c === '\n' && curr_row.length > 0) {
        rows.push(curr_row.split('\t'));
        curr_row = '';
      } else {
        curr_row += c;
      }
    }
  }
  return rows;
} 


const mainplot = document.getElementById('main-plot');

function make_plot(times) {
	const layout = {'margin': {t:0}};

	Plotly.newPlot(mainplot, [times], layout)

}




async function init() {

	const res = await fetch("/api/timeseries");
	const jr = await res.json();	
	const idx = await jr["headers"].indexOf("timestamp");

	await make_plot( {
		'x': jr["table"].map( (row) =>  row[idx]),
		'type': 'histogram'
	});

}


document.onload = init();



