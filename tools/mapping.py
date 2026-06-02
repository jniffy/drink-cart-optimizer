"""Render the placement plan as a Google Maps JavaScript API embed."""
from __future__ import annotations
import json
import os


_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { height: 100%; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
  #map { height: 100%; width: 100%; }
  .info b { color: #1e40af; }
  .info .row { margin-bottom: 2px; }
  .legend {
    position: absolute; top: 10px; right: 10px;
    background: rgba(255,255,255,0.95); padding: 8px 12px; border-radius: 6px;
    font-size: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    z-index: 5;
  }
  .legend-row { display: flex; align-items: center; margin-bottom: 4px; }
  .legend-blue { width: 16px; height: 16px; border-radius: 50%; margin-right: 8px; background: #1e40af; }
  .legend-grey { width: 16px; height: 16px; border-radius: 50%; margin-right: 8px; background: #94a3b8; border: 1px solid #475569; }
  .legend-grad { width: 100px; height: 10px; background: linear-gradient(to right, #4dffff, #00ffff, #00ff00, #ffff00, #ff7f00, #ff0000); border-radius: 2px; }
</style>
</head>
<body>
<div id="map"></div>
<div class="legend">
  <div class="legend-row"><div class="legend-blue"></div>Drink cart placement</div>
  <div class="legend-row"><div class="legend-grey"></div>Zone centroid (hover for value)</div>
  <div style="height:6px"></div>
  <div style="font-size:11px;color:#555;">Predicted foot-traffic intensity</div>
  <div class="legend-grad"></div>
  <div style="display:flex;justify-content:space-between;font-size:10px;color:#555;">
    <span>Low</span><span>High</span>
  </div>
</div>
<script>
  const PLACEMENTS = __PLACEMENTS__;
  const HEATPOINTS = __HEATPOINTS__;
  const ZONES = __ZONES__;
  const MAX_FT = __MAX_FT__;

  function initMap() {
    const map = new google.maps.Map(document.getElementById('map'), {
      center: { lat: 47.6205, lng: -122.3349 },
      zoom: 12,
      mapTypeId: 'roadmap',
      styles: [
        { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
        { featureType: 'transit', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] }
      ],
    });

    // Heat layer -- smaller radius so adjacent zones don't blob together,
    // and explicit maxIntensity so the brightest zone is the actual data max.
    const heatData = HEATPOINTS.map(p => ({
      location: new google.maps.LatLng(p.lat, p.lng),
      weight: p.weight,
    }));
    const heatmap = new google.maps.visualization.HeatmapLayer({
      data: heatData,
      radius: 28,
      blur: 18,
      opacity: 0.55,
      maxIntensity: MAX_FT / 1000.0,
    });
    heatmap.setMap(map);

    // Zone-centroid markers with the actual predicted foot-traffic value on hover.
    // This makes the per-zone numbers readable, regardless of how the heat
    // layer blobs neighboring zones together.
    const zInfo = new google.maps.InfoWindow();
    ZONES.forEach(z => {
      const dot = new google.maps.Marker({
        position: { lat: z.lat, lng: z.lng },
        map: map,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 6,
          fillColor: '#94a3b8',
          fillOpacity: 0.9,
          strokeColor: '#475569',
          strokeWeight: 1,
        },
        title: z.zone_name + ': ' + z.predicted_foot_traffic.toLocaleString() + ' pedestrians',
        zIndex: 1,
      });
      dot.addListener('click', () => {
        zInfo.setContent(
          '<div style="min-width:180px"><b>' + z.zone_name + '</b><br>' +
          'Predicted foot traffic: <b>' + z.predicted_foot_traffic.toLocaleString() + '</b> pedestrians</div>'
        );
        zInfo.open(map, dot);
      });
    });

    // Cart placement markers (blue numbered pins on top of everything)
    const infoWindow = new google.maps.InfoWindow();
    PLACEMENTS.forEach(p => {
      const marker = new google.maps.Marker({
        position: { lat: p.lat, lng: p.lng },
        map: map,
        title: p.cart_id + ' -- ' + p.spot_name,
        label: { text: p.cart_id.replace('EC-', ''), color: 'white', fontSize: '11px', fontWeight: 'bold' },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 14,
          fillColor: '#1e40af',
          fillOpacity: 0.95,
          strokeColor: 'white',
          strokeWeight: 2,
        },
        zIndex: 100,
      });
      marker.addListener('click', () => {
        infoWindow.setContent(
          '<div class="info" style="min-width:220px">' +
          '<div class="row"><b>' + p.cart_name + '</b> (' + p.cart_id + ')</div>' +
          '<div class="row"><b>Spot:</b> ' + p.spot_name + '</div>' +
          '<div class="row"><b>Zone:</b> ' + p.zone_name + '</div>' +
          '<div class="row"><b>Driver:</b> ' + p.dominant_event + '</div>' +
          '<div class="row"><b>Predicted foot traffic:</b> ' + p.predicted_foot_traffic.toLocaleString() + '</div>' +
          '<div class="row"><b>Projected revenue:</b> $' + p.projected_revenue_usd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + '</div>' +
          '</div>'
        );
        infoWindow.open(map, marker);
      });
    });
  }
  window.initMap = initMap;
</script>
<script async defer
  src="https://maps.googleapis.com/maps/api/js?key=__API_KEY__&libraries=visualization&callback=initMap">
</script>
</body>
</html>
"""


def render_placement_map_html(predictions, plan, api_key=None):
    api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY", "")
    max_ft = max((p.get("predicted_foot_traffic", 0) for p in predictions), default=1000)
    heat = [
        {"lat": p["lat"], "lng": p["lng"],
         "weight": max(1, p["predicted_foot_traffic"]) / 1000.0}
        for p in predictions
    ]
    zones = [
        {"lat": p["lat"], "lng": p["lng"],
         "zone_name": p["zone_name"],
         "predicted_foot_traffic": p["predicted_foot_traffic"]}
        for p in predictions
    ]
    return (
        _HTML_TEMPLATE
        .replace("__PLACEMENTS__", json.dumps(plan))
        .replace("__HEATPOINTS__", json.dumps(heat))
        .replace("__ZONES__", json.dumps(zones))
        .replace("__MAX_FT__", str(max_ft))
        .replace("__API_KEY__", api_key)
    )


def render_placement_map(predictions, plan):
    return render_placement_map_html(predictions, plan)
