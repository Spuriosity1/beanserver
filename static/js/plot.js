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

async function make_plot(data) {
	const layout = {
    'margin': {t:0},
    'barmode': 'stack'
  };


  cappdata = {
    'x': [],
    'users': [],
    'name': 'Cappuccino',
    'type': 'histogram'
  }

  amerdata = {
    'x': [],
    'users': [],
    'name': 'Americano',
    'type': 'histogram'
  }

  esprdata = {
    'x': [],
    'users': [],
    'name': 'Espresso',
    'type': 'histogram'
  }

  teadata = {
    'x': [],
    'users': [],
    'name': 'Tea',
    'type': 'histogram'
  }

  
  beantypes = {
    "cappuccino": cappdata,
    "cappuccino2": cappdata,
    "americano": amerdata,
    "americano2": amerdata,
    "espresso": esprdata,
    "espresso2": esprdata,
    "tea": teadata
  }

  const typeID = await data["headers"].indexOf("type");
  const timeID = await data["headers"].indexOf("timestamp");
  const userID = await data["headers"].indexOf("crsid");

  (await data["table"]).forEach( row => {   
    beantypes[row[typeID]].x.push(row[timeID]);
    beantypes[row[typeID]].users.push(row[userID]);
  });
  

  const dataset = [esprdata,cappdata,amerdata,teadata];

	Plotly.newPlot(mainplot, dataset, layout);

  // register event handlers
  //
  
  mainplot.on('plotly_click',  (clickdata) => {
    const dd = clickdata['points'][0];
    const data = dataset[ dd['curveNumber'] ];
    count = {};
    dd['pointIndices'].forEach( I => {
      let ca = count[ data['users'][I] ];
      ca = (ca === undefined) ? 1 : ca +1;
      count[ data['users'][I] ] = ca;
    }); 
    console.log(count);
  });



}



async function init() {

	const res = await fetch("/api/timeseries");
	const jr = await res.json();	

  await make_plot( jr );
}


document.onload = init();



