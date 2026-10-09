import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo, useRef } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import type { FeatureCollection } from "../../types/api";
import { formatNumber } from "../../utils/format";

interface Props {
  data: FeatureCollection;
  selectedIndex: number | null;
  onSelect: (featureIndex: number) => void;
}

let datasetCounter = 0;
const COLOR = "#176b58";
const COLOR_SELECTED = "#d97706";

const styleFor = (selected: boolean): L.PathOptions => ({
  color: selected ? COLOR_SELECTED : COLOR,
  weight: selected ? 3.5 : 2,
  fillColor: selected ? COLOR_SELECTED : COLOR,
  fillOpacity: selected ? 0.35 : 0.18,
});

function FitBounds({ data }: { data: FeatureCollection }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.geoJSON(data as GeoJSON.GeoJsonObject).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28], maxZoom: 18 });
  }, [data, map]);
  return null;
}

function FocusSelected({ layers, index }: { layers: Map<number, L.Layer>; index: number | null }) {
  const map = useMap();
  useEffect(() => {
    if (index === null) return;
    const layer = layers.get(index) as (L.Layer & { getBounds?: () => L.LatLngBounds; getLatLng?: () => L.LatLng }) | undefined;
    if (!layer) return;
    if (layer.getBounds) map.fitBounds(layer.getBounds(), { padding: [48, 48], maxZoom: 18 });
    else if (layer.getLatLng) map.setView(layer.getLatLng(), Math.max(map.getZoom(), 16));
  }, [index, layers, map]);
  return null;
}

export function FeatureMap({ data, selectedIndex, onSelect }: Props) {
  const layers = useRef(new Map<number, L.Layer>());
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const selectedRef = useRef(selectedIndex);
  selectedRef.current = selectedIndex;

  // Rebuild layers only when the dataset changes; selection restyles in place.
  const geoJsonKey = useMemo(() => ++datasetCounter, [data]);

  useEffect(() => {
    layers.current.forEach((layer, index) => {
      const selected = index === selectedIndex;
      if (layer instanceof L.CircleMarker) {
        layer.setStyle({ ...styleFor(selected), fillOpacity: 0.9, radius: selected ? 9 : 7 } as L.CircleMarkerOptions);
      } else if (layer instanceof L.Path) {
        layer.setStyle(styleFor(selected));
      }
      if (selected && layer instanceof L.Path) layer.bringToFront();
    });
  }, [selectedIndex]);

  return (
    <MapContainer className="map" center={[0, 0]} zoom={2} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <GeoJSON
        key={geoJsonKey}
        data={data as GeoJSON.GeoJsonObject}
        style={() => styleFor(false)}
        pointToLayer={(_, latlng) =>
          L.circleMarker(latlng, { radius: 7, ...styleFor(false), fillOpacity: 0.9 })
        }
        onEachFeature={(feature, layer) => {
          const props = (feature as GeoJSON.Feature).properties as FeatureCollection["features"][number]["properties"];
          layers.current.set(props.feature_index, layer);
          const m = props.measurement;
          const lines = [`<strong>#${props.feature_index} · ${props.geometry_type}</strong>`];
          if (m) lines.push(`${m.type === "area" ? "Area" : "Length"}: ${formatNumber(m.value)} ${m.unit}`);
          layer.bindTooltip(lines.join("<br/>"), { sticky: true });
          layer.on("click", () => onSelectRef.current(props.feature_index));
          if (props.feature_index === selectedRef.current && layer instanceof L.Path) layer.setStyle(styleFor(true));
        }}
      />
      <FitBounds data={data} />
      <FocusSelected layers={layers.current} index={selectedIndex} />
    </MapContainer>
  );
}
