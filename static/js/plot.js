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

// Getting DOM elements
//

const mainplot = document.getElementById('main-plot');
const timehist = document.getElementById('time-plot');
const leaderDiv = document.getElementById("leaderboard");
const leaderDivWeekly = document.getElementById("weekly_leaderboard");


const gli_anni = ["2023", "2024", "2025", "2026", "2027", "2028"];

const cbg_term_dates = {
  "Michaelmas Full Term Begins": ['2023-10-03', '2024-10-08', '2025-10-07', '2026-10-08'],
  "Michaelmas Full Term Ends":   ['2023-12-01', '2024-12-06', '2025-12-05', '2026-12-04'],
  "Lent Full Term Begins":       ['2024-01-16', '2025-01-21', '2026-01-20', '2027-01-19'],
  "Lent Full Term Ends":         ['2024-03-15', '2025-03-21', '2026-03-20', '2027-03-19'],
  "Easter Full Term Begins":     ['2024-04-23', '2025-04-29', '2026-04-28', '2027-04-27'],
  "Easter Full Term Ends":       ['2024-06-14', '2025-06-20', '2026-06-19', '2027-06-18'],
  "Michaelmas Begins": gli_anni.map( y => y + "-10-01"),
  "Michaelmas Ends": gli_anni.map( y => y + "-12-19"),
  "Lent Begins": gli_anni.map( y => y + "-01-05"),
  "Lent Ends": gli_anni.map( y => y + "-03-25"),
  "Easter Begins": gli_anni.map( y => y + "-04-10"),
  "Easter Ends": gli_anni.map( y => y + "-06-18"),
}


async function make_plots(data) {
  const now = new Date();
  now.setHours(now.getHours()+24);
  const then = new Date(now);
  then.setMonth(now.getMonth() -6);

  const nows = now.toISOString().slice(0,10);
  const thens = then.toISOString().slice(0,10);
        
  const default_dates = [thens, nows];
  const minorticks = [];
  const ticklabels = [];

  Object.entries(cbg_term_dates).forEach( (k, v) => {
    minorticks.concat(v);
    ticklabels.concat(Array(v.length).fill(k));
  });

  const selectorOptions = {
    buttons: [
        {
          count: 7,
          label: '1w',
          step: 'day',
          stepmode: 'backward'
        },
        {
          count: 1,
          label: '1m',
          step: 'month',
          stepmode: 'backward'
        },
        {
          count: 6,
          label: '6m',
          step: 'month',
          stepmode: 'backward'
        },
        {step: 'all'}
      ]};

  const flavour_hist_layout = {
    //'margin': {t:0},
    barmode: 'stack',
    title: {
      text: 'Daily Coffee Consumption',
      xref: 'paper',
      x: 0.05,
    },
    xaxis: {
      autorange: false,
      range: default_dates,
      rangeselector: selectorOptions,
      rangeslider: {},
      type: 'date',
//      minor:{
//        tickmode: 'array',
//        tickvals: minorticks
//      },
//      ticktext: ticklabels
    },
    yaxis: {
      autorange: true,
      type: 'linear'
    },
    showlegend: true,
    legend: {
      x: 0,
      y: 1,
      xanchor: 'left'
    },
    margin: {
      l: 0,
      r: 0
    }
  };

  const time_hist_layout = {
    //title: {
    //  text: 'Beverage Time',
    //  xref: 'paper',
    //  x: 0.05,
    //},
    yaxis: {
      autorange: 'reversed',
      tickformat: '%H'
    },
  autosize:false,
    margin:{
      b:0,
      t:0,
      r:0,
      l:20
    },
    height: 260,
    width: 250


  };

  const traces = ['Cappuccino', 'Americano', 'Espresso', 'Tea'].map( s => {
    return {'x': [],'users': [],'name': s, 'type': 'histogram', 'xbins': {'size': 1000*3600*24}};
  });


  // Lodaing data
  // Group double shots together
  const beantypes = {
    "cappuccino": traces[0],
    "cappuccino2": traces[0],
    "americano": traces[1],
    "americano2": traces[1],
    "espresso": traces[2],
    "espresso2": traces[2],
    "tea": traces[3]
  };

  const timedata = {'y': [],
    'type': 'histogram',
   // 'xbins': {'size': 1000*3600}
  }

  const typeID = await data["headers"].indexOf("type");
  const timeID = await data["headers"].indexOf("timestamp");
  const userID = await data["headers"].indexOf("crsid");

  (await data["table"]).forEach( row => {
    if (row[typeID] in beantypes){
      beantypes[row[typeID]].x.push(row[timeID]);
      beantypes[row[typeID]].users.push(row[userID]);
      timedata.y.push("1970-01-01 "+row[timeID].split(' ')[1]);
    }
  });

  Plotly.newPlot(mainplot, traces, flavour_hist_layout);
  Plotly.newPlot(timehist, [timedata], time_hist_layout);

  // register event handlers
  // 
  window.addEventListener('resize', resize_all);
  
  const menu = document.getElementById('menu');
  if (menu !== null){
    menu.addEventListener('transitionend', resize_all);
  }
  
//    function adjust_histogram(start, end) {
//      traces.forEach( d => {d.xbins = {'start': start, 'end': end, 'size': 1000*3600*24};});
//    }
//  mainplot.on('plotly_reflavour_hist_layout',  (relayout) => {
//    console.log(
//      reflavour_hist_layout["xaxis.range[0]"],
//      reflavour_hist_layout["xaxis.range[1]"]
//    );
//    adjust_histogram(
//      reflavour_hist_layout["xaxis.range[0]"],
//      reflavour_hist_layout["xaxis.range[1]"]
//    );
//  });
  //
  //
  resize_all();
}


  function resize_all() {
    Plotly.relayout(mainplot, {width: mainplot.offsetWidth});
    Plotly.relayout(timehist, {width: timehist.offsetWidth});
  }

async function make_leaderboard(res){

  if (!res["success"] || res["data"] === undefined){
    return "<p>Failed to fetch data.</p>";
  }
  
  let s = '<table class="pure-table pure-table-horizontal centred">\
    <thead><tr><th>crsid</th><th>Shots</th></tr></thead>\
    ';
  s += "<tbody>";
  res["data"].slice(0,5).forEach( r => {
    s += "<tr><td>" + r["crsid"] + "</td><td>" + r["shots"] +"</td></tr>";
  });
  s += "</tbody></table>";
  return s;
}



async function init() {

  const res_leader = await fetch("/api/leaderboard");
  const res_week = await fetch("/api/leaderboard/sinceday/6");
  const res_ts = await fetch("/api/timeseries");

  let data_week = await res_week.json();
  leaderDivWeekly.innerHTML = await make_leaderboard( data_week );
  document.getElementById('weekly').setAttribute("title",
    "Shots since " + data_week['datesince'])
  leaderDiv.innerHTML = await make_leaderboard( await res_leader.json());


  await make_plots(await res_ts.json());

  
}


document.onload = init();



