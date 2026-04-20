const userLat = localStorage.getItem("farm_lat");
const userLng = localStorage.getItem("farm_lng");

console.log("Latitude:", userLat);
console.log("Longitude:", userLng);

if (!userLat || !userLng) {
  document.getElementById("store-list").innerHTML =
    "<p>Please select farm location first.</p>";
  throw new Error("Location not found");
}

const map = L.map("storeMap").setView([userLat, userLng], 10);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "© OpenStreetMap contributors"
}).addTo(map);

function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;

  const a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI/180) *
    Math.cos(lat2 * Math.PI/180) *
    Math.sin(dLon/2) * Math.sin(dLon/2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

async function fetchStores() {
  const radius = 20000;

  const query = `
    [out:json];
    (
      node["shop"="fertilizer"](around:${radius},${userLat},${userLng});
      node["shop"="agrarian"](around:${radius},${userLat},${userLng});
      node["shop"="agricultural"](around:${radius},${userLat},${userLng});
      node["shop"="garden_centre"](around:${radius},${userLat},${userLng});
    );
    out;
  `;
   
  const response = await fetch(
    "https://overpass.kumi.systems/api/interpreter",
    { method: "POST", headers: {
      "Content-Type": "text/plain"
    },
    body: query }
  );

  if (!response.ok) {
  throw new Error("Overpass API error");
  }

  const data = await response.json();

  const storeList = document.getElementById("store-list");

  data.elements.forEach(store => {
    const distance = calculateDistance(
      parseFloat(userLat),
      parseFloat(userLng),
      store.lat,
      store.lon
    );

    if (distance <= 50) {

      L.marker([store.lat, store.lon])
        .addTo(map)
        .bindPopup(
          `<b>${store.tags?.name || "Fertilizer Store"}</b>
           <br>Distance: ${distance.toFixed(2)} km`
        );

      const div = document.createElement("div");
      div.className = "p-4 border rounded-lg";
      div.innerHTML = `
        <h3 class="font-semibold">
          ${store.tags?.name || "Fertilizer Store"}
        </h3>
        <p>Distance: ${distance.toFixed(2)} km</p>
      `;

      storeList.appendChild(div);
    }
  });
}

fetchStores();