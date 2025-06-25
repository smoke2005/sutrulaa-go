// Call this when rendering each place in the itinerary
function addOlaButtonForPlace(placeName, dropLat, dropLng, containerElement) {
  const button = document.createElement('button');
  button.textContent = 'Book Ola to ' + placeName;
  button.style.backgroundColor = '#FFD700'; // Gold
  button.style.color = '#222';
  button.style.fontWeight = 'bold';
  button.style.padding = '8px 16px';
  button.style.margin = '6px 0';
  button.style.border = 'none';
  button.style.borderRadius = '8px';
  button.style.cursor = 'pointer';
  button.style.boxShadow = '0 2px 6px rgba(0,0,0,0.12)';
  button.onclick = function() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(position) {
        const pickupLat = position.coords.latitude;
        const pickupLng = position.coords.longitude;
        const olaLink = getOlaDeepLink(pickupLat, pickupLng, dropLat, dropLng);
        window.open(olaLink, '_blank');
      }, function() {
        alert('Could not get your location for Ola booking.');
      });
    } else {
      alert('Geolocation is not supported by your browser.');
    }
  };
  containerElement.appendChild(button);
}

function getOlaDeepLink(pickupLat, pickupLng, dropLat, dropLng) {
  return `https://book.olacabs.com/?pickup_lat=${pickupLat}&pickup_lng=${pickupLng}&drop_lat=${dropLat}&drop_lng=${dropLng}`;
}