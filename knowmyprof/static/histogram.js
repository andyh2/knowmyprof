function histogram(histogramArr, id) {
    var histogramYears = histogramArr.map(function(u) { return u['year']; });
    var scaleMin = Math.min.apply(null, histogramYears);
    var scaleMax = Math.max.apply(null, histogramYears);
    console.log(histogramYears)
    console.log(scaleMin, scaleMax);
    var vlSpec = {
        width: 550,
      "data": {'values': histogramArr},
      "mark": "bar",
      "description": "",
      actions: false,
      "encoding": {
        "x": {
          "field": "year",
          "type": "ordinal",
          'title': 'Year',
          'scale': {
            // domain: [scaleMin, scaleMax],
            bandSize: 17
          }
        },
        "y": {
          "field": "publications",
          "type": "quantitative"
        }
      }
    }

    var embedSpec = {
      width: 600,
      mode: "vega-lite",
      spec: vlSpec,

      actions: false
    }
    vg.embed("#vis_" + id, embedSpec, function(error, result) {
        console.log(result)
    });
}