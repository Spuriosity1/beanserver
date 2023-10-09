const datauri = "/data/transactions.csv";


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




function init() {
	const mainplot = document.getElementById('main-plot');
	const rowdata = get_csv_data(datauri);
	
	const layout = {'margin': {t:0}};
	Plotly.newPlot(mainplot, rowdata, layout)

}


document.onload = init();



