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

async function make_plot(times) {
	const layout = {'margin': {t:0}};

	Plotly.newPlot(mainplot, [times], layout)

}




async function init() {
	const timeseries = await fetch("api/timeseries");

	const idx = timeseries["headers"].findIndex("timestamp");

	await make_plot(timeseries["table"].map( (row) => { row[idx] }));

}


document.onload = init();



